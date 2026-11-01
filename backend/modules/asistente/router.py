"""Router del Asistente (AI Companion).

- Solo ve el resumen del proyecto autenticado en el token: nunca mezcla el
  negocio real con los datos de práctica de demo.
- Toda llamada a un modelo pasa por `ia.servicio` (capa agnóstica, AGENTS.md).
- Lo que sale hacia el proveedor va seudonimizado (ADR-034): el modelo ve
  "Cliente 1", el operador lee "Sra. Flora". También el historial.
- Las acciones que propone son botones que el operador decide tocar (ADR-037).
- No depende del router del Dashboard (D-06): usa su servicio de cálculo y,
  si no está disponible, responde igual pero sin cifras.
"""

import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

import seguridad
from database import obtener_sesion
from fechas import dia_peruano
from ia import configuracion, llave_local, registro
from ia.privacidad import seudonimizar_resumen
from ia.servicio import AsistenteNoDisponible, armar_mensajes, preguntar
from seguridad import proyecto_autenticado

from .schemas import EstadoAsistente, LlaveEntrada, PreguntaEntrada, RespuestaSalida, ValoracionEntrada

router = APIRouter(prefix="/api/asistente", tags=["asistente"])

SIN_CIFRAS = {"aviso": "Las cifras de la caja no están disponibles en este momento."}


MAX_DEUDORES = 5


def _clientes_que_deben(sesion: Session) -> list[dict]:
    """Los que más deben, para responder "¿quién me debe más?" sin adivinar.

    El resumen de caja solo trae la deuda de quien tiene una orden abierta.
    """
    from sqlalchemy import select

    from modules.ventas import servicio as ventas
    from modules.ventas.models import Cliente

    deudas = sorted(
        ((cliente_id, deuda) for cliente_id, deuda in ventas.deudas_por_cliente(sesion).items() if deuda > 0),
        key=lambda par: par[1],
        reverse=True,
    )[:MAX_DEUDORES]
    ids = [cliente_id for cliente_id, _ in deudas]
    nombres = dict(sesion.execute(select(Cliente.id, Cliente.nombre).where(Cliente.id.in_(ids))).all())
    return [{"nombre": nombres[cid], "deuda": f"{deuda:.2f}"} for cid, deuda in deudas if cid in nombres]


def _resumen_del_proyecto(sesion: Session) -> dict:
    try:
        from modules.dashboard.servicio import calcular_resumen

        resumen = calcular_resumen(sesion, dia_peruano()).model_dump(mode="json")
    except Exception:  # noqa: BLE001 — sin Dashboard, el Asistente sigue atendiendo
        return dict(SIN_CIFRAS)
    # El modelo no sabe qué día es: sin esto no puede decir qué pedido se atrasó
    hoy = dia_peruano().isoformat()
    resumen["hoy"] = hoy
    for pedido in resumen.get("pedidos_por_llegar", []):
        pedido["atrasado"] = pedido["fecha_estimada"] < hoy
    try:
        resumen["clientes_que_deben"] = _clientes_que_deben(sesion)
    except Exception:  # noqa: BLE001 — sin Ventas, se responde con lo que hay
        sesion.rollback()
    return resumen


@router.post("/preguntar", response_model=RespuestaSalida)
async def preguntar_endpoint(
    datos: PreguntaEntrada,
    sesion: Session = Depends(obtener_sesion),
    proyecto: str = Depends(proyecto_autenticado),
) -> RespuestaSalida:
    # El Asistente responde con el mismo resumen que ve el operador: no inventa cifras
    resumen = _resumen_del_proyecto(sesion)
    anonimo, alias = seudonimizar_resumen(resumen)
    contexto = json.dumps(anonimo, ensure_ascii=False)
    pregunta = alias.ocultar_en_texto(datos.mensaje)
    historial = [(turno.rol, alias.ocultar_en_texto(turno.texto)) for turno in datos.historial]

    try:
        respuesta = await preguntar(pregunta, contexto, historial)
    except AsistenteNoDisponible as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    id_respuesta = str(uuid4())
    # Solo si está activado (ADR-038), y solo con texto seudonimizado
    registro.guardar_intercambio(
        proyecto,
        id_respuesta,
        mensajes_enviados=armar_mensajes(pregunta, contexto, historial),
        respuesta_del_modelo=respuesta.texto,
        modelo=respuesta.modelo,
    )
    return RespuestaSalida(
        respuesta=alias.reidentificar(respuesta.texto),
        acciones=respuesta.acciones,
        id_respuesta=id_respuesta,
        modelo=respuesta.modelo,
    )


@router.post("/valoracion", status_code=status.HTTP_204_NO_CONTENT)
def valorar(datos: ValoracionEntrada, proyecto: str = Depends(proyecto_autenticado)) -> None:
    """ "Me sirvió" / "No me sirvió". Señal para elegir ejemplos de fine-tuning."""
    registro.valorar(proyecto, datos.id_respuesta, datos.util)


# ---------------------------------------------------------------- llave (D-14)

EQUIPO_LOCAL = {"127.0.0.1", "::1"}
_SOLO_DESDE_EL_EQUIPO = "La llave solo se cambia desde la computadora del programa."


def _estado(request: Request) -> EstadoAsistente:
    ajustes = configuracion.leer()
    return EstadoAsistente(
        listo=ajustes.lista,
        puede_guardar_llave=_se_puede_guardar(ajustes.proveedor, request),
        llave_guardada=llave_local.guardada(),
    )


def _se_puede_guardar(proveedor: str, request: Request) -> bool:
    """Solo la app de escritorio, desde la misma computadora.

    En la nube la llave es configuración del servidor, y el PIN de demo es público:
    nadie debe poder reemplazarla desde otro dispositivo de la red.
    """
    origen = request.client.host if request.client else ""
    return (
        seguridad.ENTORNO == "local"
        and proveedor == "nvidia"
        and llave_local.disponible()
        and origen in EQUIPO_LOCAL
    )


@router.get("/estado", response_model=EstadoAsistente)
def estado_del_asistente(
    request: Request, _proyecto: str = Depends(proyecto_autenticado)
) -> EstadoAsistente:
    """Si el Asistente puede responder, para saber si hay que pedir la llave."""
    return _estado(request)


@router.post("/llave", response_model=EstadoAsistente)
async def guardar_llave(
    datos: LlaveEntrada, request: Request, _proyecto: str = Depends(proyecto_autenticado)
) -> EstadoAsistente:
    """Guarda la llave cifrada en este dispositivo. No queda en ninguna respuesta ni registro."""
    ajustes = configuracion.leer()
    if not _se_puede_guardar(ajustes.proveedor, request):
        raise HTTPException(status_code=403, detail=_SOLO_DESDE_EL_EQUIPO)
    llave = datos.llave.strip()
    largo_valido = llave_local.LARGO_MINIMO <= len(llave) <= llave_local.LARGO_MAXIMO
    if not largo_valido or any(c.isspace() for c in llave):
        raise HTTPException(status_code=400, detail="No parece una llave. Cópiala completa, sin espacios.")
    modelo = ajustes.modelos[0] if ajustes.modelos else ""
    if await llave_local.rechazada_por_el_proveedor(llave, ajustes.url_base, modelo):
        raise HTTPException(status_code=400, detail="NVIDIA no aceptó esa llave. Revisa que esté completa.")
    llave_local.guardar(llave)
    return _estado(request)


@router.delete("/llave", response_model=EstadoAsistente)
def quitar_llave(request: Request, _proyecto: str = Depends(proyecto_autenticado)) -> EstadoAsistente:
    """Olvida la llave guardada en este dispositivo."""
    if not _se_puede_guardar(configuracion.leer().proveedor, request):
        raise HTTPException(status_code=403, detail=_SOLO_DESDE_EL_EQUIPO)
    llave_local.borrar()
    return _estado(request)

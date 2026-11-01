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

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import obtener_sesion
from fechas import dia_peruano
from ia import registro
from ia.privacidad import seudonimizar_resumen
from ia.servicio import AsistenteNoDisponible, armar_mensajes, preguntar
from seguridad import proyecto_autenticado

from .schemas import PreguntaEntrada, RespuestaSalida, ValoracionEntrada

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

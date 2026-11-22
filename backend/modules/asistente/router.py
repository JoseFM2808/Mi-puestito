"""Router del Asistente (AI Companion).

- Solo ve el resumen del proyecto autenticado en el token: nunca mezcla el
  negocio real con los datos de práctica de demo.
- Toda llamada a un modelo pasa por `ia.servicio` (capa agnóstica, AGENTS.md).
- Lo que sale hacia el proveedor va seudonimizado (ADR-034): el modelo ve
  "Cliente 1", el operador lee "Sra. Flora". También el historial.
- Las acciones que propone son botones que el operador decide tocar (ADR-037); si el
  operador pidió ir o hacer algo, la primera se abre sola (ADR-047). Solo navegar.
- Puede LLENAR una orden (`borrador`, ADR-049), un pago, gasto o merma (`formulario`, D-28) o un pedido a un
  proveedor (`pedido`) que el operador revisa y guarda; nunca guarda.
- No depende del router del Dashboard (D-06): usa su servicio de cálculo y,
  si no está disponible, responde igual pero sin cifras.
- Recuerda lo que el operador le pide recordar (D-26, ADR-052): hechos cortos en la base del
  proyecto, con un tope; el operador los ve y los olvida desde la pantalla.
"""

import json
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

import seguridad
from database import obtener_sesion, obtener_sesion_escritura, sesion_escritura_para
from fechas import dia_peruano
from ia import borrador, configuracion, formularios, guias, llave_local, memoria, registro
from ia import pedido as pedido_ia
from ia.acciones import EnPantalla, accion_por_tema, corregir_destino, marcar_automatica, pide_ir_o_hacer
from ia.privacidad import ALIAS_SUELTO, Seudonimos, seudonimizar_resumen
from ia.servicio import AsistenteNoDisponible, armar_mensajes, consolidar_recuerdos, preguntar
from seguridad import proyecto_autenticado

from .models import MemoriaAsistente
from .schemas import (
    EstadoAsistente,
    LlaveEntrada,
    PreguntaEntrada,
    RecuerdoSalida,
    RespuestaSalida,
    ValoracionEntrada,
)

bitacora = logging.getLogger("mi_puestito.ia")

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
    try:
        from modules.caja.servicio import del_dia

        caja = del_dia(sesion, dia_peruano())
        resumen["caja_abierta"] = caja.abierta
        resumen["en_caja"] = caja.en_caja.model_dump(mode="json")
    except Exception:  # noqa: BLE001 — sin Caja, se responde con lo demás
        sesion.rollback()
    try:
        # La semana y el mes (Fase 7): "¿cuánto vendí esta semana?" ya tiene respuesta
        from modules.analisis.servicio import del_periodo

        for periodo in ("semana", "mes"):
            datos = del_periodo(sesion, periodo).model_dump(mode="json")
            resumen[periodo] = {
                campo: datos[campo]
                for campo in (
                    "desde",
                    "vendido",
                    "pagado_a_proveedores",
                    "gastos_del_puesto",
                    "gastos_de_la_casa",
                    "resultado_del_negocio",
                    "libre",
                )
            }
    except Exception:  # noqa: BLE001 — sin Análisis, solo las cifras de hoy
        sesion.rollback()
    try:
        resumen["productos_del_inventario"] = _nombres_de_productos(sesion)
        resumen["productos_por_acabarse"] = _por_acabarse(sesion)
    except Exception:  # noqa: BLE001 — sin Inventario, la orden se llena con el nombre que dijo el operador
        sesion.rollback()
    return resumen


def _por_acabarse(sesion: Session) -> list[str]:
    """Nombres de lo que está en su mínimo o debajo (la misma regla que la tarjeta de Inventario), sin
    cantidades: "¿qué tengo que pedir?" ya tiene respuesta y no hay cifras que el modelo pueda torcer."""
    from modules.inventario.models import Producto

    consulta = (
        select(Producto.nombre)
        .where(Producto.stock_minimo.is_not(None), Producto.stock_actual <= Producto.stock_minimo)
        .order_by(Producto.nombre)
        .limit(MAX_PRODUCTOS_EN_CONTEXTO)
    )
    return list(sesion.scalars(consulta))


MAX_PRODUCTOS_EN_CONTEXTO = 80


def _nombres_de_productos(sesion: Session) -> list[str]:
    """Solo los nombres (no stock ni precios): para que una orden llenada use el nombre
    exacto del producto ("Leche Gloria", no "leches gloria") y la app lo enlace (ADR-049)."""
    from sqlalchemy import select

    from modules.inventario.models import Producto

    return list(
        sesion.scalars(select(Producto.nombre).order_by(Producto.nombre).limit(MAX_PRODUCTOS_EN_CONTEXTO))
    )


def _nombres_guardados(sesion: Session) -> tuple[list[str], list[str]]:
    """Todos los clientes y proveedores, para reconocerlos en texto libre. Sin el módulo, ninguno."""
    clientes: list[str] = []
    proveedores: list[str] = []
    try:
        from modules.ventas.models import Cliente

        clientes = list(sesion.scalars(select(Cliente.nombre)))
    except Exception:  # noqa: BLE001 — sin Ventas, solo los nombres del resumen
        sesion.rollback()
    try:
        from modules.compras.models import Proveedor

        proveedores = list(sesion.scalars(select(Proveedor.nombre)))
    except Exception:  # noqa: BLE001 — sin Compras, solo los nombres del resumen
        sesion.rollback()
    return clientes, proveedores


def _recuerdos(sesion: Session) -> list[MemoriaAsistente]:
    """Lo que recuerda, del más viejo al más nuevo. Si la tabla falla, atiende sin memoria."""
    try:
        orden = (MemoriaAsistente.creado_en, MemoriaAsistente.id)
        return list(sesion.scalars(select(MemoriaAsistente).order_by(*orden)))
    except Exception:  # noqa: BLE001
        sesion.rollback()
        return []


MAX_RECUERDOS_POR_RESPUESTA = 3


async def _recordar(
    proyecto: str, propuestos: list[str], existentes: list[str], alias: Seudonimos
) -> list[str]:
    """Guarda lo nuevo que el operador pidió recordar y, pasado el tope, consolida (D-26).

    El modelo escribe con códigos ("Cliente 2 paga por Yape"): se guarda con el nombre real, en la
    computadora del vendedor. Un hecho que conserva un código suelto no se entiende después y se
    descarta. Devuelve lo que se guardó, para decírselo al operador.
    """
    reales = [alias.reidentificar(hecho) for hecho in propuestos[:MAX_RECUERDOS_POR_RESPUESTA]]
    nuevos = memoria.sin_repetidos(existentes, [h for h in reales if not ALIAS_SUELTO.search(h)])
    if not nuevos:
        return []
    todos = [*existentes, *nuevos]
    sesion = sesion_escritura_para(proyecto)
    try:
        if len(todos) > memoria.MAX_RECUERDOS:
            # El modelo repiensa la lista sin ver nombres reales; si falla, quedan los más nuevos
            anonimos = await consolidar_recuerdos([alias.ocultar_en_texto(r) for r in todos])
            conservados = [alias.reidentificar(r) for r in anonimos]
            conservados = [r for r in conservados if not ALIAS_SUELTO.search(r)] or todos[
                -memoria.RECUERDOS_TRAS_CONSOLIDAR :
            ]
            sesion.execute(delete(MemoriaAsistente))
            sesion.add_all(MemoriaAsistente(texto=texto[: memoria.MAX_TEXTO]) for texto in conservados)
        else:
            sesion.add_all(MemoriaAsistente(texto=texto) for texto in nuevos)
        sesion.commit()
    except Exception as error:  # noqa: BLE001 — no recordar no impide responder
        sesion.rollback()
        bitacora.warning("No se pudo guardar lo que el Asistente debía recordar: %s", error)
        return []
    finally:
        sesion.close()
    return nuevos


def _lo_que_ve(datos: PreguntaEntrada, alias: Seudonimos) -> EnPantalla | None:
    """Las partes de la pantalla abierta, con los nombres de clientes y proveedores en código.

    No se incluye la del propio Asistente: señalar su caja de texto no ayuda a nadie.
    """
    if not datos.pantalla_actual or datos.pantalla_actual == "asistente" or not datos.en_pantalla:
        return None
    elementos: dict[str, str] = {}
    for elemento in datos.en_pantalla:
        if elemento.id.startswith("asistente") or elemento.id in elementos:
            continue
        nombre = alias.ocultar_en_texto(elemento.texto) or elemento.id
        if elemento.tipo == "campo":
            nombre = f"campo {nombre}" + (" [vacío]" if elemento.lleno is False else "")
        elif elemento.tipo == "boton":
            nombre = f"botón {nombre}"
        elementos[elemento.id] = nombre
    return EnPantalla(datos.pantalla_actual, elementos)


@router.post("/preguntar", response_model=RespuestaSalida)
async def preguntar_endpoint(
    datos: PreguntaEntrada,
    sesion: Session = Depends(obtener_sesion),
    proyecto: str = Depends(proyecto_autenticado),
) -> RespuestaSalida:
    # El Asistente responde con el mismo resumen que ve el operador: no inventa cifras
    resumen = _resumen_del_proyecto(sesion)
    if datos.pantalla_actual:
        resumen["pantalla_actual"] = datos.pantalla_actual
    recordados = [r.texto for r in _recuerdos(sesion)]
    anonimo, alias = seudonimizar_resumen(resumen)
    # Quien se nombra en la pregunta, el historial o un recuerdo también viaja con código (D-26)
    clientes, proveedores = _nombres_guardados(sesion)
    del_historial = [t.texto for t in datos.historial]
    en_la_pantalla = [e.texto for e in datos.en_pantalla]
    texto_libre = "\n".join([datos.mensaje, *del_historial, *recordados, *en_la_pantalla])
    alias.registrar_mencionados(texto_libre, clientes, proveedores)
    sesion.close()  # no se tiene la base abierta mientras responde el modelo

    contexto = json.dumps(anonimo, ensure_ascii=False)
    pregunta = alias.ocultar_en_texto(datos.mensaje)
    historial = [(turno.rol, alias.ocultar_en_texto(turno.texto)) for turno in datos.historial]
    recuerdos = [alias.ocultar_en_texto(r) for r in recordados]
    en_pantalla = _lo_que_ve(datos, alias)
    # Si pide ayuda, los botones de esa pantalla salen de su README (Fase 6); no llevan datos del negocio
    detalle = guias.para_la_pregunta(datos.mensaje, datos.pantalla_actual)

    try:
        respuesta = await preguntar(pregunta, contexto, historial, recuerdos, en_pantalla, detalle)
    except AsistenteNoDisponible as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    id_respuesta = str(uuid4())
    # Solo si está activado (ADR-038), y solo con texto seudonimizado
    registro.guardar_intercambio(
        proyecto,
        id_respuesta,
        mensajes_enviados=armar_mensajes(pregunta, contexto, historial, recuerdos, en_pantalla, detalle),
        respuesta_del_modelo=respuesta.texto,
        modelo=respuesta.modelo,
    )
    # Solo se recuerda si el operador lo pidió o contó algo que dura: una pregunta de cifras no deja nada
    recordado = []
    if respuesta.recuerdos and memoria.pide_recordar(datos.mensaje):
        recordado = await _recordar(proyecto, respuesta.recuerdos, recordados, alias)
    # Orden llenada (ADR-049): solo si el operador pidió registrar (ahora, o en su mensaje anterior:
    # "regístrala por mí"), y solo con precios que él dijo
    del_operador = [t.texto for t in datos.historial if t.rol == "operador"]
    lo_pidio = pide_ir_o_hacer(datos.mensaje) or bool(del_operador and pide_ir_o_hacer(del_operador[-1]))
    items = []
    if respuesta.borrador and lo_pidio:
        dicho = " ".join([datos.mensaje, *del_operador])
        items = [
            {**item, "nombre": alias.reidentificar(item["nombre"])}
            for item in borrador.validar(respuesta.borrador, dicho)
        ]
    # Pago de fiado, gasto o merma llenados (D-28): mismas reglas que la orden de venta
    formulario = None
    if respuesta.formulario and lo_pidio:
        dicho = " ".join([datos.mensaje, *del_operador])
        formulario = formularios.validar(respuesta.formulario, dicho)
        if formulario.get("cliente"):
            formulario = {**formulario, "cliente": alias.reidentificar(formulario["cliente"])}
    # Pedido a un proveedor (Compras): mismas reglas; el proveedor vuelve con su nombre real
    pedido_llenado = None
    if respuesta.pedido and lo_pidio and not items and not formulario:
        dicho = " ".join([datos.mensaje, *del_operador])
        pedido_llenado = pedido_ia.validar(respuesta.pedido, dicho)
        if pedido_llenado.get("proveedor"):
            pedido_llenado["proveedor"] = alias.reidentificar(pedido_llenado["proveedor"])
    texto = alias.reidentificar(respuesta.texto)
    # Nunca "revisa la orden" si no hay orden llenada: el operador la buscaría y no estaría
    llenado = items or formulario or pedido_llenado
    if not llenado and borrador.HABLA_DE_UNA_ORDEN_LLENADA.search(texto):
        texto = borrador.PEDIR_PRODUCTOS
    return RespuestaSalida(
        respuesta=texto,
        acciones=marcar_automatica(
            datos.mensaje,
            accion_por_tema(datos.mensaje, corregir_destino(datos.mensaje, respuesta.acciones)),
        ),
        borrador=(
            {"items": items, "para": alias.reidentificar(respuesta.para) if respuesta.para else None}
            if items
            else None
        ),
        formulario=formulario,
        pedido=pedido_llenado,
        recordado=recordado,
        id_respuesta=id_respuesta,
        modelo=respuesta.modelo,
    )


# ---------------------------------------------------------------- lo que recuerda (D-26)


@router.get("/recuerdos", response_model=list[RecuerdoSalida])
def ver_recuerdos(sesion: Session = Depends(obtener_sesion)) -> list[MemoriaAsistente]:
    """Lo que el Asistente recuerda de este negocio, del más viejo al más nuevo."""
    return _recuerdos(sesion)


@router.delete("/recuerdos/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
def olvidar(uuid: str, sesion: Session = Depends(obtener_sesion_escritura)) -> None:
    """Olvida un recuerdo (idempotente: olvidar dos veces no es un error)."""
    sesion.execute(delete(MemoriaAsistente).where(MemoriaAsistente.uuid == uuid))
    sesion.commit()


@router.delete("/recuerdos", status_code=status.HTTP_204_NO_CONTENT)
def olvidar_todo(sesion: Session = Depends(obtener_sesion_escritura)) -> None:
    """Olvida todo lo que recordaba de este negocio."""
    sesion.execute(delete(MemoriaAsistente))
    sesion.commit()


@router.post("/valoracion", status_code=status.HTTP_204_NO_CONTENT)
def valorar(datos: ValoracionEntrada, proyecto: str = Depends(proyecto_autenticado)) -> None:
    """ "Me sirvió" / "No me sirvió". Señal para elegir ejemplos de fine-tuning."""
    registro.valorar(proyecto, datos.id_respuesta, datos.util)


# ---------------------------------------------------------------- llave (D-14)

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
    return proveedor == "nvidia" and llave_local.disponible() and seguridad.desde_este_equipo(origen)


@router.get("/estado", response_model=EstadoAsistente)
def estado_del_asistente(request: Request, _proyecto: str = Depends(proyecto_autenticado)) -> EstadoAsistente:
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

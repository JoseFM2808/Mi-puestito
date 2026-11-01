"""Orquestación del Asistente: arma el contexto, prueba modelos por prioridad
y devuelve la primera respuesta que llegue a tiempo.

El operador atiende clientes mientras pregunta: un modelo que tarda demasiado
no sirve aunque responda mejor. Cada modelo tiene `tiempo_limite` segundos;
si falla o se pasa, se prueba el siguiente. El orden lo da `configuracion.py`
(medido con `python -m ia.verificar`).

Este archivo no sabe qué proveedor hay detrás (AGENTS.md): habla con
cualquier API compatible con OpenAI a través de `compatible_openai.py`.
"""

import logging
from dataclasses import dataclass, field

from . import configuracion
from .acciones import PANTALLAS, extraer
from .cifras import cifras_no_respaldadas
from .compatible_openai import ProveedorCompatibleOpenAI, es_transitorio, motivo_error

registro = logging.getLogger("mi_puestito.ia")
REINTENTOS_TRANSITORIOS = 2

# Lo que el Asistente sabe de la app, para guiar al operador (Fase 6:
# "los MD de módulos como contexto en runtime", en versión compacta).
GUIA_APP = """\
- Caja de hoy: cuánto se vendió hoy, órdenes abiertas, fiados por cobrar, ventas rápidas por \
completar y pedidos de proveedores por llegar. "Mañana necesitas en caja" es lo que hay que \
pagar por pedidos que llegan mañana.
- Ventas: "Nueva orden" abre una orden (por ejemplo, una mesa que sigue pidiendo). Se agregan \
productos con su monto y se cierra con "Cobrar en efectivo", "Cobrar con Yape o Plin" o "Fiar a \
un cliente". "Venta rápida" registra solo el monto cobrado; el detalle se completa después en \
"Ventas rápidas por completar". Todo funciona aunque no haya internet.
- Fiados: quién debe y cuánto. "Registrar un pago" anota lo que el cliente abona.
La app NO tiene todavía reportes por mes ni pantalla de inventario. No menciones pantallas ni \
reportes que no estén en esta lista."""

PROMPT_SISTEMA = """Eres el Asistente de Mi Puestito, una app para vendedores \
informales en Perú. Responde SIEMPRE en español peruano sencillo, en 1 a 4 frases \
cortas, sin tecnicismos: quien te lee puede tener baja fluidez lectora. Los montos \
van en soles con el formato S/ 12.50.

Cómo funciona la app:
{guia}

Estado actual del negocio, en formato de datos (es la única fuente de cifras):
{contexto}

Qué significa cada dato: hoy = la fecha de hoy. ventas_hoy = lo cobrado hoy. ventas_cerradas = \
cuántas ventas se cobraron hoy. proyeccion_manana = lo que hay que pagar mañana. fiados_por_cobrar \
= lo que deben TODOS los clientes, ya sumado. clientes_que_deben = quienes más deben. \
ordenes_activas = órdenes abiertas ahora (deuda_cliente = lo que ese cliente ya debía antes). \
pedidos_por_llegar = pedidos a proveedores (atrasado true = debió llegar y no llegó).

Reglas:
- Copia las cifras tal como están en los datos: no las sumes, no las redondees ni calcules \
totales. Solo si el operador te da sus propias cifras puedes hacer esa cuenta.
- No inventes cifras ni nombres. Si algo no está en los datos (por ejemplo, lo vendido en el mes), \
di que no lo tienes y sugiere dónde revisarlo.
- Los clientes y proveedores aparecen con códigos ("Cliente 1", "Proveedor A"). Escríbelos sin \
artículo: di "Cliente 1 debe", no "el Cliente 1 debe".
- Tú no registras ventas ni cobras: solo explicas y guías. Nunca digas que hiciste algo en la app.
- Si conviene que el operador vaya a una pantalla, agrega al final UNA línea exacta:
ACCION: ir_a <pantalla>
donde <pantalla> es una de: {pantallas}. Si no hace falta, no agregues esa línea."""

MAX_TURNOS_PREVIOS = 6
SIN_CIFRA_SEGURA = "No tengo esa cifra y prefiero no darte un monto dudoso. Revísala en la Caja de hoy."
MODELO_VERIFICADOR = "verificador-de-cifras"  # no es un modelo: el registro de fine-tuning lo descarta


class AsistenteNoDisponible(Exception):
    """El Asistente no pudo responder (sin configurar, o todos los modelos
    fallaron o tardaron demasiado)."""


@dataclass
class RespuestaIA:
    texto: str
    modelo: str
    acciones: list[dict[str, str]] = field(default_factory=list)


def armar_mensajes(
    mensaje: str, contexto_json: str, historial: list[tuple[str, str]]
) -> list[dict[str, str]]:
    sistema = PROMPT_SISTEMA.format(guia=GUIA_APP, contexto=contexto_json, pantallas=", ".join(PANTALLAS))
    mensajes = [{"role": "system", "content": sistema}]
    for rol, texto in historial[-MAX_TURNOS_PREVIOS:]:
        mensajes.append({"role": "assistant" if rol == "asistente" else "user", "content": texto})
    mensajes.append({"role": "user", "content": mensaje})
    return mensajes


async def preguntar(
    mensaje: str, contexto_json: str, historial: list[tuple[str, str]] | None = None
) -> RespuestaIA:
    config = configuracion.leer()
    if not config.lista:
        raise AsistenteNoDisponible(
            "El Asistente todavía no está configurado en esta computadora "
            "(falta la variable de entorno NVIDIA_API_KEY)."
        )

    proveedor = ProveedorCompatibleOpenAI(config.url_base, config.api_key)
    mensajes = armar_mensajes(mensaje, contexto_json, historial or [])
    dicho_por_el_operador = " ".join(
        [mensaje, *(texto for rol, texto in (historial or []) if rol != "asistente")]
    )

    ultimo_error: Exception | None = None
    alguna_cifra_rechazada = False
    for modelo in config.modelos:
        texto = None
        for intento in range(REINTENTOS_TRANSITORIOS + 1):
            try:
                texto = await proveedor.responder(
                    mensajes, modelo, config.tiempo_limite, configuracion.ajustes_para(modelo)
                )
                break
            except Exception as error:  # noqa: BLE001 — se prueba el siguiente modelo
                ultimo_error = error
                registro.warning("El modelo %s falló: %s", modelo, motivo_error(error))
                if not es_transitorio(error) or intento == REINTENTOS_TRANSITORIOS:
                    break
        if texto is None:
            continue
        limpio, acciones = extraer(texto)
        # Un monto inventado nunca llega al operador (ADR-042)
        if cifras_no_respaldadas(limpio, contexto_json, dicho_por_el_operador):
            alguna_cifra_rechazada = True
            registro.warning("Respuesta de %s descartada: monto sin respaldo en los datos", modelo)
            continue
        return RespuestaIA(texto=limpio or texto, modelo=modelo, acciones=acciones)

    if alguna_cifra_rechazada:
        # Mejor admitirlo que dar un monto dudoso: la pantalla sí tiene la cifra exacta
        return RespuestaIA(
            texto=SIN_CIFRA_SEGURA,
            modelo=MODELO_VERIFICADOR,
            acciones=[{"tipo": "ir_a", "pantalla": "caja", "etiqueta": PANTALLAS["caja"]}],
        )

    raise AsistenteNoDisponible(
        "El Asistente no pudo responder ahora mismo. Intenta de nuevo en un momento."
    ) from ultimo_error

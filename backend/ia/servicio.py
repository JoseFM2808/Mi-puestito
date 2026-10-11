"""Orquestación del Asistente: arma el contexto, prueba modelos por prioridad
y devuelve la primera respuesta que llegue a tiempo.

El operador atiende clientes mientras pregunta: un modelo que tarda demasiado
no sirve aunque responda mejor. Cada modelo tiene `tiempo_limite` segundos;
si falla o se pasa, se prueba el siguiente. El orden lo da `configuracion.py`
(medido con `python -m ia.verificar`).

Este archivo no sabe qué proveedor hay detrás (AGENTS.md): habla con
cualquier API compatible con OpenAI a través de `compatible_openai.py`.
"""

from dataclasses import dataclass, field

from . import configuracion
from .acciones import PANTALLAS, extraer
from .compatible_openai import ProveedorCompatibleOpenAI

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
- Fiados: quién debe y cuánto. "Registrar un pago" anota lo que el cliente abona."""

PROMPT_SISTEMA = """Eres el Asistente de Mi Puestito, una app para vendedores \
informales en Perú. Responde SIEMPRE en español peruano sencillo, en 1 a 4 frases \
cortas, sin tecnicismos: quien te lee puede tener baja fluidez lectora. Los montos \
van en soles con el formato S/ 12.50.

Cómo funciona la app:
{guia}

Estado actual del negocio, en formato de datos (es la única fuente de cifras):
{contexto}

Reglas:
- No inventes cifras ni nombres. Si algo no está en los datos, dilo y sugiere dónde revisarlo.
- Los clientes y proveedores aparecen con códigos ("Cliente 1", "Proveedor A"). Escríbelos sin \
artículo: di "Cliente 1 debe", no "el Cliente 1 debe".
- Tú no registras ventas ni cobras: solo explicas y guías. Nunca digas que hiciste algo en la app.
- Si conviene que el operador vaya a una pantalla, agrega al final UNA línea exacta:
ACCION: ir_a <pantalla>
donde <pantalla> es una de: {pantallas}. Si no hace falta, no agregues esa línea."""

MAX_TURNOS_PREVIOS = 6


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

    ultimo_error: Exception | None = None
    for modelo in config.modelos:
        try:
            texto = await proveedor.responder(
                mensajes, modelo, config.tiempo_limite, configuracion.ajustes_para(modelo)
            )
        except Exception as error:  # noqa: BLE001 — se prueba el siguiente modelo
            ultimo_error = error
            continue
        limpio, acciones = extraer(texto)
        return RespuestaIA(texto=limpio or texto, modelo=modelo, acciones=acciones)

    raise AsistenteNoDisponible(
        "El Asistente no pudo responder ahora mismo. Intenta de nuevo en un momento."
    ) from ultimo_error

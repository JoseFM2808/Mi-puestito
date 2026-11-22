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

from . import borrador, configuracion, formularios, memoria, pedido
from .acciones import APARTADOS, PANTALLAS, EnPantalla, extraer, texto_si_solo_hubo_accion
from .cifras import cifras_no_respaldadas
from .compatible_openai import ProveedorCompatibleOpenAI, es_transitorio, motivo_error

registro = logging.getLogger("mi_puestito.ia")
REINTENTOS_TRANSITORIOS = 2

# Lo que el Asistente sabe de la app, para guiar al operador, en versión compacta. Si pide ayuda, se
# agregan los botones de la pantalla desde su README (ia/guias.py: los MD de módulos en runtime).
GUIA_APP = """\
- Caja de hoy: cuánto se vendió hoy, órdenes abiertas, fiados por cobrar, ventas rápidas por \
completar y pedidos de proveedores por llegar. "Mañana necesitas en caja" es lo que hay que \
pagar por pedidos que llegan mañana. "En caja ahora" dice cuánto hay en efectivo y en Yape: \
cada día se empieza con "Abrir caja" (con cuánto se empieza en efectivo y en Yape).
- Ventas: "Nueva orden" abre una orden (por ejemplo, una mesa que sigue pidiendo). Se agregan \
productos con su monto y se cierra con "Cobrar en efectivo", "Cobrar con Yape o Plin" o "Fiar a \
un cliente". "Venta rápida" registra solo el monto cobrado; el detalle se completa después en \
"Ventas rápidas por completar". Todo funciona aunque no haya internet.
- Fiados: la lista completa de quién debe y cuánto, cliente por cliente. Si preguntan dónde ver \
a los que deben o anotar lo que un cliente pagó, es aquí: la Caja de hoy solo muestra el total. \
"Registrar un pago" anota lo que el cliente abona.
- Compras: pedidos a proveedores. "Nuevo pedido" arma un pedido y registra al proveedor si es \
nuevo. Cuando llega, "Llegó este pedido" abre la lista para marcar cada producto como "Llegó", \
"No llegó" o "Cambió", y calcula lo que hay que pagar. "Ya le pagué en efectivo" o "Ya le pagué \
con Yape" lo termina y lo descuenta de la caja.
- Gastos: lo que sale de la caja, del puesto (alquiler, transporte, luz) o de la casa (comida, \
colegio). "Anotar un gasto" pide cuánto, si salió de la gaveta o del Yape y para qué fue.
- Inventario: cuánto hay de cada producto. "Contar lo que hay" corrige el stock y "Registrar merma" \
anota lo que se perdió o venció. Tú NO ves el stock: si preguntan cuánto queda, di que no lo \
sabes y ofrece ir a Inventario.
- ¿Cómo me va? (analisis): cuánto vendió, pagó a proveedores y gastó en el puesto y en la casa en la \
semana o el mes, y cuánto le quedó libre. También qué productos le dejan más ganancia.
Hay cifras de HOY, de ESTA SEMANA (semana) y de ESTE MES (mes). De otros períodos no: dilo y ofrece \
¿Cómo me va?. No menciones pantallas que no estén en esta lista."""

PROMPT_SISTEMA = """Eres el Asistente de Mi Puestito, una app para vendedores \
informales en Perú. Responde SIEMPRE en español peruano sencillo, en 1 a 4 frases \
cortas, sin tecnicismos: quien te lee puede tener baja fluidez lectora. Los montos \
van en soles con el formato S/ 12.50.

Cómo funciona la app:
{guia}{detalle}

Estado actual del negocio, en formato de datos (es la única fuente de cifras):
{contexto}

Lo que recuerdas de este negocio porque el operador te lo contó antes (úsalo para atenderlo mejor; \
no son cifras de hoy):
{recuerdos}

Qué significa cada dato: hoy = la fecha de hoy. ventas_hoy = lo cobrado hoy. ventas_cerradas = \
cuántas ventas se cobraron hoy. proyeccion_manana = lo que hay que pagar mañana. fiados_por_cobrar \
= lo que deben TODOS los clientes, ya sumado. clientes_que_deben = quienes más deben. \
ordenes_activas = órdenes abiertas ahora (deuda_cliente = lo que ese cliente ya debía antes). \
pedidos_por_llegar = pedidos a proveedores (atrasado true = debió llegar y no llegó). \
pantalla_actual = la pantalla que el operador tiene abierta ahora. en_caja = cuánto hay ahora en \
efectivo y en Yape (caja_abierta false = aún no se abrió la caja hoy). productos_del_inventario = \
nombres de los productos registrados (sin stock ni precios). semana y mes = vendido, \
pagado_a_proveedores, gastos_del_puesto, gastos_de_la_casa, resultado_del_negocio (lo que ganó el \
negocio: "¿cuánto gané?") y libre (lo que quedó después de los gastos de la casa) de esta semana y \
de este mes.

Reglas:
- Copia las cifras tal como están en los datos: no las sumes, no las redondees ni calcules \
totales. Solo si el operador te da sus propias cifras puedes hacer esa cuenta.
- No inventes cifras ni nombres. Si algo no está en los datos (por ejemplo, lo vendido en el mes), \
di que no lo tienes y sugiere dónde revisarlo.
- Los clientes y proveedores aparecen con códigos ("Cliente 1", "Proveedor A"). Escríbelos sin \
artículo: di "Cliente 1 debe", no "el Cliente 1 debe".
- Tú no guardas ventas ni cobras: explicas, guías y LLENAS órdenes para que el operador las \
confirme. Nunca digas que registraste, cobraste o guardaste algo.
- Si el operador pide registrar una venta u orden y dice qué productos lleva (ahora o antes en la \
conversación, como "regístrala por mí"), llénala: escribe al final UNA línea por producto:
VENTA: <cantidad> x <producto> a <precio>
El precio es el de UNA unidad y va SOLO si el operador lo dijo; si no lo dijo, termina la línea en \
el producto, sin "a": la app pone el precio del inventario. Si dijo para quién es, agrega:
PARA: <nombre del cliente>
Si el producto está en productos_del_inventario, escribe ese nombre exacto (en singular). \
También en tus frases: nombra los productos por ese nombre exacto, no "esos productos".
Ejemplos: "quiero registrar 2 fideos anita a 4.80 cada uno" → VENTA: 2 x Fideos Anita a 4.80
"una venta para la señora Lucía, 1 kilo de arroz" → estas dos líneas:
VENTA: 1 x Arroz Costeño
PARA: Sra. Lucía
La app abre Ventas con la orden llenada. Dile en una frase que la revise y toque «Guardar orden». \
En ese caso no agregues ACCION.
- Si pide anotar que un cliente PAGÓ lo que debía, un GASTO o una MERMA (algo que se perdió o \
venció), llénalo con UNA línea al final (el monto solo si el operador lo dijo; si no, déjalo vacío):
ABONO: <cliente> | <monto> | <efectivo o yape>
GASTO: <monto> | <categoría> | <efectivo o yape> | <puesto o hogar> | <nota>
(categoría: alquiler, servicios, transporte, alimentacion, educacion u otros)
MERMA: <cantidad> x <producto> | <qué pasó>
Ejemplos: "anota que Cliente 9 me pagó 10 soles" → ABONO: Cliente 9 | 10.00 | efectivo
"anota un gasto de 5 soles de pasaje" → GASTO: 5.00 | transporte | efectivo | puesto | pasaje
"se vencieron 2 leches gloria" → MERMA: 2 x Leche Gloria | vencido
Dile que lo revise y toque «Guardar». En ese caso no agregues ACCION.
- Si pide hacer un PEDIDO a un proveedor (comprarle mercadería), llénalo con UNA línea por producto y, si \
dijo a quién, una con el proveedor (el monto es el total de ese producto y va SOLO si el operador lo dijo; \
si no, deja ese campo vacío):
COMPRA: <producto> | <cantidad como la dijo> | <monto total>
PROVEEDOR: <proveedor>
Ejemplo: "pídele a Proveedor A 2 sacos de arroz por 180 soles" → estas dos líneas:
COMPRA: Arroz | 2 sacos | 180.00
PROVEEDOR: Proveedor A
Dile que lo revise y toque «Guardar pedido». En ese caso no agregues ACCION.
- Si preguntan CÓMO hacer algo, explica los pasos con los nombres exactos de los botones, en 2 o \
3 frases, y ofrece hacerlo por él. Ejemplo para una venta: toca «Nueva orden», agrega lo que \
lleva y toca «Cobrar en efectivo», «Cobrar con Yape o Plin» o «Fiar a un cliente»; o dime qué \
lleva y te lleno la orden.
- Si el operador te pide que recuerdes algo, o te cuenta algo de su negocio que dura (cómo paga un \
cliente, qué día llega un proveedor, qué vende los sábados), agrega al final UNA línea:
RECORDAR: <el hecho en pocas palabras, con los códigos de clientes y proveedores>
Ejemplo: "acuérdate que Cliente 2 siempre paga por Yape" → RECORDAR: Cliente 2 paga por Yape
No recuerdes lo que solo pasó hoy ni cifras del día. Dile en una frase que lo vas a recordar.
- Responde SIEMPRE con al menos una frase. La línea ACCION va al final, nunca sola.
- Si conviene que el operador vaya a una pantalla, agrega al final UNA línea exacta:
ACCION: ir_a <pantalla>
donde <pantalla> es una de: {pantallas}. Si no hace falta, no agregues esa línea.
- Para HACER algo, lleva a la pantalla donde se hace: vender o cobrar en ventas, ver a los que \
deben o anotar un pago en fiados, pedidos a proveedores y lo que llegó en compras, productos en \
inventario. La caja es solo para ver las cifras de hoy.
- Si preguntan qué botón tocar o dónde está algo que aparece en esta lista, usa resaltar y no \
ir_a: la app lleva a la pantalla y marca esa parte. Si solo preguntan una cifra, no señales nada. \
Escribe UNA línea:
ACCION: resaltar <apartado>
donde <apartado> es uno de estos (la app lleva a su pantalla y lo marca):
{apartados}
o uno de los que el operador ve AHORA en su pantalla (úsalos para "¿dónde pongo…?" o "¿qué toco ahora?" \
mientras llena algo; [vacío] = campo sin llenar):
{en_pantalla}"""

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
    # Productos de una orden que el Asistente llenó y el operador confirma (ADR-049)
    borrador: list[dict[str, str | None]] = field(default_factory=list)
    # Para quién es esa orden ("Sra. Bertha"), si el operador lo dijo
    para: str | None = None
    # Un pago de fiado, un gasto o una merma llenados para que el operador los confirme (D-28)
    formulario: dict | None = None
    # Un pedido a un proveedor llenado para que el operador lo confirme (Compras)
    pedido: dict | None = None
    # Hechos que el modelo propone recordar (D-26); el router decide si se guardan
    recuerdos: list[str] = field(default_factory=list)


TEXTO_SI_SOLO_HUBO_FORMULARIO = (
    "Te lo dejé llenado. Revísalo y toca «Guardar»: hasta entonces no se guarda nada."
)
TEXTO_SI_SOLO_HUBO_RECUERDO = "Listo, lo voy a recordar."
TEXTO_SI_SOLO_HUBO_BORRADOR = "Te dejé la orden llenada en Ventas. Revísala y toca «Guardar orden»."


SIN_RECUERDOS = "(todavía nada)"
SIN_PANTALLA = "(no se sabe)"
TITULO_DETALLE = "Botones de esas pantallas (del manual de la app; nómbralos tal cual):"
MAX_EN_PANTALLA = 40


def _describir_pantalla(en_pantalla: EnPantalla | None) -> str:
    if not en_pantalla or not en_pantalla.elementos:
        return SIN_PANTALLA
    return "\n".join(
        f"{clave} = {nombre}" for clave, nombre in list(en_pantalla.elementos.items())[:MAX_EN_PANTALLA]
    )


def armar_mensajes(
    mensaje: str,
    contexto_json: str,
    historial: list[tuple[str, str]],
    recuerdos: list[str] | None = None,
    en_pantalla: EnPantalla | None = None,
    detalle: str = "",
) -> list[dict[str, str]]:
    sistema = PROMPT_SISTEMA.format(
        en_pantalla=_describir_pantalla(en_pantalla),
        detalle=f"\n\n{TITULO_DETALLE}\n{detalle}" if detalle else "",
        guia=GUIA_APP,
        contexto=contexto_json,
        recuerdos="\n".join(f"- {r}" for r in recuerdos) if recuerdos else SIN_RECUERDOS,
        pantallas=", ".join(PANTALLAS),
        apartados="\n".join(f"{clave} = {nombre} ({donde})" for clave, (donde, nombre) in APARTADOS.items()),
    )
    mensajes = [{"role": "system", "content": sistema}]
    for rol, texto in historial[-MAX_TURNOS_PREVIOS:]:
        mensajes.append({"role": "assistant" if rol == "asistente" else "user", "content": texto})
    mensajes.append({"role": "user", "content": mensaje})
    return mensajes


async def preguntar(
    mensaje: str,
    contexto_json: str,
    historial: list[tuple[str, str]] | None = None,
    recuerdos: list[str] | None = None,
    en_pantalla: EnPantalla | None = None,
    detalle: str = "",
) -> RespuestaIA:
    config = configuracion.leer()
    if not config.lista:
        raise AsistenteNoDisponible(
            "El Asistente todavía no está configurado en esta computadora "
            "(falta la variable de entorno NVIDIA_API_KEY)."
        )

    proveedor = ProveedorCompatibleOpenAI(config.url_base, config.api_key)
    mensajes = armar_mensajes(mensaje, contexto_json, historial or [], recuerdos, en_pantalla, detalle)
    # Lo que recuerda también lo dijo el operador (antes): sus cifras no son inventadas
    dicho_por_el_operador = " ".join(
        [mensaje, *(texto for rol, texto in (historial or []) if rol != "asistente"), *(recuerdos or [])]
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
        # Primero lo que propone recordar (D-26), luego las líneas VENTA (ADR-049) y al final las ACCION
        sin_recuerdos, recuerdos_propuestos = memoria.separar(texto)
        sin_borrador, items = borrador.separar(sin_recuerdos)
        sin_para, para = borrador.separar_para(sin_borrador)
        sin_formulario, formulario = formularios.separar(sin_para)
        sin_pedido, pedido_llenado = pedido.separar(sin_formulario)
        limpio, acciones = extraer(sin_pedido, en_pantalla)
        # Un monto inventado nunca llega al operador (ADR-042)
        if cifras_no_respaldadas(limpio, contexto_json, dicho_por_el_operador):
            alguna_cifra_rechazada = True
            registro.warning("Respuesta de %s descartada: monto sin respaldo en los datos", modelo)
            continue
        if not limpio and recuerdos_propuestos and not (items or formulario or pedido_llenado or acciones):
            limpio = TEXTO_SI_SOLO_HUBO_RECUERDO
        if not limpio and (items or formulario or pedido_llenado):
            limpio = TEXTO_SI_SOLO_HUBO_BORRADOR if items else TEXTO_SI_SOLO_HUBO_FORMULARIO
        elif not limpio and acciones:
            limpio = texto_si_solo_hubo_accion(acciones)
        return RespuestaIA(
            texto=limpio or texto,
            modelo=modelo,
            acciones=acciones,
            borrador=items,
            para=para if items else None,
            formulario=formulario,
            pedido=pedido_llenado,
            recuerdos=recuerdos_propuestos,
        )

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


async def consolidar_recuerdos(recuerdos: list[str]) -> list[str]:
    """Pasado el límite, el modelo repiensa qué conservar (D-26). Sin modelo, quedan los más nuevos."""
    config = configuracion.leer()
    if not config.lista or not config.modelos:
        return recuerdos[-memoria.RECUERDOS_TRAS_CONSOLIDAR :]
    proveedor = ProveedorCompatibleOpenAI(config.url_base, config.api_key)
    return await memoria.consolidar(recuerdos, proveedor, config.modelos[0], config.tiempo_limite)

"""Acciones que el Asistente puede SUGERIR (ADR-037). Nunca las ejecuta.

El modelo termina su respuesta con una línea como `ACCION: ir_a ventas` y
aquí se convierte en un botón con texto completo ("Ir a Ventas") que el
operador decide tocar. Con `ACCION: resaltar compras.nuevo-pedido` señala una
parte de la pantalla: la app la trae a la vista y la marca unos segundos
(ADR-047). Si el operador pidió ir o hacer algo, la app lo hace sola; nunca
llena ni guarda datos. Se eligió una línea de texto y no "tool calling"
porque los modelos muy pequeños que correrán en el dispositivo la siguen de
forma más confiable, y es trivial de enseñar con fine-tuning.

Solo se aceptan pantallas y apartados de una lista blanca: lo que el modelo
invente se descarta en silencio.
"""

import re

PANTALLAS = {
    "caja": "Ir a la Caja de hoy",
    "ventas": "Ir a Ventas",
    "fiados": "Ir a Fiados",
    "compras": "Ir a Compras",
    "inventario": "Ir a Inventario",
    "gastos": "Ir a Gastos",
    "analisis": "Ir a ¿Cómo me va?",
}

# Partes de la pantalla que el Asistente puede señalar. La clave es el `data-ai-id` real del
# elemento (frontend); el valor, su pantalla y cómo se nombra en el botón "Muéstrame …".
# Solo lo que se ve al abrir la pantalla: un formulario cerrado no se puede señalar.
APARTADOS = {
    "dashboard.accesos": ("caja", "qué puedes hacer"),
    "dashboard.ventas-hoy": ("caja", "lo que vendiste hoy"),
    "dashboard.proyeccion-manana": ("caja", "lo que necesitas mañana"),
    "dashboard.ordenes-activas": ("caja", "las órdenes abiertas"),
    "dashboard.fiados": ("caja", "los fiados por cobrar"),
    "dashboard.pedidos-por-llegar": ("caja", "los pedidos por llegar"),
    "ventas.nueva": ("ventas", "el botón Nueva orden"),
    "ventas.nuevo-fiado": ("ventas", "el botón Nuevo fiado"),
    "ventas.rapida": ("ventas", "el botón Venta rápida"),
    "ventas.ordenes": ("ventas", "las órdenes abiertas"),
    "ventas.rapidas": ("ventas", "las ventas rápidas por completar"),
    "fiados.total": ("fiados", "lo que te deben en total"),
    "compras.nuevo-pedido": ("compras", "el botón Nuevo pedido"),
    "inventario.nuevo-producto": ("inventario", "el botón Nuevo producto"),
    "dashboard.en-caja": ("caja", "cuánto hay en caja ahora"),
    "gastos.anotar": ("gastos", "el botón Anotar un gasto"),
    "inventario.buscar": ("inventario", "el buscador de productos"),
    "inventario.solo-poco": ("inventario", "el botón de lo que se está acabando"),
}

MAX_ACCIONES = 2

# Red de seguridad: si el modelo no escribió la línea ACCION pero sí indicó una
# pantalla ("ve a la pantalla fiados"), igual se ofrece el botón. Los modelos
# muy pequeños olvidan el formato más que el contenido.
_MENCION = re.compile(
    r"\b(?:pantalla|secci[oó]n|men[uú])\s+(?:de\s+)?(?:la\s+|los\s+)?[«\"']?(?P<destino>fiados|ventas|caja|compras|inventario|gastos|analisis)\b",
    re.IGNORECASE,
)

_LINEA = re.compile(
    # Sin ancla al inicio: algunos modelos la pegan al final de la última frase
    # Sin tipo ("ACCION: ventas", visto el 2026-11-08) se entiende "ir_a"
    r"\s*\bACCI[OÓ]N\s*:\s*(?:(?P<tipo>\w+)\s+)?(?P<destino>[\wáéíóú.-]+?)\s*\.?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Red final: ninguna línea de control llega al operador, aunque venga mal escrita
_LINEA_DE_CONTROL = re.compile(
    r"^[ \t]*(?:ACCI[OÓ]N|VENTA|PARA|COMPRA|PROVEEDOR|RECORDAR|ABONO|GASTO|MERMA)[ \t]*:.*$",
    re.IGNORECASE | re.MULTILINE,
)


# El operador pide ir a algún lado o hacer algo ("quiero registrar una compra", "llévame a
# fiados"): ahí la app abre la pantalla sola, con el Asistente a la vista (ADR-047). Lo decide
# esta regla fija sobre lo que escribió el operador, nunca el modelo; una pregunta como
# "¿cuánto debe Flora?" solo deja el botón.
_PIDE_IR_O_HACER = re.compile(
    # Sin "necesito": "¿cuánto necesito en caja mañana?" es una pregunta, no un pedido de ir
    r"\b(?:quiero|quisiera|vamos|ll[eé]vame|abre|[aá]breme|mu[eé]strame|ir\s+a|voy\s+a|"
    # Toda forma del verbo: "registrar", "anota", "regístrala por mí", "¿cómo registro…?" (también
    # pide hacerlo). Sin "vendí": "¿cuánto vendí hoy?" es una pregunta de cifras
    # El pasado no es un pedido: "dime que ya registraste…" no lleva a ningún lado
    r"(?:reg[ií]str|an[oó]t|agr[eé]g|ap[uú]nt|c[oó]br|revis)(?!aste\b|é\b|ó\b)\w*|"
    r"h[aá]z(?:lo|la|me)\w*|h[aá]cel[oa]\w*|contar|"
    # Pedidos a un proveedor: "pídele a…", "encárgale…", "haz un pedido". Sin "pedí" ni "compras":
    # "¿qué le pedí?" y "¿qué compras tengo?" son preguntas
    r"p[ií]de(?:le|les|me)|ped[ií]rle|enc[aá]rg(?:a|ale|ales|ar|arle)|c[oó]mpra(?:le|les|me)|"
    r"h[aá]z\s+un\s+pedido)\b",
    re.IGNORECASE,
)


# El operador pregunta dónde está algo o qué tocar: ahí la app lo lleva y, si hay, lo señala sola.
_PREGUNTA_DONDE = re.compile(
    r"\b(?:d[oó]nde|cu[aá]l\s+bot[oó]n|qu[eé]\s+(?:bot[oó]n|toco|aprieto)|en\s+qu[eé]\s+parte|"
    r"mu[eé]strame|se[nñ][aá]lame)\b",
    re.IGNORECASE,
)


def pide_ir_o_hacer(mensaje_del_operador: str) -> bool:
    """El operador pidió ir a algún lado o hacer algo (no solo preguntó)."""
    return bool(_PIDE_IR_O_HACER.search(mensaje_del_operador))


# El modelo a veces manda a la Caja de hoy lo que vive en otra pantalla ("quiero ver quiénes me
# deben" → caja, visto en ia.evaluar). La Caja solo resume: si el mensaje habla claramente de un
# tema con pantalla propia, el "Ir a la Caja" se corrige hacia esa pantalla.
_TEMA_CON_PANTALLA = [
    (re.compile(r"\b(?:me\s+deben|deud\w*|fiad\w*|abon\w*)\b", re.IGNORECASE), "fiados"),
    (re.compile(r"\b(?:proveedor\w*|pedido\w*|compra\w*)\b", re.IGNORECASE), "compras"),
    (re.compile(r"\b(?:stock|inventario|me\s+queda\w*|merma\w*)\b", re.IGNORECASE), "inventario"),
    (re.compile(r"\b(?:gast\w*|alquiler|pasaje\w*)\b", re.IGNORECASE), "gastos"),
    (re.compile(r"\b(?:semana|mes|rentable|ganancia\w*|gan[eé]|ganado|libre)\b", re.IGNORECASE), "analisis"),
]


def corregir_destino(mensaje_del_operador: str, acciones: list[dict]) -> list[dict]:
    """Cambia una acción hacia la Caja de hoy ("Ir a la Caja" o señalar una de sus tarjetas, que
    solo resumen) por la pantalla del tema del mensaje, si es una sola."""
    temas = {pantalla for patron, pantalla in _TEMA_CON_PANTALLA if patron.search(mensaje_del_operador)}
    if len(temas) != 1:
        return acciones
    (destino,) = temas
    if any(a["pantalla"] == destino for a in acciones):
        return acciones
    hacia_el_tema = {"tipo": "ir_a", "pantalla": destino, "etiqueta": PANTALLAS[destino]}
    return [dict(hacia_el_tema) if a["pantalla"] == "caja" else a for a in acciones]


# Para cuando el operador pide HACER algo y el modelo no propuso pantalla ("quiero registrar una
# compra" → explicó los pasos sin la línea ACCION). Aquí sí entra Ventas: en una corrección de la
# Caja no, porque "mis ventas de hoy" sí se ven en la Caja.
_TEMA_PARA_HACER = [
    (re.compile(r"\b(?:venta\w*|vender|orden\w*)\b", re.IGNORECASE), "ventas"),
    *_TEMA_CON_PANTALLA,
]


def accion_por_tema(mensaje_del_operador: str, acciones: list[dict]) -> list[dict]:
    """Si el operador pidió hacer algo y no hay ninguna acción, ofrece la pantalla de su tema
    (solo si el tema es uno solo: con dos, no se adivina)."""
    if acciones or not pide_ir_o_hacer(mensaje_del_operador):
        return acciones
    temas = {pantalla for patron, pantalla in _TEMA_PARA_HACER if patron.search(mensaje_del_operador)}
    if len(temas) != 1:
        return acciones
    (destino,) = temas
    return [{"tipo": "ir_a", "pantalla": destino, "etiqueta": PANTALLAS[destino]}]


def marcar_automatica(mensaje_del_operador: str, acciones: list[dict]) -> list[dict]:
    """Marca la primera acción como `automatica` (la app la hace sola) si el operador pidió ir
    o hacer algo, o si preguntó dónde está algo o qué tocar.

    Solo navegar y marcar: no cambia ningún dato. El Asistente sigue sin registrar nada por su
    cuenta (ADR-037). Si el modelo agrega una acción a una pregunta de cifras, queda como botón.
    """
    marcadas = [{**accion, "automatica": False} for accion in acciones]
    if not marcadas:
        return marcadas
    marcadas[0]["automatica"] = bool(
        _PIDE_IR_O_HACER.search(mensaje_del_operador) or _PREGUNTA_DONDE.search(mensaje_del_operador)
    )
    return marcadas


def texto_si_solo_hubo_accion(acciones: list[dict[str, str]]) -> str:
    """Algunos modelos responden SOLO con la línea ACCION. El operador nunca debe ver esa
    línea: se le dice en palabras a dónde mirar."""
    primera = acciones[0]
    if primera["tipo"] == "resaltar":
        return f"Mira aquí: {primera['etiqueta'].removeprefix('Muéstrame ')}."
    return f"Lo encuentras en {primera['etiqueta'].removeprefix('Ir a ')}."


def _resaltar(apartado: str, en_pantalla: "EnPantalla | None" = None) -> dict[str, str]:
    if apartado in APARTADOS:
        pantalla, nombre = APARTADOS[apartado]
    else:  # algo que el operador tiene a la vista ahora (Fase 6: lectura de la pantalla)
        pantalla, nombre = en_pantalla.pantalla, f"«{en_pantalla.elementos[apartado]}»"
    return {"tipo": "resaltar", "pantalla": pantalla, "etiqueta": f"Muéstrame {nombre}", "apartado": apartado}


class EnPantalla:
    """Lo que el operador tiene a la vista ahora: su pantalla y sus partes (data-ai-id → cómo se
    llaman). El Asistente puede señalar cualquiera de ellas, además de la lista blanca: existen."""

    def __init__(self, pantalla: str, elementos: dict[str, str]) -> None:
        self.pantalla = pantalla
        self.elementos = elementos


def extraer(texto: str, en_pantalla: EnPantalla | None = None) -> tuple[str, list[dict[str, str]]]:
    """Separa las líneas ACCION del texto y devuelve (texto limpio, acciones válidas).

    Una sola acción por pantalla: señalar un apartado ya lleva a su pantalla, así que
    reemplaza al "Ir a" de esa misma pantalla. Se puede señalar un apartado de la lista blanca
    o algo que el operador tiene a la vista ahora (`en_pantalla`); nada inventado.
    """
    a_la_vista = en_pantalla.elementos if en_pantalla and en_pantalla.pantalla in PANTALLAS else {}
    acciones: list[dict[str, str]] = []
    for coincidencia in _LINEA.finditer(texto):
        tipo = (coincidencia["tipo"] or "ir_a").lower()
        destino = coincidencia["destino"].lower()
        if tipo == "ir_a" and destino in PANTALLAS and all(a["pantalla"] != destino for a in acciones):
            acciones.append({"tipo": "ir_a", "pantalla": destino, "etiqueta": PANTALLAS[destino]})
        elif tipo == "resaltar" and (destino in APARTADOS or destino in a_la_vista):
            nueva = _resaltar(destino, en_pantalla)
            previa = next((i for i, a in enumerate(acciones) if a["pantalla"] == nueva["pantalla"]), None)
            if previa is None:
                acciones.append(nueva)
            elif acciones[previa]["tipo"] == "ir_a":
                acciones[previa] = nueva
    limpio = _LINEA_DE_CONTROL.sub("", _LINEA.sub("", texto))
    limpio = re.sub(r"\n{3,}", "\n\n", limpio).strip()
    if not acciones:
        for mencion in _MENCION.finditer(limpio):
            destino = mencion["destino"].lower()
            if all(a["pantalla"] != destino for a in acciones):
                acciones.append({"tipo": "ir_a", "pantalla": destino, "etiqueta": PANTALLAS[destino]})
    return limpio, acciones[:MAX_ACCIONES]

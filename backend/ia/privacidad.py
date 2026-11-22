"""Seudonimización del contexto que sale hacia un proveedor de IA (ADR-034).

Nombres de clientes y proveedores son datos personales (Ley 29733). Antes de
enviar el resumen a un servicio externo se reemplazan por alias ("Cliente 1",
"Proveedor A") y la respuesta se re-identifica aquí, en la computadora del
vendedor. El modelo nunca ve un nombre real; el operador sí lo lee.

La misma tabla de alias se aplica a la pregunta: "¿cuánto debe la Sra.
Flora?" viaja como "¿cuánto debe Cliente 1?".
"""

import re
from string import ascii_uppercase

# Rótulos genéricos que la app genera y que no identifican a nadie
NO_PERSONALES = re.compile(r"^Orden \d+$")

# Formas de decir el mismo tratamiento: "Sra. Rosa" también llega como "señora Rosa" o "doña Rosa"
_FEMENINO = ("sra.", "sra", "señora", "senora", "doña", "dona")
_MASCULINO = ("sr.", "sr", "señor", "senor", "don")
_TRATAMIENTOS = {forma: grupo for grupo in (_FEMENINO, _MASCULINO) for forma in grupo}


def _formas_de(nombre: str) -> list[str]:
    """El nombre tal como está guardado y, si empieza con un tratamiento, sus otras formas."""
    partes = nombre.split(maxsplit=1)
    grupo = _TRATAMIENTOS.get(partes[0].lower()) if len(partes) == 2 else None
    if grupo is None:
        return [nombre]
    return [nombre, *(f"{forma} {partes[1]}" for forma in grupo)]


def _patron(forma: str) -> str:
    """La forma como palabra entera, con cualquier cantidad de espacios entre sus partes."""
    return r"(?<!\w)" + r"\s+".join(re.escape(p) for p in forma.split()) + r"(?!\w)"


def _aparece(forma: str, texto: str) -> bool:
    return bool(re.search(_patron(forma), texto, flags=re.IGNORECASE))


# Lo que queda de un alias que no se pudo devolver a su nombre real
ALIAS_SUELTO = re.compile(r"\b(?:Cliente \d+|Proveedor [A-Z]\d*)\b")


class Seudonimos:
    def __init__(self) -> None:
        self._alias: dict[str, str] = {}  # nombre real → alias
        self._clientes = 0
        self._proveedores = 0

    def cliente(self, nombre: str) -> str:
        if NO_PERSONALES.match(nombre):
            return nombre
        if nombre not in self._alias:
            self._clientes += 1
            self._alias[nombre] = f"Cliente {self._clientes}"
        return self._alias[nombre]

    def proveedor(self, nombre: str) -> str:
        if nombre not in self._alias:
            letra = ascii_uppercase[self._proveedores % 26]
            vuelta = self._proveedores // 26
            self._proveedores += 1
            self._alias[nombre] = f"Proveedor {letra}{vuelta or ''}"
        return self._alias[nombre]

    def registrar_mencionados(self, texto: str, clientes: list[str], proveedores: list[str]) -> None:
        """Da alias a los clientes y proveedores guardados que aparecen en `texto`.

        El resumen solo trae a quien tiene una orden abierta o está entre los que más deben. Un
        recuerdo ("la Sra. Lucía paga los viernes") o una pregunta pueden nombrar a cualquier otro:
        sin esto, ese nombre viajaría tal cual al proveedor de IA (D-26).
        """
        candidatos = [*((c, self.cliente) for c in clientes), *((p, self.proveedor) for p in proveedores)]
        for nombre, dar_alias in candidatos:
            if nombre in self._alias or not nombre.strip():
                continue
            if any(_aparece(forma, texto) for forma in _formas_de(nombre)):
                dar_alias(nombre)

    def ocultar_en_texto(self, texto: str) -> str:
        """Reemplaza en texto libre (la pregunta) cada nombre conocido por su alias.

        La gente no escribe el nombre como está guardado: "Sra. Rosa" llega como "señora Rosa",
        "sra rosa" o "doña Rosa". Se reconocen esas formas del tratamiento (D-28: sin esto el
        modelo veía el nombre real y llenaba el pago a otro cliente). El nombre solo, sin
        tratamiento, no se toca: "rosa" también es un color.
        """
        variantes = [(forma, alias) for real, alias in self._alias.items() for forma in _formas_de(real)]
        # Primero las formas largas: "Sra. Flora Quispe" antes que "Flora"
        for forma, alias in sorted(variantes, key=lambda par: len(par[0]), reverse=True):
            texto = re.sub(_patron(forma), alias, texto, flags=re.IGNORECASE)
        return texto

    def reidentificar(self, texto: str) -> str:
        """Devuelve los nombres reales en la respuesta del modelo.

        El modelo suele escribir "el Cliente 1" o "al Cliente 1": con el nombre
        real eso daría "el Sra. Flora". El artículo se ajusta al restituir:
        "el/la X" → "X", "al X" → "a X", "del X" → "de X".
        """
        # "Cliente 12" antes que "Cliente 1" para no cortar el número
        for real, alias in sorted(self._alias.items(), key=lambda par: len(par[1]), reverse=True):
            patron = rf"\b(?:(?P<art>el|la|al|del)\s+)?{re.escape(alias)}\b"

            def poner_nombre(coincidencia: re.Match, real: str = real) -> str:
                articulo = coincidencia["art"] or ""
                prefijo = {"al": "a ", "del": "de "}.get(articulo.lower(), "")
                if prefijo and articulo[0].isupper():
                    prefijo = prefijo.capitalize()
                return prefijo + real

            texto = re.sub(patron, poner_nombre, texto, flags=re.IGNORECASE)
        return texto


def seudonimizar_resumen(resumen: dict) -> tuple[dict, Seudonimos]:
    """Copia del resumen del Dashboard con los nombres reemplazados por alias."""
    alias = Seudonimos()
    copia = dict(resumen)
    # Sin uuid ni id: al modelo no le sirven y un uuid es un identificador más que no debe salir
    copia["ordenes_activas"] = [
        {**{k: v for k, v in orden.items() if k != "uuid"}, "nombre": alias.cliente(orden["nombre"])}
        for orden in resumen.get("ordenes_activas", [])
    ]
    copia["pedidos_por_llegar"] = [
        {
            **{k: v for k, v in pedido.items() if k != "uuid"},
            "proveedor": alias.proveedor(pedido["proveedor"]),
        }
        for pedido in resumen.get("pedidos_por_llegar", [])
    ]
    if "clientes_que_deben" in resumen:
        copia["clientes_que_deben"] = [
            {**cliente, "nombre": alias.cliente(cliente["nombre"])}
            for cliente in resumen["clientes_que_deben"]
        ]
    motivo = resumen.get("motivo_proyeccion", "")
    copia["motivo_proyeccion"] = alias.ocultar_en_texto(motivo)
    return copia, alias

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

    def ocultar_en_texto(self, texto: str) -> str:
        """Reemplaza en texto libre (la pregunta) cada nombre conocido por su alias."""
        # Primero los nombres largos: "Sra. Flora Quispe" antes que "Flora"
        for real in sorted(self._alias, key=len, reverse=True):
            texto = re.sub(re.escape(real), self._alias[real], texto, flags=re.IGNORECASE)
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
    copia["ordenes_activas"] = [
        {**orden, "nombre": alias.cliente(orden["nombre"])} for orden in resumen.get("ordenes_activas", [])
    ]
    copia["pedidos_por_llegar"] = [
        {**pedido, "proveedor": alias.proveedor(pedido["proveedor"])}
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

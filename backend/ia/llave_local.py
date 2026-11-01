"""Llave del proveedor de IA guardada en el dispositivo del vendedor (D-14, ADR-043).

Un vendedor no sabe configurar variables de entorno, así que el `.exe` le pide la
llave en pantalla. Reglas que este archivo hace cumplir:

- Se guarda cifrada con DPAPI de Windows, ligada a la cuenta de Windows: copiar el
  archivo a otra computadora o abrirlo con otro usuario no sirve de nada.
- Fuera de Windows no se guarda nunca en claro: ahí sigue siendo variable de entorno.
- Vive en la carpeta de datos (`ia_llave.dpapi`), nunca en el repo: `*.dpapi` está en
  `.gitignore` y lo vigila el test de higiene.
- Ningún endpoint la devuelve, ni los mensajes de error la repiten.
"""

import ctypes
import logging
import sys

import httpx

import rutas

ARCHIVO = "ia_llave.dpapi"
LARGO_MINIMO = 20
LARGO_MAXIMO = 300
TIEMPO_PRUEBA = 15.0
# Distingue este uso de otros datos cifrados por la misma cuenta de Windows
_ENTROPIA = b"mi-puestito.ia.llave.v1"

registro = logging.getLogger("mi_puestito.ia")


class _Blob(ctypes.Structure):
    _fields_ = [("largo", ctypes.c_uint32), ("datos", ctypes.POINTER(ctypes.c_char))]


def _blob(bytes_: bytes) -> tuple[_Blob, ctypes.Array]:
    # Se devuelve también el búfer: si se libera, el puntero del blob queda colgando
    bufer = ctypes.create_string_buffer(bytes_, len(bytes_))
    return _Blob(len(bytes_), ctypes.cast(bufer, ctypes.POINTER(ctypes.c_char))), bufer


def _llamar_dpapi(funcion, entrada: bytes) -> bytes:
    bloque, _bufer = _blob(entrada)
    entropia, _bufer_entropia = _blob(_ENTROPIA)
    salida = _Blob()
    # Sin UI: es un servicio en segundo plano, nunca debe abrir un diálogo de Windows
    CRYPTPROTECT_UI_FORBIDDEN = 0x1
    if not funcion(
        ctypes.byref(bloque), None, ctypes.byref(entropia), None, None,
        CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(salida),
    ):
        raise OSError("DPAPI no pudo procesar la llave")
    try:
        return ctypes.string_at(salida.datos, salida.largo)
    finally:
        ctypes.windll.kernel32.LocalFree(salida.datos)


def _cifrar(texto: bytes) -> bytes:
    return _llamar_dpapi(ctypes.windll.crypt32.CryptProtectData, texto)


def _descifrar(cifrado: bytes) -> bytes:
    return _llamar_dpapi(ctypes.windll.crypt32.CryptUnprotectData, cifrado)


def disponible() -> bool:
    """¿Este sistema puede guardar la llave de forma segura?"""
    return sys.platform == "win32"


def _ruta():
    return rutas.directorio_datos() / ARCHIVO


def guardada() -> bool:
    return disponible() and _ruta().exists()


def leer() -> str | None:
    """La llave guardada, o None. Un archivo dañado o de otra cuenta equivale a no tenerla."""
    if not guardada():
        return None
    try:
        return _descifrar(_ruta().read_bytes()).decode("utf-8")
    except (OSError, ValueError):
        registro.warning("No se pudo leer la llave guardada: habrá que escribirla de nuevo")
        return None


def guardar(llave: str) -> None:
    _ruta().write_bytes(_cifrar(llave.encode("utf-8")))


def borrar() -> None:
    _ruta().unlink(missing_ok=True)


async def rechazada_por_el_proveedor(llave: str, url_base: str, modelo: str) -> bool:
    """True solo si el proveedor dice que la llave no vale.

    Sin red o con un modelo caído no se sabe: la llave se guarda igual y el operador
    verá el problema real al preguntar. La prueba es un saludo: no lleva datos del negocio.
    """
    try:
        async with httpx.AsyncClient(timeout=TIEMPO_PRUEBA) as cliente:
            respuesta = await cliente.post(
                f"{url_base}/chat/completions",
                headers={"Authorization": f"Bearer {llave}"},
                json={"model": modelo, "messages": [{"role": "user", "content": "Hola"}], "max_tokens": 1},
            )
    except httpx.HTTPError:
        return False
    return respuesta.status_code in (401, 403)

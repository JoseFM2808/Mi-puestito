"""Rutas de recursos y de datos, iguales en desarrollo y en el ejecutable.

Al empaquetar con PyInstaller la aplicación corre desde una carpeta temporal
(`sys._MEIPASS`) y, en Windows, el .exe puede estar en una ubicación de solo
lectura. Por eso los archivos que se leen (frontend) y los que se escriben
(base de datos) viven en lugares distintos.
"""

import os
import sys
from pathlib import Path

NOMBRE_APP = "MiPuestito"


def es_ejecutable() -> bool:
    """True cuando corre dentro del ejecutable empaquetado."""
    return getattr(sys, "frozen", False)


def directorio_recursos() -> Path:
    """Carpeta con los archivos empaquetados (frontend ya construido)."""
    if es_ejecutable():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent


def directorio_web() -> Path:
    """Frontend construido (`frontend/dist`) que se sirve como sitio."""
    if es_ejecutable():
        return directorio_recursos() / "web"
    return Path(__file__).resolve().parent.parent / "frontend" / "dist"


def directorio_datos() -> Path:
    """Carpeta donde se guardan los datos del vendedor.

    Nunca junto al ejecutable: en Windows va a %LOCALAPPDATA%\\MiPuestito para
    que funcione aunque la app esté instalada en una carpeta protegida, y para
    que los datos sobrevivan al reemplazar el .exe por una versión nueva.

    `MI_PUESTITO_DATOS` la fija a mano: Staging la usa para que las bases de
    prueba no queden dentro de la carpeta del repo (que puede estar en Drive).
    """
    forzada = os.environ.get("MI_PUESTITO_DATOS")
    if forzada:
        carpeta = Path(forzada)
        carpeta.mkdir(parents=True, exist_ok=True)
        return carpeta

    if not es_ejecutable():
        return Path(__file__).resolve().parent

    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    carpeta = base / NOMBRE_APP
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def ruta_base_datos(proyecto: str) -> Path:
    """Cada proyecto (demo / anita) tiene su propio archivo de base de datos.

    Nunca comparten archivo: un proyecto de práctica no debe poder mezclar
    ni un solo registro con los datos reales de una empresa.
    """
    return directorio_datos() / f"mi_puestito_{proyecto}.db"


def ruta_usuarios() -> Path:
    """Archivo con las credenciales de acceso (PIN con hash, nunca en claro)."""
    return directorio_datos() / "usuarios.json"

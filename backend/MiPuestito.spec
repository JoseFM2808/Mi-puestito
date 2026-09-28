# -*- mode: python ; coding: utf-8 -*-
"""Receta de empaquetado (PyInstaller) del ejecutable de Mi Puestito.

Genera UN solo archivo que incluye el intérprete de Python, el backend y el
frontend ya construido. El usuario final no instala nada.

    cd frontend && npm ci && npm run build
    cd backend  && pyinstaller MiPuestito.spec --noconfirm

En Windows produce dist/MiPuestito.exe
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

RAIZ = Path(SPECPATH).parent
# collect_submodules importa los paquetes para listarlos: sin el backend en
# sys.path devuelve [] en silencio y el .exe arranca con TODOS los módulos
# degradados (/api/salud sigue diciendo "ok").
sys.path.insert(0, str(RAIZ / "backend"))
WEB = RAIZ / "frontend" / "dist"

if not WEB.is_dir():
    raise SystemExit(
        "Falta el frontend construido. Ejecuta primero:\n"
        "  cd frontend && npm ci && npm run build"
    )

analisis = Analysis(
    ["escritorio.py"],
    pathex=[str(RAIZ / "backend")],
    binaries=[],
    # El frontend construido viaja dentro del ejecutable, en la carpeta "web"
    datas=[(str(WEB), "web")],
    hiddenimports=[
        # Uvicorn carga estos por nombre; sin declararlos no entran al paquete
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        # Base de zonas horarias: Windows no la trae (ZoneInfo("America/Lima"))
        "tzdata",
    ]
    # main.py importa los módulos por nombre (importlib), así que PyInstaller
    # no los ve: una lista a mano se quedó sin auth ni asistente y el .exe
    # arrancaba sin login. Se recogen todos los submódulos automáticamente.
    + collect_submodules("modules")
    + collect_submodules("ia"),
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "pytest"],
    noarchive=False,
)

pyz = PYZ(analisis.pure)

exe = EXE(
    pyz,
    analisis.scripts,
    analisis.binaries,
    analisis.datas,
    [],
    name="MiPuestito",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,  # muestra la dirección y dónde se guardan los datos
    disable_windowed_traceback=False,
    icon=str(RAIZ / "frontend" / "public" / "icono.ico")
    if (RAIZ / "frontend" / "public" / "icono.ico").exists()
    else None,
)

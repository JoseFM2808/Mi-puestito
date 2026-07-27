# -*- mode: python ; coding: utf-8 -*-
"""Receta de empaquetado (PyInstaller) del ejecutable de Mi Puestito.

Genera UN solo archivo que incluye el intérprete de Python, el backend y el
frontend ya construido. El usuario final no instala nada.

    cd frontend && npm ci && npm run build
    cd backend  && pyinstaller MiPuestito.spec --noconfirm

En Windows produce dist/MiPuestito.exe
"""

from pathlib import Path

RAIZ = Path(SPECPATH).parent
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
        # Los módulos del backend se importan desde main.py
        "modules.compras.models",
        "modules.compras.router",
        "modules.dashboard.router",
        "modules.ventas.models",
        "modules.ventas.router",
    ],
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

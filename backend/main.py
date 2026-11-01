"""Punto de entrada del backend de Mi Puestito.

Arranque en desarrollo:  uvicorn main:app --reload
Cada módulo vive en modules/<nombre>/ con router, modelos, esquemas y README
propios. El fallo de un módulo no debe derribar a los demás.
"""

import importlib
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import eventos
from database import migrar_todos_los_proyectos
from datos_demo import cargar_si_vacio as cargar_datos_demo
from rutas import directorio_web
from seguridad import asegurar_usuarios_iniciales

# Módulos que se montan al arrancar. Cada entrada es independiente: si uno
# falla al importarse, los demás siguen operativos (ver cargar_modulos).
# "auth" va sin autenticar (es la puerta de entrada); los demás exigen login.
MODULOS = ("auth", "dashboard", "ventas", "compras", "inventario", "asistente", "respaldo")

# Módulos que no pudieron cargarse, para que el Dashboard informe la degradación
modulos_degradados: dict[str, str] = {}


def cargar_modulos(app: FastAPI) -> None:
    """Monta cada módulo por separado.

    Regla no negociable del proyecto: el fallo de un módulo no derriba a otro.
    Si Ventas no puede importarse, Compras, el Dashboard y /api/salud siguen
    respondiendo, y el módulo caído queda anotado en `modulos_degradados`.
    """
    for nombre in MODULOS:
        try:
            # Importar los modelos registra las tablas del módulo (si tiene)
            try:
                importlib.import_module(f"modules.{nombre}.models")
            except ModuleNotFoundError:
                pass  # El Dashboard no tiene tablas propias: agrega las de otros
            modulo = importlib.import_module(f"modules.{nombre}.router")
            app.include_router(modulo.router)
        except Exception as error:  # noqa: BLE001 — aislar es justamente el punto
            modulos_degradados[nombre] = str(error)
            print(f"AVISO: el módulo '{nombre}' no pudo cargarse: {error}")


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    # Cada proyecto se lleva a la última versión del esquema (Alembic, D-03)
    migrar_todos_los_proyectos()
    # Demo trae datos de muestra; un proyecto real arranca vacío
    try:
        cargar_datos_demo()
    except Exception as error:  # noqa: BLE001 — sin muestra, la app igual arranca
        print(f"AVISO: no se pudieron cargar los datos de demo: {error}")
    asegurar_usuarios_iniciales()
    yield


app = FastAPI(
    title="Mi Puestito",
    description="Gestión de ventas, compras y caja para pequeños vendedores",
    version="0.1.0",
    lifespan=ciclo_de_vida,
)

# CORS para el dev server de Vite; en producción el frontend se sirve junto al API.
# Se puede ajustar con MI_PUESTITO_ORIGENES (lista separada por comas).
ORIGENES_PERMITIDOS = [
    origen.strip()
    for origen in os.environ.get(
        "MI_PUESTITO_ORIGENES", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origen.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES_PERMITIDOS,
    allow_methods=["*"],
    allow_headers=["*"],
)

cargar_modulos(app)


@app.get("/api/salud", tags=["salud"])
def salud():
    """Comprobación de vida del servicio.

    Informa qué módulos quedaron degradados: el servicio responde "ok" aunque
    alguno haya fallado, porque los demás siguen sirviendo.
    """
    return {
        "estado": "ok",
        "modulos_degradados": sorted(modulos_degradados),
        # Suscriptores que fallaron (p. ej. Inventario no pudo descontar stock)
        "eventos_con_fallas": sorted(eventos.fallos),
    }


# El frontend construido se sirve desde el mismo servidor: así la aplicación
# de escritorio abre una sola dirección y funciona sin internet. En desarrollo
# se usa el dev server de Vite y esta carpeta puede no existir todavía.
# Va al final para no tapar las rutas /api.
_web = directorio_web()
if _web.is_dir():
    # Los archivos con extensión (JS, CSS, imágenes) se sirven tal cual
    app.mount("/assets", StaticFiles(directory=_web / "assets"), name="assets")

    @app.get("/{ruta_completa:path}", include_in_schema=False)
    def servir_aplicacion(ruta_completa: str):
        """Sirve el archivo pedido y, si no existe, la aplicación.

        El frontend es una sola página: recargar o entrar directo a /ventas
        debe devolver la aplicación, no un 404. Las rutas /api nunca llegan
        aquí porque se registraron antes.
        """
        candidato = (_web / ruta_completa).resolve()
        # resolve() + is_relative_to evita salir de la carpeta web con ".."
        if ruta_completa and candidato.is_file() and candidato.is_relative_to(_web.resolve()):
            return FileResponse(candidato)
        return FileResponse(_web / "index.html")

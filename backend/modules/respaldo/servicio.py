"""Respaldo y restauración del archivo de datos del vendedor (Fase 5, ADR-044).

Reglas que este archivo hace cumplir:

1. **La copia es coherente:** usa la API de backup de SQLite, nunca copiar el archivo
   (con WAL, una copia simple puede perder lo último registrado).
2. **Cada copia sabe de qué negocio es:** lleva una tabla `respaldo_info`. Restaurar la
   práctica sobre un negocio real borraría sus ventas; eso se rechaza.
3. **El archivo que llega no es de confianza:** se revisa en una carpeta temporal antes de
   tocar nada. Sin triggers ni vistas, porque el esquema de la app no usa ninguno y
   podrían ejecutar SQL ajeno al abrir la base.
4. **Restaurar no destruye:** antes se guarda una copia de lo actual en `respaldos/`, y si
   algo falla al migrar se vuelve a ella.

Lo que NO va en la copia: los PIN (`usuarios.json`), la llave de IA ni el secreto de
sesión. Son de la instalación, no del negocio.
"""

import shutil
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from alembic.script import ScriptDirectory

import rutas
from database import _url_para, motor_de
from migraciones.ejecutar import configuracion, migrar

TABLA_INFO = "respaldo_info"
TAMANO_MAXIMO = 200 * 1024 * 1024
ESPERA_SEGUNDOS = 30
CABECERA_SQLITE = b"SQLite format 3\x00"
# Sin estas tablas no es una base de Mi Puestito, aunque sea un SQLite sano
TABLAS_NECESARIAS = {"clientes", "ventas", "items_venta", "pagos", "proveedores", "ordenes_compra"}


class ErrorDeRespaldo(Exception):
    def __init__(self, mensaje: str, codigo: int = 400):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


def _exigir_sqlite(proyecto: str) -> None:
    if not _url_para(proyecto).startswith("sqlite"):
        raise ErrorDeRespaldo("El respaldo de archivo solo existe en el programa local.", 409)


def _copiar(origen: Path, destino: Path) -> None:
    """Copia coherente, aunque en ese momento se esté registrando una venta."""
    with (
        closing(sqlite3.connect(origen, timeout=ESPERA_SEGUNDOS)) as de,
        closing(sqlite3.connect(destino, timeout=ESPERA_SEGUNDOS)) as a,
    ):
        de.backup(a)


def _momento() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")


def crear_copia(proyecto: str) -> bytes:
    """El archivo que el vendedor guarda en su USB o en su correo."""
    _exigir_sqlite(proyecto)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as carpeta:
        copia = Path(carpeta) / "copia.db"
        _copiar(rutas.ruta_base_datos(proyecto), copia)
        with closing(sqlite3.connect(copia)) as base:
            base.execute(f"CREATE TABLE {TABLA_INFO} (proyecto TEXT NOT NULL, creado_en TEXT NOT NULL)")
            base.execute(
                f"INSERT INTO {TABLA_INFO} VALUES (?, ?)",
                (proyecto, datetime.now(timezone.utc).isoformat()),
            )
            base.commit()
            # Un solo archivo: sin WAL aparte que se pueda quedar atrás al copiarlo
            base.execute("PRAGMA journal_mode=DELETE")
        return copia.read_bytes()


def _revisar(archivo: Path, proyecto: str) -> None:
    """Lanza ErrorDeRespaldo si el archivo no se debe restaurar. No modifica nada."""
    no_sirve = ErrorDeRespaldo("Ese archivo no es una copia de Mi Puestito.")
    try:
        with closing(sqlite3.connect(archivo)) as base:
            if base.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ErrorDeRespaldo("Esa copia está dañada: no se puede usar.")
            objetos = base.execute("SELECT type, name FROM sqlite_master").fetchall()
            if any(tipo in ("trigger", "view") for tipo, _ in objetos):
                raise no_sirve
            tablas = {nombre for tipo, nombre in objetos if tipo == "table"}
            if not TABLAS_NECESARIAS <= tablas or TABLA_INFO not in tablas or "alembic_version" not in tablas:
                raise no_sirve
            info = base.execute(f"SELECT proyecto FROM {TABLA_INFO}").fetchone()
            revision = base.execute("SELECT version_num FROM alembic_version").fetchone()
    except sqlite3.Error as error:
        raise ErrorDeRespaldo("Esa copia está dañada: no se puede usar.") from error

    if not info or info[0] != proyecto:
        raise ErrorDeRespaldo("Esa copia es de otro negocio: no se puede usar aquí.", 409)
    conocidas = {r.revision for r in ScriptDirectory.from_config(configuracion()).walk_revisions()}
    if not revision or revision[0] not in conocidas:
        raise ErrorDeRespaldo(
            "Esa copia viene de una versión más nueva del programa. Actualiza el programa primero.", 409
        )


def restaurar(proyecto: str, contenido: bytes) -> Path:
    """Reemplaza los datos del proyecto por la copia. Devuelve dónde quedó lo anterior."""
    _exigir_sqlite(proyecto)
    if not contenido.startswith(CABECERA_SQLITE):
        raise ErrorDeRespaldo("Ese archivo no es una copia de Mi Puestito.")

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as carpeta:
        recibido = Path(carpeta) / "recibido.db"
        recibido.write_bytes(contenido)
        _revisar(recibido, proyecto)
        with closing(sqlite3.connect(recibido)) as base:
            base.execute(f"DROP TABLE {TABLA_INFO}")
            base.commit()

        actual = rutas.ruta_base_datos(proyecto)
        carpeta_respaldos = rutas.directorio_datos() / "respaldos"
        carpeta_respaldos.mkdir(exist_ok=True)
        anterior = carpeta_respaldos / f"antes-de-restaurar-{proyecto}-{_momento()}.db"
        _copiar(actual, anterior)

        motor = motor_de(proyecto)
        motor.dispose()  # conexiones abiertas verían la base anterior en su caché
        _copiar(recibido, actual)
        motor.dispose()
        try:
            # Una copia de una versión anterior se lleva al esquema de hoy
            migrar(motor)
        except Exception as error:
            motor.dispose()
            _copiar(anterior, actual)
            motor.dispose()
            mensaje = "No se pudo usar esa copia. Tus datos quedaron como estaban."
            raise ErrorDeRespaldo(mensaje, 409) from error
    return anterior


def espacio_suficiente(tamano: int) -> bool:
    """Evita empezar una restauración que se quedaría a medias por falta de disco."""
    return shutil.disk_usage(rutas.directorio_datos()).free > tamano * 3

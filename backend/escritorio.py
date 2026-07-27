"""Aplicación de escritorio: arranca el servidor y abre la app en el navegador.

Este es el punto de entrada del ejecutable (`MiPuestito.exe`). El usuario hace
doble clic y ve su caja: no hay que instalar Python, ni Node, ni configurar
nada. Todo corre en la propia computadora, sin internet.
"""

import socket
import sys
import threading
import time
import webbrowser

import uvicorn

from main import app
from rutas import directorio_datos, directorio_web, ruta_base_datos

DIRECCION = "127.0.0.1"


def _archivo_puerto():
    return directorio_datos() / "puerto.txt"


def puerto_disponible(puerto: int) -> bool:
    """True si se puede escuchar en ese puerto ahora mismo."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((DIRECCION, puerto))
            return True
        except OSError:
            return False


def buscar_puerto_libre() -> int:
    """Pide al sistema un puerto disponible (evita chocar con otros programas)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((DIRECCION, 0))
        return s.getsockname()[1]


def obtener_puerto() -> int:
    """Devuelve SIEMPRE el mismo puerto entre arranques.

    El navegador identifica el almacenamiento por origen, y el puerto es parte
    del origen: si cambiara en cada arranque, todo lo guardado sin conexión
    (IndexedDB, preferencias, caché de la PWA) quedaría huérfano al reabrir el
    programa. Por eso el puerto elegido se recuerda; solo se busca otro si
    quedó ocupado por un programa ajeno.
    """
    archivo = _archivo_puerto()
    try:
        guardado = int(archivo.read_text().strip())
        if 1024 < guardado <= 65535 and puerto_disponible(guardado):
            return guardado
    except (OSError, ValueError):
        pass

    puerto = buscar_puerto_libre()
    try:
        archivo.write_text(str(puerto))
    except OSError:
        # Sin permiso de escritura la app sigue funcionando (sin recordar)
        pass
    return puerto


def esperar_servidor(puerto: int, intentos: int = 100) -> bool:
    """Espera a que el servidor acepte conexiones antes de abrir el navegador."""
    for _ in range(intentos):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            if s.connect_ex((DIRECCION, puerto)) == 0:
                return True
        time.sleep(0.1)
    return False


def main() -> int:
    if not directorio_web().is_dir():
        print(
            "No se encontró la interfaz. Si estás en desarrollo, primero:\n"
            "  cd frontend && npm install && npm run build",
            file=sys.stderr,
        )
        return 1

    puerto = obtener_puerto()
    direccion_app = f"http://{DIRECCION}:{puerto}"

    print("Mi Puestito")
    print(f"  Abriendo en: {direccion_app}")
    print(f"  Tus datos se guardan en: {ruta_base_datos()}")
    print("  Para cerrar el programa, cierra esta ventana.")

    # Se pasa la aplicación ya importada (y no "main:app"): dentro del
    # ejecutable empaquetado uvicorn no puede resolver módulos por nombre.
    servidor = uvicorn.Server(
        uvicorn.Config(app, host=DIRECCION, port=puerto, log_level="warning")
    )
    hilo = threading.Thread(target=servidor.run, daemon=True)
    hilo.start()

    if esperar_servidor(puerto):
        webbrowser.open(direccion_app)
    else:
        print("El servidor no respondió a tiempo.", file=sys.stderr)
        return 1

    try:
        while hilo.is_alive():
            hilo.join(timeout=0.5)
    except KeyboardInterrupt:
        print("\nCerrando Mi Puestito…")
        servidor.should_exit = True
        hilo.join(timeout=5)
    return 0


if __name__ == "__main__":
    sys.exit(main())

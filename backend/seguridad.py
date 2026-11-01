"""Login simple por usuario + PIN.

Nada de contraseñas complejas ni registro: el vendedor no tiene experiencia
técnica (AGENTS.md). Cada usuario queda ligado a un único proyecto — entrar
como "anita" da acceso SOLO a los datos de Anita, nunca a los de demo.

Regla del repo: "No almacenar credenciales en el repo". Por eso:
- La cuenta "demo" tiene un PIN fijo y público (0000): no protege nada real.
- La cuenta del proyecto real se genera sola en el primer arranque (o se
  toma de una variable de entorno) y se guarda con hash, nunca en claro.
"""

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from dataclasses import dataclass

from fastapi import Header, HTTPException

from proyectos import proyecto_valido
from rutas import ruta_secreto, ruta_usuarios

PIN_DEMO_FIJO = "0000"
DURACION_TOKEN_SEGUNDOS = 12 * 60 * 60  # una jornada de trabajo

# Límite de intentos (D-04): un PIN de 6 dígitos tiene un millón de
# combinaciones. Tras INTENTOS_LIBRES fallos seguidos, el usuario queda en
# espera, y cada nuevo fallo duplica la espera (tope: ESPERA_MAXIMA).
INTENTOS_LIBRES = 5
ESPERA_INICIAL_SEGUNDOS = 30
ESPERA_MAXIMA_SEGUNDOS = 15 * 60

# "local" = escritorio y desarrollo; "production" = servidor en la nube
ENTORNO = os.environ.get("MI_PUESTITO_ENTORNO", "local").strip().lower()


def _hash_pin(pin: str, sal: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), sal.encode(), 100_000).hex()


def _generar_pin() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _cargar_usuarios() -> dict:
    ruta = ruta_usuarios()
    if ruta.exists():
        return json.loads(ruta.read_text())
    return {}


def _guardar_usuarios(usuarios: dict) -> None:
    ruta_usuarios().write_text(json.dumps(usuarios, indent=2))


def asegurar_usuarios_iniciales() -> None:
    """Crea las cuentas base la primera vez que arranca el programa.

    "demo" siempre con el mismo PIN público. El proyecto real toma su PIN de
    MI_PUESTITO_ANITA_PIN si está definida; si no, genera una al azar y la
    imprime una sola vez para que el dueño del negocio la anote.
    """
    usuarios = _cargar_usuarios()
    cambios = False

    if "demo" not in usuarios:
        sal = secrets.token_hex(16)
        usuarios["demo"] = {
            "proyecto": "demo",
            "sal": sal,
            "pin_hash": _hash_pin(PIN_DEMO_FIJO, sal),
        }
        cambios = True

    if "anita" not in usuarios:
        pin = os.environ.get("MI_PUESTITO_ANITA_PIN")
        if not pin:
            pin = _generar_pin()
            print(
                "\n"
                "==========================================================\n"
                " Se creó el acceso de Anita. PIN de ingreso (guárdalo):\n"
                f"   Usuario: anita   PIN: {pin}\n"
                "==========================================================\n"
            )
        sal = secrets.token_hex(16)
        usuarios["anita"] = {
            "proyecto": "anita",
            "sal": sal,
            "pin_hash": _hash_pin(pin, sal),
        }
        cambios = True

    if cambios:
        _guardar_usuarios(usuarios)


@dataclass
class _Intentos:
    fallos: int = 0
    bloqueado_hasta: float = 0.0


_intentos: dict[str, _Intentos] = {}
_candado_intentos = threading.Lock()


class DemasiadosIntentos(Exception):
    def __init__(self, segundos: int):
        super().__init__(f"espera {segundos} s")
        self.segundos = segundos


def _registrar_fallo(nombre_usuario: str) -> None:
    with _candado_intentos:
        estado = _intentos.setdefault(nombre_usuario, _Intentos())
        estado.fallos += 1
        exceso = estado.fallos - INTENTOS_LIBRES
        if exceso >= 0:
            espera = min(ESPERA_INICIAL_SEGUNDOS * 2**exceso, ESPERA_MAXIMA_SEGUNDOS)
            estado.bloqueado_hasta = time.monotonic() + espera


def verificar_credenciales(nombre_usuario: str, pin: str) -> str | None:
    """Devuelve la clave del proyecto si el PIN es correcto; si no, None.

    Lanza `DemasiadosIntentos` si el usuario está en espera por fallos
    seguidos (el PIN ni se evalúa: no se puede seguir adivinando).
    """
    with _candado_intentos:
        estado = _intentos.get(nombre_usuario)
        if estado is not None and estado.bloqueado_hasta > time.monotonic():
            raise DemasiadosIntentos(int(estado.bloqueado_hasta - time.monotonic()) + 1)

    usuarios = _cargar_usuarios()
    usuario = usuarios.get(nombre_usuario)
    if usuario is None:
        _registrar_fallo(nombre_usuario)
        return None
    calculado = _hash_pin(pin, usuario["sal"])
    if not hmac.compare_digest(calculado, usuario["pin_hash"]):
        _registrar_fallo(nombre_usuario)
        return None
    with _candado_intentos:
        _intentos.pop(nombre_usuario, None)
    return usuario["proyecto"]


def cuentas_registradas() -> list[tuple[str, str]]:
    """(usuario, proyecto) de cada cuenta; demo primero. Sin datos secretos."""
    usuarios = _cargar_usuarios()
    return sorted(
        ((nombre, datos["proyecto"]) for nombre, datos in usuarios.items()),
        key=lambda par: (par[0] != "demo", par[0]),
    )


# ---- Token de sesión ----
# Firmado con HMAC (sin librerías externas): suficiente para una app de
# escritorio de un solo dispositivo, que solo escucha en 127.0.0.1.

LARGO_MINIMO_SECRETO = 32


class ConfiguracionInsegura(RuntimeError):
    """Producción sin un secreto de firma propio: no se arranca."""


def _secreto_de_firma() -> bytes:
    """Llave HMAC de los tokens.

    `or` y no el default de `get`: una variable definida pero vacía (como
    en config/.env.example) devolvería "" y los tokens se firmarían con una
    llave vacía, falsificables por cualquiera.

    En "production" (servidor en la nube, D-09) el secreto es obligatorio: uno
    al azar cerraría todas las sesiones en cada reinicio o despliegue, y uno
    corto se adivina. En "local" (escritorio) se genera una vez y se guarda en la
    carpeta de datos: reiniciar el programa no cierra la sesión del operador (D-13).
    """
    configurado = os.environ.get("MI_PUESTITO_SECRETO") or ""
    if ENTORNO == "production" and len(configurado) < LARGO_MINIMO_SECRETO:
        raise ConfiguracionInsegura(
            f"En producción MI_PUESTITO_SECRETO debe tener al menos {LARGO_MINIMO_SECRETO} "
            'caracteres. Genera uno con: python -c "import secrets; print(secrets.token_hex(32))"'
        )
    return (configurado or _secreto_local()).encode()


def _secreto_local() -> str:
    """El secreto guardado de esta instalación; lo crea la primera vez."""
    ruta = ruta_secreto()
    try:
        guardado = ruta.read_text(encoding="utf-8").strip()
        if len(guardado) >= LARGO_MINIMO_SECRETO:
            return guardado
    except OSError:
        pass
    nuevo = secrets.token_hex(32)
    try:
        ruta.write_text(nuevo, encoding="utf-8")
    except OSError:
        pass  # sin permiso de escritura la app funciona igual: la sesión dura hasta reiniciar
    return nuevo


_SECRETO = _secreto_de_firma()


def crear_token(proyecto: str) -> str:
    vence = int(time.time()) + DURACION_TOKEN_SEGUNDOS
    cuerpo = f"{proyecto}:{vence}"
    firma = hmac.new(_SECRETO, cuerpo.encode(), hashlib.sha256).hexdigest()
    return f"{cuerpo}:{firma}"


@dataclass
class SesionInvalida(Exception):
    motivo: str


def _verificar_token(token: str) -> str:
    try:
        proyecto, vence, firma = token.split(":")
    except ValueError:
        raise SesionInvalida("token con formato inválido") from None

    cuerpo = f"{proyecto}:{vence}"
    firma_esperada = hmac.new(_SECRETO, cuerpo.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(firma, firma_esperada):
        raise SesionInvalida("firma inválida")
    if int(vence) < time.time():
        raise SesionInvalida("la sesión venció, vuelve a ingresar")
    if not proyecto_valido(proyecto):
        raise SesionInvalida("proyecto desconocido")
    return proyecto


def proyecto_autenticado(authorization: str | None = Header(default=None)) -> str:
    """Dependencia de FastAPI: exige `Authorization: Bearer <token>` válido
    y devuelve la clave del proyecto (demo / anita) al que da acceso."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Falta iniciar sesión")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        return _verificar_token(token)
    except SesionInvalida as error:
        raise HTTPException(status_code=401, detail=error.motivo) from error

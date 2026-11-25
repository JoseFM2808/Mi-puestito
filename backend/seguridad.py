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

# "local" = escritorio y desarrollo; "production" = servidor en la nube. En Vercel, si nadie lo dijo,
# es "production": tratarlo como local firmaría las sesiones con una llave distinta por instancia
# y podría mostrar el PIN del primer arranque a quien llegue por el proxy (ADR-058)
ENTORNO = (
    os.environ.get("MI_PUESTITO_ENTORNO") or ("production" if os.environ.get("VERCEL") else "local")
).strip().lower()


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


# PIN generado que la pantalla de ingreso todavía debe mostrar (D-07). Solo en memoria: nunca
# en disco ni en la consola, que puede ir a un log. En usuarios.json queda solo la marca
# "pin_por_mostrar"; si el programa se cierra antes de que el dueño lo anote, al volver a abrir
# se genera otro (el anterior nunca se mostró).
_pines_por_mostrar: dict[str, str] = {}

EQUIPO_LOCAL = {"127.0.0.1", "::1"}


def desde_este_equipo(origen: str | None) -> bool:
    """La petición viene de la misma computadora del programa (no de otra de la red)."""
    return ENTORNO == "local" and (origen or "") in EQUIPO_LOCAL


def _nuevo_pin_por_mostrar(usuarios: dict, nombre_usuario: str, proyecto: str) -> None:
    pin = _generar_pin()
    sal = secrets.token_hex(16)
    usuarios[nombre_usuario] = {
        "proyecto": proyecto,
        "sal": sal,
        "pin_hash": _hash_pin(pin, sal),
        "pin_por_mostrar": True,
    }
    _pines_por_mostrar[nombre_usuario] = pin
    # En un servidor no hay pantalla en "esta computadora": ahí la consola es el único camino
    # (mejor: fijar el PIN con la variable de entorno del negocio)
    como_verlo = (
        " Abre Mi Puestito en esta computadora: la pantalla de\n ingreso te muestra el PIN una sola vez.\n"
        if ENTORNO == "local"
        else f"   Usuario: {nombre_usuario}   PIN: {pin}\n"
    )
    print(
        "\n"
        "==========================================================\n"
        f" Se creó el acceso de {nombre_usuario}.\n"
        f"{como_verlo}"
        "==========================================================\n"
    )


def pines_por_mostrar() -> list[tuple[str, str]]:
    """(usuario, PIN) de las cuentas cuyo PIN generado aún no se anotó."""
    return sorted(_pines_por_mostrar.items())


def marcar_pin_anotado(nombre_usuario: str) -> None:
    """El dueño ya anotó el PIN (o entró con él): no se vuelve a mostrar."""
    _pines_por_mostrar.pop(nombre_usuario, None)
    usuarios = _cargar_usuarios()
    if usuarios.get(nombre_usuario, {}).pop("pin_por_mostrar", None) is not None:
        _guardar_usuarios(usuarios)


def asegurar_usuarios_iniciales() -> None:
    """Crea las cuentas base la primera vez que arranca el programa.

    "demo" siempre con el mismo PIN público. El proyecto real toma su PIN de
    MI_PUESTITO_ANITA_PIN si está definida; si no, genera uno al azar que la
    pantalla de ingreso muestra una sola vez, solo en esta computadora (D-07).

    En la nube (ADR-058) no hay disco que dure ni pantalla en "esta computadora": el PIN del
    negocio real sale SIEMPRE de su variable secreta (se vuelve a leer en cada arranque, así
    cambiarla en Vercel cambia el PIN) y, si falta, esa cuenta no se crea. `MI_PUESTITO_DEMO=0`
    quita la cuenta de práctica.
    """
    usuarios = _cargar_usuarios()
    cambios = False
    if ENTORNO != "local":
        cambios = _cuentas_de_la_nube(usuarios)
        if cambios:
            _guardar_usuarios(usuarios)
        return

    # Un PIN que nunca se llegó a mostrar (el programa se cerró antes) se reemplaza por otro
    for nombre_usuario, datos in list(usuarios.items()):
        if datos.get("pin_por_mostrar") and nombre_usuario not in _pines_por_mostrar:
            _nuevo_pin_por_mostrar(usuarios, nombre_usuario, datos["proyecto"])
            cambios = True

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
        if pin:
            sal = secrets.token_hex(16)
            usuarios["anita"] = {
                "proyecto": "anita",
                "sal": sal,
                "pin_hash": _hash_pin(pin, sal),
            }
        else:
            _nuevo_pin_por_mostrar(usuarios, "anita", "anita")
        cambios = True

    if cambios:
        _guardar_usuarios(usuarios)


def demo_habilitada() -> bool:
    return os.environ.get("MI_PUESTITO_DEMO", "1").strip() not in ("0", "no", "false")


def _cuentas_de_la_nube(usuarios: dict) -> bool:
    """Cuentas en la nube: la práctica si está habilitada y el negocio real con el PIN de su secreto."""
    antes = json.dumps(usuarios, sort_keys=True)
    if demo_habilitada():
        if "demo" not in usuarios:
            sal = secrets.token_hex(16)
            usuarios["demo"] = {"proyecto": "demo", "sal": sal, "pin_hash": _hash_pin(PIN_DEMO_FIJO, sal)}
    else:
        usuarios.pop("demo", None)
    pin = os.environ.get("MI_PUESTITO_ANITA_PIN", "").strip()
    if pin:
        actual = usuarios.get("anita")
        if not actual or not hmac.compare_digest(_hash_pin(pin, actual["sal"]), actual["pin_hash"]):
            sal = secrets.token_hex(16)
            usuarios["anita"] = {"proyecto": "anita", "sal": sal, "pin_hash": _hash_pin(pin, sal)}
    else:
        usuarios.pop("anita", None)
        print("AVISO: falta MI_PUESTITO_ANITA_PIN: la cuenta del negocio real no se puede usar.")
    return json.dumps(usuarios, sort_keys=True) != antes


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


def _contador_compartido() -> bool:
    """En la nube el contador de intentos vive en PostgreSQL, común a todas las instancias."""
    from database import url_postgres

    return ENTORNO != "local" and url_postgres() is not None


def _registrar_fallo(nombre_usuario: str) -> None:
    if _contador_compartido():
        import intentos_nube

        intentos_nube.registrar_fallo(
            nombre_usuario, INTENTOS_LIBRES, ESPERA_INICIAL_SEGUNDOS, ESPERA_MAXIMA_SEGUNDOS
        )
        return
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
    if _contador_compartido():
        import intentos_nube

        espera = intentos_nube.segundos_de_espera(nombre_usuario)
        if espera:
            raise DemasiadosIntentos(espera)
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
    if _contador_compartido():
        import intentos_nube

        intentos_nube.limpiar(nombre_usuario)
    if usuario.get("pin_por_mostrar"):
        marcar_pin_anotado(nombre_usuario)  # entró con él: ya lo tiene
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

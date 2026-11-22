"""Login simple: usuario + PIN → token ligado a un único proyecto.

No hay registro de cuentas nuevas desde la app: las cuentas de "demo" y del
negocio real se crean solas en `seguridad.asegurar_usuarios_iniciales()`.
"""

from fastapi import APIRouter, HTTPException, Request, status

from proyectos import PROYECTOS
from seguridad import (
    DemasiadosIntentos,
    crear_token,
    cuentas_registradas,
    desde_este_equipo,
    marcar_pin_anotado,
    pines_por_mostrar,
    verificar_credenciales,
)

from .schemas import CuentaVisible, IngresoEntrada, IngresoSalida, PinPorMostrar

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/ingresar", response_model=IngresoSalida)
def ingresar(datos: IngresoEntrada) -> IngresoSalida:
    try:
        proyecto_clave = verificar_credenciales(datos.nombre_usuario, datos.pin)
    except DemasiadosIntentos as espera:
        raise HTTPException(
            status_code=429,
            detail=f"Demasiados intentos con PIN incorrecto. Espera {espera.segundos} segundos.",
            headers={"Retry-After": str(espera.segundos)},
        ) from espera
    if proyecto_clave is None:
        raise HTTPException(status_code=401, detail="Usuario o PIN incorrecto")

    proyecto = PROYECTOS[proyecto_clave]
    return IngresoSalida(
        token=crear_token(proyecto.clave),
        proyecto=proyecto.clave,
        nombre_proyecto=proyecto.nombre,
        es_real=proyecto.es_real,
    )


@router.get("/cuentas", response_model=list[CuentaVisible])
def cuentas() -> list[CuentaVisible]:
    """Cuentas que pueden ingresar, para la pantalla de ingreso.

    Así el frontend no tiene escrito en su código el nombre de ningún negocio
    real (repo público). Nunca incluye PIN, hash ni sal.
    """
    return [
        CuentaVisible(
            nombre_usuario=usuario,
            nombre_proyecto=PROYECTOS[proyecto].nombre,
            es_real=PROYECTOS[proyecto].es_real,
        )
        for usuario, proyecto in cuentas_registradas()
        if proyecto in PROYECTOS
    ]


def _origen(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/primer-ingreso", response_model=list[PinPorMostrar])
def primer_ingreso(request: Request) -> list[PinPorMostrar]:
    """El PIN generado en el primer arranque, para que el dueño lo anote (D-07).

    Solo a la misma computadora del programa: desde otro dispositivo de la red (o en la nube)
    la lista sale vacía. Deja de salir cuando el dueño toca «Ya lo anoté» o entra con él.
    """
    if not desde_este_equipo(_origen(request)):
        return []
    return [
        PinPorMostrar(
            nombre_usuario=usuario,
            nombre_proyecto=PROYECTOS[proyecto].nombre,
            pin=pin,
        )
        for usuario, pin in pines_por_mostrar()
        for nombre, proyecto in cuentas_registradas()
        if nombre == usuario and proyecto in PROYECTOS
    ]


@router.post("/primer-ingreso/{nombre_usuario}/anotado", status_code=status.HTTP_204_NO_CONTENT)
def pin_anotado(nombre_usuario: str, request: Request) -> None:
    """«Ya lo anoté»: el PIN no se vuelve a mostrar."""
    if not desde_este_equipo(_origen(request)):
        raise HTTPException(status_code=403, detail="Solo desde la computadora del programa.")
    marcar_pin_anotado(nombre_usuario)

"""Login simple: usuario + PIN → token ligado a un único proyecto.

No hay registro de cuentas nuevas desde la app: las cuentas de "demo" y del
negocio real se crean solas en `seguridad.asegurar_usuarios_iniciales()`.
"""

from fastapi import APIRouter, HTTPException

from proyectos import PROYECTOS
from seguridad import DemasiadosIntentos, crear_token, verificar_credenciales

from .schemas import IngresoEntrada, IngresoSalida

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

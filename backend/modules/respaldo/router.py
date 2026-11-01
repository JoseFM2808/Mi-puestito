"""Router de Respaldo: guardar y recuperar una copia de los datos del negocio.

Cada token solo toca la base de su propio proyecto. Las rutas no usan sesión de
SQLAlchemy porque trabajan sobre el archivo completo (ver `servicio.py`).
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.concurrency import run_in_threadpool

from fechas import dia_peruano
from seguridad import proyecto_autenticado

from . import servicio

router = APIRouter(prefix="/api/respaldo", tags=["respaldo"])


@router.get(
    "/copia",
    responses={200: {"content": {"application/octet-stream": {}}}},
    response_class=Response,
)
async def descargar_copia(proyecto: str = Depends(proyecto_autenticado)) -> Response:
    """El archivo de datos del negocio. Son datos sensibles: nunca se guarda en caché."""
    try:
        contenido = await run_in_threadpool(servicio.crear_copia, proyecto)
    except servicio.ErrorDeRespaldo as error:
        raise HTTPException(status_code=error.codigo, detail=error.mensaje) from error
    nombre = f"mi-puestito-{proyecto}-{dia_peruano().isoformat()}.db"
    return Response(
        content=contenido,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"', "Cache-Control": "no-store"},
    )


@router.post("/restaurar", status_code=status.HTTP_204_NO_CONTENT)
async def restaurar_copia(request: Request, proyecto: str = Depends(proyecto_autenticado)) -> None:
    """Reemplaza los datos por la copia enviada en el cuerpo. Lo anterior queda guardado."""
    declarado = request.headers.get("content-length", "")
    if declarado.isdigit() and int(declarado) > servicio.TAMANO_MAXIMO:
        raise HTTPException(status_code=413, detail="Ese archivo es demasiado grande para ser una copia.")
    contenido = await request.body()
    if len(contenido) > servicio.TAMANO_MAXIMO:
        raise HTTPException(status_code=413, detail="Ese archivo es demasiado grande para ser una copia.")
    if not servicio.espacio_suficiente(len(contenido)):
        raise HTTPException(status_code=507, detail="No hay espacio suficiente en esta computadora.")
    try:
        await run_in_threadpool(servicio.restaurar, proyecto, contenido)
    except servicio.ErrorDeRespaldo as error:
        raise HTTPException(status_code=error.codigo, detail=error.mensaje) from error

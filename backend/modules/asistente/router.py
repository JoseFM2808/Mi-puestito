"""Router del Asistente (AI Companion).

El Asistente solo ve el resumen del proyecto autenticado en el token — nunca
mezcla el negocio real con los datos de práctica de demo (ver seguridad.py).
Toda llamada a un modelo pasa por `ia.servicio`, la capa de abstracción
agnóstica al proveedor (regla no negociable de AGENTS.md).
"""

from fastapi import APIRouter, Depends, HTTPException

from ia.servicio import AsistenteNoDisponible, preguntar
from modules.dashboard.router import obtener_resumen
from seguridad import proyecto_autenticado

from .schemas import PreguntaEntrada, RespuestaSalida

router = APIRouter(prefix="/api/asistente", tags=["asistente"])


@router.post("/preguntar", response_model=RespuestaSalida)
async def preguntar_endpoint(
    datos: PreguntaEntrada, proyecto: str = Depends(proyecto_autenticado)
) -> RespuestaSalida:
    # Se reutiliza la misma lógica que ve el Dashboard: el Asistente nunca
    # inventa cifras, responde con el mismo resumen que ve el operador.
    resumen = obtener_resumen(proyecto=proyecto)
    contexto = resumen.model_dump_json()

    try:
        respuesta = await preguntar(datos.mensaje, contexto)
    except AsistenteNoDisponible as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    return RespuestaSalida(respuesta=respuesta)

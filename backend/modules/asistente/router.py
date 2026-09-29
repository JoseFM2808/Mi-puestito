"""Router del Asistente (AI Companion).

- Solo ve el resumen del proyecto autenticado en el token: nunca mezcla el
  negocio real con los datos de práctica de demo.
- Toda llamada a un modelo pasa por `ia.servicio` (capa agnóstica, AGENTS.md).
- Lo que sale hacia el proveedor va seudonimizado (ADR-034): el modelo ve
  "Cliente 1", el operador lee "Sra. Flora".
- No depende del router del Dashboard (D-06): usa su servicio de cálculo y,
  si no está disponible, responde igual pero sin cifras.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import obtener_sesion
from fechas import dia_peruano
from ia.privacidad import seudonimizar_resumen
from ia.servicio import AsistenteNoDisponible, preguntar

from .schemas import PreguntaEntrada, RespuestaSalida

router = APIRouter(prefix="/api/asistente", tags=["asistente"])

SIN_CIFRAS = {"aviso": "Las cifras de la caja no están disponibles en este momento."}


def _resumen_del_proyecto(sesion: Session) -> dict:
    try:
        from modules.dashboard.servicio import calcular_resumen

        return calcular_resumen(sesion, dia_peruano()).model_dump(mode="json")
    except Exception:  # noqa: BLE001 — sin Dashboard, el Asistente sigue atendiendo
        return dict(SIN_CIFRAS)


@router.post("/preguntar", response_model=RespuestaSalida)
async def preguntar_endpoint(
    datos: PreguntaEntrada, sesion: Session = Depends(obtener_sesion)
) -> RespuestaSalida:
    # El Asistente responde con el mismo resumen que ve el operador: no inventa cifras
    resumen = _resumen_del_proyecto(sesion)
    anonimo, alias = seudonimizar_resumen(resumen)

    try:
        respuesta = await preguntar(
            alias.ocultar_en_texto(datos.mensaje), json.dumps(anonimo, ensure_ascii=False)
        )
    except AsistenteNoDisponible as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    return RespuestaSalida(respuesta=alias.reidentificar(respuesta))

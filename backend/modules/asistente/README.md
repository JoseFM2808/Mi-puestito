# Módulo backend: Asistente (AI Companion)

## Qué es

El endpoint del Asistente que guía al operador (`docs/04-ia/AI-Companion.md`). Toda llamada a un modelo pasa por
`backend/ia/` (regla no negociable de AGENTS.md): este módulo no sabe si detrás hay NVIDIA NIM o un modelo local.

## Qué datos maneja

No tiene tablas. En cada pregunta:

1. Calcula el resumen de caja del proyecto del token (`modules/dashboard/servicio.py`, importado de forma perezosa: si
   falla, responde sin cifras).
2. Seudonimiza resumen, pregunta e historial (`ia/privacidad.py`, ADR-034): el modelo ve "Cliente 1", nunca un nombre.
3. Pregunta al modelo (`ia/servicio.py`), en el orden verificado de `ia/configuracion.py` (ADR-036).
4. Convierte las líneas `ACCION: ir_a <pantalla>` en botones de lista blanca (`ia/acciones.py`, ADR-037).
5. Si el registro está activo, guarda el intercambio seudonimizado para un futuro fine-tuning (`ia/registro.py`, ADR-038).

## Qué acciones permite

| Endpoint | Acción |
|---|---|
| `POST /api/asistente/preguntar` | `{mensaje, historial?}` → `{respuesta, acciones, id_respuesta, modelo}`; `503` si no hay proveedor |
| `POST /api/asistente/valoracion` | `{id_respuesta, util}` → `204` ("Me sirvió" / "No me sirvió") |

## Configuración

Variables en `backend/ia/configuracion.py` (tabla en su docstring). Para Staging con NVIDIA:
`powershell -ExecutionPolicy Bypass -File scripts\staging-con-ia.ps1` (pide la llave oculta y verifica los modelos).
Para un modelo local: `MI_PUESTITO_IA_PROVEEDOR=local` y `MI_PUESTITO_IA_MODELOS=<modelo instalado>`.

## Cómo interactúa la IA

Este módulo ES la IA de cara al usuario. Sus límites: no inventa cifras (solo el resumen), no registra ni cobra, y una
acción sugerida nunca se ejecuta sin que el operador toque el botón.

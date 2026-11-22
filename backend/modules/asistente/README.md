# Módulo backend: Asistente (AI Companion)

## Qué es

El endpoint del Asistente que guía al operador (`docs/04-ia/AI-Companion.md`). Toda llamada a un modelo pasa por
`backend/ia/` (regla no negociable de AGENTS.md): este módulo no sabe si detrás hay NVIDIA NIM o un modelo local.

## Qué datos maneja

Una tabla: `memorias_asistente` (lo que recuerda del negocio, D-26, ADR-052). En cada pregunta:

1. Calcula el resumen de caja del proyecto del token (`modules/dashboard/servicio.py`, importado de forma perezosa: si
   falla, responde sin cifras).
2. Seudonimiza resumen, pregunta, historial y recuerdos (`ia/privacidad.py`, ADR-034): el modelo ve "Cliente 1", nunca
   un nombre. Un cliente o proveedor guardado que se nombre en el texto también recibe código aunque no esté en el
   resumen (`registrar_mencionados`).
3. Pregunta al modelo (`ia/servicio.py`), en el orden verificado de `ia/configuracion.py` (ADR-036).
4. Convierte las líneas `ACCION: ir_a <pantalla>` en botones de lista blanca (`ia/acciones.py`, ADR-037), y las de
   llenado en datos para que el operador los confirme: `VENTA`/`PARA` (orden, `ia/borrador.py`), `ABONO`/`GASTO`/`MERMA`
   (`ia/formularios.py`) y `COMPRA`/`PROVEEDOR` (pedido a un proveedor, `ia/pedido.py`). Solo si el operador pidió
   hacerlo, y solo con los montos que él dijo.
5. Si el operador pidió recordar algo (`ia/memoria.py`), guarda las líneas `RECORDAR:` con el nombre real; pasado el
   tope de 20, el modelo consolida la lista en 15 (si falla, quedan los más nuevos).
6. Si el registro está activo, guarda el intercambio seudonimizado para un futuro fine-tuning (`ia/registro.py`, ADR-038).

## Qué acciones permite

| Endpoint | Acción |
|---|---|
| `POST /api/asistente/preguntar` | `{mensaje, historial?, pantalla_actual?}` → `{respuesta, acciones, borrador, formulario, recordado, id_respuesta, modelo}`; `503` si no hay proveedor |
| `GET /api/asistente/recuerdos` | Lo que recuerda, del más viejo al más nuevo |
| `DELETE /api/asistente/recuerdos/{uuid}` | Olvida uno (`204`, idempotente) |
| `DELETE /api/asistente/recuerdos` | Olvida todo (`204`) |
| `POST /api/asistente/valoracion` | `{id_respuesta, util}` → `204` ("Me sirvió" / "No me sirvió") |

## Configuración

Variables en `backend/ia/configuracion.py` (tabla en su docstring). Para Staging con NVIDIA:
`powershell -ExecutionPolicy Bypass -File scripts\staging-con-ia.ps1` (pide la llave oculta y verifica los modelos).
Para un modelo local: `MI_PUESTITO_IA_PROVEEDOR=local` y `MI_PUESTITO_IA_MODELOS=<modelo instalado>`.

## Cómo interactúa la IA

Este módulo ES la IA de cara al usuario. Sus límites: no inventa cifras (solo el resumen), no registra ni cobra, y una
acción sugerida nunca se ejecuta sin que el operador toque el botón.

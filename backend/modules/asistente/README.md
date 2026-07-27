# Módulo backend: Asistente (AI Companion)

## Qué es

El [[AI-Companion]] conectado a un modelo real. Responde preguntas del
operador en lenguaje simple usando el mismo resumen que ve en el Dashboard —
nunca inventa cifras que no estén ahí.

## Qué datos maneja

Ninguna tabla propia. Por cada pregunta, arma el contexto a partir de
`GET /api/dashboard/resumen` del **proyecto autenticado** y se lo pasa al
modelo como parte del prompt de sistema. El Asistente de "demo" solo ve datos
ficticios; el de un proyecto real (p. ej. "anita") solo ve los suyos — nunca
se mezclan.

## Qué acciones permite

| Endpoint | Descripción |
|---|---|
| `POST /api/asistente/preguntar` | `{mensaje}` → `{respuesta}`. Requiere sesión iniciada. |

## Capa de IA agnóstica (importante)

Este router **no** llama a NVIDIA directamente: llama a `ia.servicio.preguntar`,
la capa de abstracción (`backend/ia/`). Eso cumple la regla no negociable de
`AGENTS.md`: *"Nunca acoplar el código a un proveedor de IA específico."*
Hoy el único proveedor conectado es NVIDIA NIM (`ia/nvidia.py`, API compatible
con OpenAI, llave en la variable de entorno `NVIDIA_API_KEY` — nunca en el
repo). Cambiar de proveedor el día de mañana significa escribir un nuevo
archivo en `ia/` con la misma interfaz (`ia/proveedor.py`), no tocar este
router ni el frontend.

### Prioridad por velocidad

El operador necesita respuestas rápidas mientras atiende clientes. `ia/servicio.py`
prueba una lista de modelos de más rápido/chico a más grande/capaz
(configurable con `NVIDIA_MODELOS_PRIORIDAD`, separados por coma) con un
tiempo límite corto por intento (`MI_PUESTITO_IA_TIMEOUT`, 8s por defecto):
si el primero no contesta a tiempo, se prueba el siguiente.

### Si no hay llave configurada

El endpoint responde `503` con un mensaje claro en vez de fallar feo. El
Asistente puede estar "apagado" sin que el resto de la app (Dashboard,
Ventas, Compras) se vea afectado — mismo principio de aislamiento por módulo
que ya existe en `main.py`.

## Cómo interactúa la IA

Este módulo *es* la IA: el frontend expone el botón "Asistente" de la barra
superior como un panel de chat que llama a este endpoint.

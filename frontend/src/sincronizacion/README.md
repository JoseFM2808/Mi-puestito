# Sincronización offline (frontend)

## Qué es

La cola que cumple la regla offline-first (AGENTS.md, ADR-032): toda escritura de Ventas y Fiados se guarda en el
dispositivo ANTES de enviarse, y se envía sola cuando hay red.

## Qué datos maneja

`base-local.ts` abre una base IndexedDB **por proyecto** (`mi-puestito-<proyecto>`) con:

| Tabla            | Contenido                                                                                  |
| ---------------- | ------------------------------------------------------------------------------------------ |
| `operaciones`    | Cola: método, ruta, cuerpo (con `ocurrido_en`), descripción en palabras, estado e intentos |
| `ventasAbiertas` | Última versión de las órdenes abiertas, para abrir la app sin red                          |
| `clientes`       | Clientes buscados o creados, para fiar sin red                                             |
| `instantaneas`   | Última "Caja de hoy" conocida                                                              |

## Qué acciones permite

`cola.ts`:

- `encolar`: guarda y dispara el envío. La hora real viaja en `ocurrido_en`.
- `procesarCola`: FIFO, de a una. Sin red se detiene; `4xx` → queda **rechazada** con el motivo del servidor y sigue con
  las demás; `5xx` o `401` → se reintenta más tarde (nada se pierde).
- `iniciarSincronizacion`: reintenta al volver la red (`online`) y cada 20 s.
- `alAplicarOperacion`: avisa a quien escucha con la respuesta del servidor.

`componentes/sincronizacion/EstadoSincronizacion.tsx` muestra el estado ("Sin conexión. 2 cambios guardados en esta
tablet; se enviarán solos.") y las operaciones rechazadas con **Entendido**.

## Cómo interactúa la IA

`data-ai-id`: `sincronizacion.estado`, `sincronizacion.rechazadas`, `sincronizacion.rechazada-<id>.entendido`. El
Asistente puede explicar qué significa el aviso de conexión; no manipula la cola.

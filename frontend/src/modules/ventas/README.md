# Módulo: Ventas (frontend)

## Qué es

Pantalla de ventas (`docs/03-modulos/Modulo-Ventas.md`): órdenes activas en paralelo, fiado, venta rápida y su detalle
posterior. Funciona **sin conexión**: cada acción cambia la pantalla al instante, se guarda en el dispositivo y se envía
cuando hay red (ADR-032).

## Qué datos maneja

- `almacen.ts` (Zustand): órdenes abiertas, ventas rápidas por completar, clientes buscados y avisos del servidor.
  Persiste las órdenes abiertas en IndexedDB para abrir la app sin red.
- Toda escritura genera un `uuid` en el dispositivo y pasa por `sincronizacion/cola.ts`. La respuesta del servidor
  reemplaza a la versión local cuando ya no quedan cambios pendientes de esa venta.
- Montos en céntimos enteros; lo que escribe el operador ("12,50") se lee con `leerMontoEscrito`.

## Qué acciones permite

| Acción                                             | Botón                                                                     |
| -------------------------------------------------- | ------------------------------------------------------------------------- |
| Abrir una orden (con nombre opcional: "Mesa 2")    | **Nueva orden**                                                           |
| Abrir un fiado eligiendo o registrando al cliente  | **Nuevo fiado**                                                           |
| Registrar solo el monto cobrado                    | **Venta rápida** → **Cobré en efectivo** / **Cobré con Yape o Plin**      |
| Cambiar de orden con un toque                      | Pestañas de órdenes abiertas                                              |
| Agregar / quitar productos                         | **Agregar producto** / **Quitar**                                         |
| Cerrar la orden                                    | **Cobrar en efectivo**, **Cobrar con Yape o Plin**, **Fiar a un cliente** |
| Anular una orden vacía                             | **Anular esta orden**                                                     |
| Completar una venta rápida (debe sumar lo cobrado) | **Completar el detalle** → **Guardar el detalle**                         |

Los avisos del servidor (límite de crédito, stock negativo) y las operaciones rechazadas se muestran en palabras, con
**Entendido**.

## Cómo interactúa la IA

`data-ai-id`: `ventas`, `ventas.nueva`, `ventas.nuevo-fiado`, `ventas.rapida`, `ventas.ordenes`,
`ventas.pestana-<uuid>`, `ventas.orden-<uuid>` y sus `.cobrar-efectivo`, `.cobrar-yape`, `.fiar`, `.anular`,
`.quitar-<item>`, `.total`; formularios `ventas-orden-<uuid>.producto|cantidad|monto|agregar`, `ventas.venta-rapida.*`,
`ventas.selector-cliente.*`, `ventas.rapidas`, `ventas.rapida-<uuid>.*`. El Asistente puede sugerir "Ir a Ventas" y
explicar los pasos; nunca toca estos botones por el operador.

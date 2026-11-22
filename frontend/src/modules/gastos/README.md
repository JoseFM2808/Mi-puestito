# Módulo: Gastos

## Qué es

La pantalla de lo que sale de la caja (D-24, ADR-051, `docs/03-modulos/Modulo-Gastos.md`): del puesto o de la casa, y de
dónde salió la plata (gaveta o Yape). Opción **Gastos** del menú y acceso **Anotar un gasto** en la Caja de hoy.

## Qué datos maneja

- `almacen.ts` (Zustand): los gastos del día peruano, offline-first como Ventas. Anotar o borrar cambia la pantalla al
  instante, se guarda en IndexedDB (`gastos`, con su día) y se encola (`POST /api/gastos`, `DELETE /api/gastos/{uuid}`).
- Sin red muestra lo guardado en la tablet; al terminar de enviar la cola, trae la versión del servidor.
- `totales()` suma en céntimos por medio y por ámbito, solo para mostrar: el servidor tiene la verdad.

## Qué acciones permite

| Acción            | Botón                                                                                                                                                      |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Anotar un gasto   | **Anotar un gasto** → monto, **De la gaveta (efectivo)** / **Del Yape o Plin**, **Para el puesto** / **Para la casa**, categoría, nota → **Guardar gasto** |
| Corregir un error | **Borrar** en el gasto                                                                                                                                     |

El pago de un pedido no se anota aquí: llega solo desde Compras (**Ya le pagué en efectivo / con Yape**).

## Cómo interactúa la IA

`data-ai-id`: `gastos`, `gastos.anotar`, `gastos.nuevo`, `gastos.monto`, `gastos.medio-efectivo|yape_plin`,
`gastos.ambito-puesto|hogar`, `gastos.categoria-<categoria>`, `gastos.descripcion`, `gastos.guardar`, `gastos.cancelar`,
`gastos.total-hoy`, `gastos.puesto-y-casa`, `gastos.lista`, `gastos.gasto-<uuid>`, `gastos.borrar-<uuid>`.
El Asistente lleva aquí ("quiero anotar un gasto") y puede señalar `gastos.anotar`; no anota gastos por su cuenta.

# Módulo backend: Compras y Proveedores

## Qué es

API y modelo de datos de `docs/03-modulos/Modulo-Compras.md`: proveedores,
órdenes de pedido y recepción de mercadería (checklist). Independiente de los
demás módulos (sin claves foráneas cruzadas).

## Qué datos maneja (tablas)

- **`proveedores`** — nombre y empresa (indexados, se buscan por texto), RUC
  (opcional, 11 dígitos, **único**: evita registrar dos veces al mismo
  proveedor), teléfono, categoría. El proveedor puede registrarse a sí mismo
  desde la tablet.
- **`ordenes_compra`** — proveedor, estado (`borrador → pendiente → en_camino →
  recibida → cerrada`), fecha estimada de llegada (alimenta la proyección del
  Dashboard, indexada junto al estado), `monto_total` planificado y
  `monto_real` recalculado tras el checklist de recepción.
- **`items_orden_compra`** — producto (nombre único en el sistema), cantidad en
  texto libre ("2 packs"), monto total del ítem (no precio unitario en esta
  fase), estado de recepción (`pendiente / recibido / no_recibido / cambiado`)
  y, si hubo cambio, el sustituto con su monto. Se borran en cascada junto con
  su orden.

Fechas en UTC (tipo `FechaHoraUTC`, siempre con zona); la zona horaria
(America/Lima) se aplica al presentar.

## Qué acciones permite

| Endpoint | Estado |
|---|---|
| `GET /api/compras/proveedores` | Demo 1 — lista proveedores, paginada |
| `GET /api/compras/ordenes` | Demo 1 — lista órdenes con items, paginada, sin N+1 |
| Registrar proveedor / crear orden / checklist de recepción | Próxima demo |

## Cómo interactúa la IA

El AI Companion consulta estos endpoints para responder preguntas como
"¿cuánto le debo pagar a Distribuidora Norte?" o "¿qué pedidos llegan mañana?".
El monto a pagar de una orden recibida es `monto_real` (lo efectivamente
recibido), no `monto_total`.

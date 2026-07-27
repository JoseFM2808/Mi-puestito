# Módulo backend: Ventas

## Qué es

API y modelo de datos de `docs/03-modulos/Modulo-Ventas.md`: ventas al
contado, órdenes activas en paralelo, fiado y ventas rápidas. Independiente de
los demás módulos: no valida stock (funciona sin Inventario) y no tiene claves
foráneas hacia Compras.

## Qué datos maneja (tablas)

- **`clientes`** — nombre (indexado, se busca por nombre), teléfono, límite de
  crédito **opcional** (`NULL` = crédito libre, el default).
- **`ventas`** — tipo (`orden_activa` / `fiado` / `venta_rapida`), cliente
  (obligatorio solo en fiado — restricción `ck_fiado_requiere_cliente`),
  nombre visible de la orden ("Orden 2"), estado (`abierta` /
  `pagada_cerrada` / `pendiente_formalizar`), monto total, método de pago
  (`efectivo` / `yape_plin`) y fechas de apertura/cierre. Índices por
  `(estado, abierta_en)` y `(tipo, cliente_id)`.
- **`items_venta`** — producto, cantidad en texto libre y monto. La venta
  rápida no tiene items hasta formalizarse; el granel sin inventario se digita
  como monto directo. Se borran en cascada junto con su venta.
- **`pagos`** — pagos de ventas y abonos de fiado. Restricción
  `ck_pago_tiene_destino`: un pago sin venta y sin cliente no se puede guardar
  (sería dinero registrado a nadie). Se borran en cascada junto con su venta.

**Regla clave:** la deuda de un cliente se **deriva** (Σ ventas fiado −
Σ pagos); nunca se guarda un saldo duplicado.

Fechas en UTC (tipo `FechaHoraUTC`, siempre con zona); la zona horaria
(America/Lima) se aplica al presentar.

## Qué acciones permite

| Endpoint | Estado |
|---|---|
| `GET /api/ventas/` | Demo 1 — lista ventas con items, paginada, sin N+1 |
| `GET /api/ventas/clientes` | Demo 1 — lista clientes, paginada |
| Abrir/cerrar órdenes, registrar fiado, venta rápida, pagos | Próxima demo |

## Cómo interactúa la IA

El AI Companion consulta estos endpoints para responder "¿cuánto me debe la
Sra. Flora?" (derivando la deuda con sus ventas fiado y pagos) o "¿qué órdenes
siguen abiertas?". Cuando existan las operaciones de escritura, el Companion
podrá pre-llenar formularios de venta, nunca confirmarlos por su cuenta.

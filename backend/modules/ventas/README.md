# Módulo backend: Ventas

## Qué es

API y reglas de `docs/03-modulos/Modulo-Ventas.md`: órdenes activas en paralelo, fiado con deuda derivada y venta
rápida. Independiente de los demás módulos: no valida stock y no tiene claves foráneas hacia Inventario ni Compras.
Las reglas viven en `servicio.py`; `router.py` solo traduce a HTTP.

## Qué datos maneja (tablas)

- **`clientes`**: `uuid`, nombre (indexado), teléfono (dato personal), límite de crédito opcional en céntimos (`NULL` =
  libre).
- **`ventas`**: `uuid`, tipo (`orden_activa` / `fiado` / `venta_rapida`), cliente (obligatorio en fiado), nombre de la
  orden, estado (`abierta` / `pagada_cerrada` / `fiada` / `pendiente_formalizar`), `monto_total` en céntimos, método de
  pago, fechas de apertura y cierre.
- **`items_venta`**: `uuid`, producto, cantidad en texto libre, monto, y opcionalmente `producto_uuid` + `cantidad_num`
  para que Inventario descuente stock.
- **`pagos`**: `uuid`, pagos de ventas y abonos a cuenta (`venta_id` NULL).

Reglas clave (ver `.ai-context/01-logica-sistema.md`):

- `monto_total` de una orden o fiado es SIEMPRE Σ items, calculado aquí. La venta rápida conserva lo cobrado y su
  detalle debe cuadrar al formalizar.
- Deuda = Σ ventas `fiada` − Σ abonos. Nunca se guarda un saldo.
- Toda escritura es idempotente por `uuid` (201 si creó, 200 si ya existía).
- Lo que ya ocurrió (un fiado sobre el límite) se guarda y devuelve un **aviso**, no un error.
- Agregar o quitar un item publica `venta.item_registrado` / `venta.item_anulado` en `eventos.py`.

## Qué acciones permite

| Endpoint | Acción |
|---|---|
| `GET /api/ventas/`, `/abiertas`, `/{uuid}` | Listar, panel de órdenes abiertas, detalle |
| `POST /api/ventas/` | Abrir orden activa o fiado; registrar venta rápida ya cobrada |
| `POST /api/ventas/{uuid}/items`, `DELETE …/items/{item}` | Agregar o quitar productos |
| `POST /api/ventas/{uuid}/cobrar`, `/fiar`, `/formalizar` | Cerrar cobrando, a crédito, o completar una venta rápida |
| `DELETE /api/ventas/{uuid}` | Anular una orden abierta sin productos |
| `GET/POST/PATCH /api/ventas/clientes…`, `GET /api/ventas/fiados`, `POST /api/ventas/abonos` | Clientes, quién debe, abonos |

Contrato completo: `.ai-context/06-api-mcp.md`.

## Cómo interactúa la IA

El Asistente no llama a estos endpoints: lee el resumen del Dashboard (que agrega estas tablas) para responder "¿cuánto
me debe la Sra. Flora?" o "¿qué órdenes siguen abiertas?", y puede sugerir el botón "Ir a Ventas" o "Ir a Fiados". Nunca
cobra, fía ni registra por su cuenta.

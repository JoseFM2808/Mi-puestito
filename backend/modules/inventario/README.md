# Módulo backend: Inventario

## Qué es

Stock de productos como **libro mayor de movimientos** (ADR-031, `docs/03-modulos/Modulo-Inventario.md`). Ventas y
Compras funcionan sin este módulo; cuando está cargado, se suscribe a los eventos de Ventas y descuenta stock en la misma
transacción que la venta, dentro de un SAVEPOINT (si falla, la venta se guarda igual).

## Qué datos maneja (tablas)

- **`productos`**: `uuid`, nombre único, código de barras opcional, unidad (`unidad` / `kg` / `litro`), precio de venta
  (céntimos), `stock_actual` (milésimas; caché de Σ movimientos), stock mínimo y si vence.
- **`movimientos_inventario`**: `delta` ±, motivo (`venta`, `anulacion_venta`, `compra`, `ajuste`, `merma`), origen
  (`origen_tipo` + `origen_ref`, único) y nota. Solo se insertan, nunca se editan.

Reglas clave:

- `servicio.registrar_movimiento` es la única función que cambia `stock_actual`, con un incremento atómico en SQL.
- Un origen mueve el stock una sola vez (`UNIQUE(origen_tipo, origen_ref)`): reenviar una venta no descuenta dos veces.
- Vender más de lo que hay **no se rechaza**: el stock queda negativo, se avisa al operador y aparece en `descuadres`.
- El conteo físico (`ajustes`) recibe cuánto HAY y calcula la diferencia en el servidor, contra el stock de ese momento.

## Qué acciones permite

| Endpoint | Acción |
|---|---|
| `GET /api/inventario/productos` | Listar (con `bajo_minimo` y `descuadre`); filtros `buscar`, `solo_bajo_minimo` |
| `POST /api/inventario/productos`, `PATCH …/{uuid}` | Registrar producto (con stock inicial opcional), editar datos maestros |
| `GET /api/inventario/productos/{uuid}/movimientos` | Por qué cambió el stock |
| `POST /api/inventario/ajustes`, `/mermas` | Conteo físico; producto vencido o dañado |
| `GET /api/inventario/descuadres`, `/conciliacion` | Stock negativo; control interno (siempre vacío) |

## Cómo interactúa la IA

Todavía no tiene pantalla ni entra en el resumen del Asistente. Cuando la tenga, el Asistente podrá responder "¿cuánto
arroz me queda?" y sugerir contar lo que hay cuando haya descuadre; nunca hará el ajuste por su cuenta.

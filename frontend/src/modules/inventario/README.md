# Módulo: Inventario (frontend)

## Qué es

Cuánto hay de cada producto (`docs/03-modulos/Modulo-Inventario.md`). Opcional: Ventas y Compras funcionan sin él. El
stock que manda es el del servidor, Σ movimientos (ADR-031). Nunca se escribe a mano: se cuenta lo que hay y el servidor
calcula la diferencia.

## Qué datos maneja

- `GET /api/inventario/productos`: se guarda en el dispositivo (`productos`) para abrir la pantalla sin red.
- `GET /api/inventario/productos/{uuid}/movimientos`: el historial, solo con red.
- Cantidades en **milésimas enteras** (`aMilesimas`), igual que el dinero en céntimos: "1.5 kg" es 1500.

## Qué acciones permite

| Acción                         | Botón                                             |
| ------------------------------ | ------------------------------------------------- |
| Registrar un producto          | **Nuevo producto** → **Guardar producto**         |
| Corregir el stock con la vista | **Contar lo que hay** → **Guardar conteo**        |
| Algo se perdió o venció        | **Registrar merma** → **Guardar merma**           |
| Precio de venta y aviso        | **Cambiar precio o mínimo** → **Guardar cambios** |
| Por qué cambió el stock        | **Ver historial**                                 |
| Ver lo que se acaba            | **Solo lo que queda poco**                        |

Todo se guarda sin red y se envía por la cola (`sincronizacion/cola.ts`); el stock se refleja al instante y el servidor
lo confirma.

## Cómo debe interactuar la IA

- Puede llevar al operador aquí con `ACCION: ir_a inventario`. Hoy no ve el stock (no está en su contexto): no debe
  decir cuánto queda de nada.
- Nunca cuenta ni registra mermas por su cuenta.
- Los `data-ai-id` son `inventario.*`; los de cada producto llevan su `uuid`: `inventario.contar-<uuid>`.

## Límites conocidos

- Sin búsqueda por código de barras, foto, alertas de vencimiento ni costo desde la última compra (pendientes del módulo).
- Las ventas descuentan stock solo si el operador elige el producto del inventario al venderlo (`FormularioProducto`);
  con texto libre no se toca el stock.

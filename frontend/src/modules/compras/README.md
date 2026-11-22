# Módulo: Compras (frontend)

## Qué es

Pedidos a proveedores, de la orden a la recepción (`docs/03-modulos/Modulo-Compras.md`). Offline-first igual que Ventas:
cada acción cambia la pantalla al instante, se guarda en IndexedDB y se encola; el total que manda es el del servidor.

## Qué datos maneja

- `GET /api/compras/ordenes` (sin las cerradas) y `GET /api/compras/proveedores`: se guardan en el dispositivo
  (`ordenesCompra`, `proveedores`) para abrir la pantalla sin red.
- `GET /api/compras/proveedores/{uuid}/frecuentes`: sugerencias al armar un pedido. Sin red el pedido se arma igual.
- `GET /api/inventario/productos`: solo para saber si preguntar cuánto entra al stock. Inventario es opcional.

## Qué acciones permite

| Acción                              | Botón                                                                               |
| ----------------------------------- | ----------------------------------------------------------------------------------- |
| Armar un pedido                     | **Nuevo pedido** → **Agregar al pedido** → **Guardar pedido**                       |
| Dejarlo sin confirmar               | **Guardar como borrador** → **Confirmar pedido**                                    |
| Registrar un proveedor              | **Registrar proveedor nuevo** (se le puede pasar la tablet)                         |
| Marcar que ya salió                 | **Ya viene en camino**                                                              |
| Revisar lo que llegó                | **Llegó este pedido** → **Llegó / No llegó / Cambió**                               |
| Saldar con el proveedor             | **Ya le pagué en efectivo** / **Ya le pagué con Yape** (la caja lo descuenta, D-24) |
| Completar lo que llenó el Asistente | **<producto>: escribir el monto** → **Agregar al pedido** → **Guardar pedido**      |

## Cómo debe interactuar la IA

- Puede llevar al operador aquí con `ACCION: ir_a compras`; nunca confirma una recepción por su cuenta.
- Puede **llenar un pedido** (líneas `COMPRA:` y `PROVEEDOR:`): llega en `pedido` de la respuesta, el Asistente lo deja en
  `stores/borradorAsistente.ts` (`ponerPedido`) y Compras lo toma una vez (`tomarPedido`) para abrir «Nuevo pedido» con el
  proveedor elegido (por nombre o empresa; si no existe, su búsqueda escrita) y los productos: los que traen monto van al
  pedido; los demás quedan en «Falta cuánto cuesta» (`compras.falta-monto`, `compras.completar-<n>`). Aviso
  `compras.llenado-asistente`. Nada se guarda hasta «Guardar pedido».
- Los `data-ai-id` son `compras.*`. Los de cada pedido llevan su `uuid`: `compras.llego-<uuid>`.
- El monto "A pagar por lo que llegó" es el `monto_real` del servidor una vez sincronizado.

## Lo que se está acabando

Si Inventario tiene productos bajo su mínimo, «Nuevo pedido» los muestra en **Se te está acabando**
(`compras.se-acaba`, `compras.se-acaba-<uuid>`): tocar uno lo lleva al formulario y, si se le suele pedir a ese
proveedor, con la cantidad y el monto de siempre. Desde Inventario, **Pedir lo que se acaba** abre «Nuevo pedido» con
todos ellos en «Falta cuánto cuesta» (mismo camino que el pedido del Asistente, `origen: 'inventario'`). Inventario es
opcional: si no está o falla, el pedido se arma igual.

## Límites conocidos

- El RUC se escribe a mano: la búsqueda en SUNAT necesita un servicio externo que aún no se ha elegido.
- Una recepción confirmada no se reescribe, porque ya movió stock. Un error se corrige con un ajuste de Inventario.

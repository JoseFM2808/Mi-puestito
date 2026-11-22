# Módulo: Inventario

#modulo #fase2

> ⚠️ Independiente de Compras y Ventas: ellos funcionan sin él. Al activarse, **enriquece** automáticamente a los demás.

## Registro de producto

- **Código de barras** → nombre automático desde base de datos pública de productos.
- **Sin código (ej. arroz a granel):** foto + categoría + nombre manual.
- Datos: nombre, cantidad, **precio de venta**, unidad (unidad / kg / litro), ¿tiene vencimiento?
- **Costo:** calculado desde la última orden de compra ([[Modulo-Compras]]). Si no hay compra registrada, queda pendiente hasta la próxima.

## Fechas de vencimiento

- Si el producto vence: registrar fecha.
- Alertas configurables al acercarse (3 / 7 / 15 días).

## Precios

- **Por peso:** se registra el precio por kg una vez; en [[Modulo-Ventas]] solo se digita el peso.
- **Cambio de precio:** se edita y se confirma como "precio nuevo" → todas las ventas futuras lo usan. Historial de precios guardado.

## Relación con proveedores

- Un producto ↔ uno o más proveedores.
- Al crear una orden, el sistema sugiere qué pedir a ese proveedor según stock bajo.

## Estado

- Fase: **2 del producto** (base técnica adelantada).
- **Avance:** backend completo como libro mayor de movimientos (decisión 31 de [[Decisiones-Tecnicas]]): productos,
  stock que se descuenta solo al vender con `producto_uuid` (si [[Modulo-Ventas]] lo envía), conteo físico, mermas,
  descuadres y conciliación. Ver `backend/modules/inventario/README.md`.
- **Pantalla (2026-11-07):** alta de productos, stock con "Queda poco" y "Descuadre", conteo, merma, precio y mínimo,
  historial, todo sin red. Las compras recibidas suman al stock si se dice cuánto ([[Modulo-Compras]]).
- **Ventas (2026-11-07):** al vender se puede elegir un producto del inventario; la cantidad descuenta el stock y el
  precio sugiere el monto ([[Modulo-Ventas]]).

- **Hecho (2026-11-17, D-22):** costo de la última compra y ganancia por unidad; vencimiento del lote más antiguo con
  aviso en Inventario y en la [[Modulo-Dashboard]]; búsqueda por código de barras (lector USB o Bluetooth).
- **Hecho (2026-11-22, D-30):** escanear el código con la cámara al buscar, al crear el producto y al venderlo en
  [[Modulo-Ventas]].
- **Hecho (2026-11-22):** sugerencia de pedido por stock bajo. «Pedir lo que se acaba» abre un pedido en
  [[Modulo-Compras]] con lo que está bajo el mínimo, y «Nuevo pedido» muestra «Se te está acabando» (con lo que se le
  suele pedir a ese proveedor, si coincide). Compras funciona igual sin Inventario.
- **Pendiente:** registro por foto del producto.

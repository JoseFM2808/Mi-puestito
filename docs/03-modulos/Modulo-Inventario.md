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
- **Pendiente:** pantalla, alertas de vencimiento, costo desde la última compra y sugerencia de pedido por stock bajo.

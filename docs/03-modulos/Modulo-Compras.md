# Módulo: Compras y Proveedores

#modulo #mvp

Gestiona proveedores, órdenes de pedido y recepción de mercadería.

## 2A. Registro de Proveedores

- **El proveedor puede registrarse a sí mismo:** se le entrega la tablet y llena sus datos (nombre, empresa, RUC opcional con búsqueda en SUNAT, teléfono, categoría de productos).
- Búsqueda por nombre, empresa o RUC.

## 2B. Creación de Orden de Pedido

- Seleccionar proveedor existente o registrar nuevo.
- Por producto: **nombre único en el sistema**, cantidad (unidad total, ej. "2 packs"), **monto total** (no precio unitario en esta fase).
- El sistema sugiere productos frecuentes de ese proveedor según órdenes anteriores.
- Fecha estimada de llegada → alimenta la proyección del [[Modulo-Dashboard]].

## 2C. Confirmación de Recepción (Checklist)

Al llegar la orden, se abre el checklist:
- ✅ Recibido / ❌ No recibido / 🔄 Cambio de producto
- Si hay cambio: registrar sustituto y monto.
- Si no llegó: llamar al proveedor / excluir de la orden / dejar pendiente.
- El sistema **recalcula el monto real a pagar** según lo efectivamente recibido.

## Estados de una orden

`Borrador → Pendiente → En camino → Recibida (checklist) → Cerrada`

## Independencia

Funciona **sin** [[Modulo-Inventario]]. Cuando el inventario se active, las compras alimentarán el costo de los productos automáticamente.

## Estado
- Fase: **MVP**
- **Avance (Demo 1):** esquema de base de datos creado en
  `backend/modules/compras/models.py` (`proveedores`, `ordenes_compra`,
  `items_orden_compra`, con estados y checklist de recepción) y endpoints de
  lectura. Pendiente: UI, auto-registro de proveedores y checklist.

# Módulo: Ventas

#modulo #mvp

Registra ventas al contado, cuentas corrientes del día, fiado y ventas rápidas. **Soporta múltiples ventas en paralelo en un solo dispositivo.**

## Tipos de venta

| Tipo | Descripción |
|---|---|
| **Orden activa** | Sigue abierta durante el día (ej. restaurante que pide varias veces). Se cierra y cobra al final. |
| **Fiado** | Cliente registrado que paga después. Acumula deuda. Límite de crédito **opcional** por cliente (libre por defecto). |
| **Venta rápida** | Solo monto, sin detalle. Se formaliza después, cuando hay pausa. |

## Panel de órdenes activas

- Todas las órdenes abiertas visibles como cards/pestañas: Orden 1, Orden 2, Orden 3...
- Cambio entre órdenes con un toque (varias ventas ocurren a la vez en el puesto).
- Botón "+" para abrir una nueva.

## Registro de producto en una venta

- **Foto** del producto → búsqueda de coincidencias → confirmación del nombre, o
- **Código de barras** (si tiene), o
- **Descripción manual** / búsqueda por nombre.
- **Productos por peso (ej. arroz a granel):** sin inventario activo, se digita el monto total directo. Con [[Modulo-Inventario]] activo, se digita el peso y el precio se calcula solo.

## Cierre y pago

- Métodos: efectivo, YAPE/Plin (mostrar QR generado; integración automática futura con APIs de pago peruanas).
- Estado final: **Pagada y Cerrada**.
- Comprobante SUNAT: previsto a futuro, no es MVP.

## Independencia

Funciona **sin** [[Modulo-Inventario]]: no se valida stock al vender. La información se regulariza después si el inventario se activa.

## Estado
- Fase: **MVP**
- **Avance (Fase 3):** API de escritura idempotente y pantalla de Ventas con
  órdenes activas en paralelo, fiado con buscador de clientes, venta rápida y su
  detalle posterior, todo funcionando sin conexión (ver
  `frontend/src/modules/ventas/README.md` y `backend/modules/ventas/README.md`).
  La deuda se deriva (Σ ventas fiadas − Σ abonos); los montos se guardan en
  céntimos. Pendiente: QR de YAPE/Plin (necesita el número del vendedor) y
  registro por foto o código de barras.

# Módulo: Dashboard / Caja Diaria (frontend)

## Qué es

Pantalla principal de la app ("Caja de hoy"). Implementa
`docs/03-modulos/Modulo-Dashboard.md`: resumen del día actual y proyección del
día siguiente. En **Demo 1** muestra datos ficticios; no bloquea ni depende de
otros módulos.

## Qué datos maneja

Todos ficticios en `datos-ficticios.ts` (en demos siguientes: datos reales de
Ventas y Compras vía IndexedDB/Dexie, con el backend como respaldo):

- **Vendiste hoy** — total de ventas cerradas del día y cantidad.
- **Mañana necesitas en caja** — proyección según órdenes de compra por llegar.
- **Órdenes abiertas ahora** — órdenes activas y fiado en curso.
- **Fiados por cobrar** — deuda total y cantidad de clientes.
- **Ventas rápidas por completar** — pendientes de formalizar.
- **Pedidos por llegar** — órdenes de compra con proveedor, fecha estimada y
  monto. Un pedido vencido se marca "Debió llegar…(atrasado)", nunca "Llega hoy".

Fechas y montos se formatean en `formato.ts` con `Intl` (`es-PE`, moneda PEN,
zona `America/Lima` fija); el sistema detecta fecha y zona horaria solo, el
usuario nunca las ingresa.

## Qué acciones permite

| Acción | Estado en Demo 1 |
|---|---|
| Tocar una orden abierta → ir a esa venta | Card presente, sin navegación aún |
| **Registrar venta** | Botón presente, sin destino aún |
| **Venta rápida** | Botón presente, sin destino aún |
| **Llegó un pedido** (checklist de recepción) | Botón presente, sin destino aún |

## Cómo interactúa la IA

El AI Companion puede leer cualquier cifra, explicarla en lenguaje simple y
navegar al módulo de origen. `data-ai-id` disponibles:

- `dashboard` — la pantalla completa
- `dashboard.fecha` — fecha del día
- `dashboard.ventas-hoy`, `dashboard.proyeccion-manana` — cards de resumen
- `dashboard.ordenes-activas` y `dashboard.orden-activa-<id>` — órdenes abiertas
- `dashboard.fiados`, `dashboard.ventas-rapidas` — cards secundarias
- `dashboard.pedidos-por-llegar` y `dashboard.pedido-<id>` — compras por recibir
- `dashboard.registrar-venta`, `dashboard.venta-rapida`, `dashboard.llego-pedido` — acciones

Ejemplo: si el usuario pregunta "¿por qué necesito 320 mañana?", la IA lee
`dashboard.proyeccion-manana` y `dashboard.pedidos-por-llegar` y explica que
mañana llega el pedido de Distribuidora Norte por ese monto.

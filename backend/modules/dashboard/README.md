# Módulo backend: Dashboard / Caja Diaria

## Qué es

API del resumen diario (`docs/03-modulos/Modulo-Dashboard.md`): total vendido
hoy, proyección de caja para mañana, órdenes abiertas, fiados por cobrar,
ventas rápidas pendientes y pedidos por llegar.

## Qué datos maneja

No tiene tablas propias: **agrega** cifras de Ventas y Compras. En Demo 1
devuelve datos ficticios (espejo de
`frontend/src/modules/dashboard/datos-ficticios.ts`) para fijar el contrato
del API. Lee de otros módulos pero no bloquea su funcionamiento: si Ventas o
Compras fallan, el resumen degrada esa cifra, no se cae.

El día se calcula con `fechas.dia_peruano()` (zona America/Lima), nunca con el
reloj del servidor: entre las 19:00 y medianoche hora peruana un servidor en
UTC ya estaría en el día siguiente.

## Qué acciones permite

| Endpoint | Estado |
|---|---|
| `GET /api/dashboard/resumen` | Demo 1 — datos ficticios tipados (`ResumenDashboard`) |

La proyección "mañana necesitas en caja" se calculará como la suma de las
órdenes de compra con `fecha_estimada_llegada` = mañana que aún no se pagan.

## Cómo interactúa la IA

El AI Companion usa este endpoint como fuente única del estado del día para
explicar cualquier cifra en lenguaje simple ("mañana necesitas S/ 320 porque
llega el pedido de Distribuidora Norte") y decidir a qué módulo navegar.

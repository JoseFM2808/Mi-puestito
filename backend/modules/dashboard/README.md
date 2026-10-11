# Módulo backend: Dashboard / Caja Diaria

## Qué es

API del resumen diario (`docs/03-modulos/Modulo-Dashboard.md`): total cobrado hoy, proyección de caja para mañana,
órdenes abiertas, fiados por cobrar, ventas rápidas pendientes y pedidos por llegar. El cálculo vive en `servicio.py`;
`router.py` solo lo expone.

## Qué datos maneja

No tiene tablas propias: **lee** las de Ventas y Compras del proyecto del token. Cada sección va en su propio `try`: si
un módulo no puede leerse, su parte sale en cero y se nombra en `secciones_no_disponibles`, y el resto se muestra igual.
Demo y negocio real usan exactamente el mismo cálculo (demo trae datos de muestra, `backend/datos_demo.py`).

- **Vendiste hoy**: ventas `pagada_cerrada` + `pendiente_formalizar` cerradas dentro del día de Lima.
- **Mañana necesitas en caja**: Σ de pedidos `pendiente`/`en_camino` con llegada mañana, con el motivo en palabras.
- **Fiados por cobrar**: Σ de deudas positivas (derivadas, ver Ventas) y cuántos clientes deben.

El día se calcula con `fechas.dia_peruano()` (America/Lima), nunca con el reloj del servidor.

## Qué acciones permite

| Endpoint | Acción |
|---|---|
| `GET /api/dashboard/resumen` | Resumen del día (`ResumenDashboard`) |

## Cómo interactúa la IA

Es la única fuente de cifras del Asistente: `modules/asistente` usa `servicio.calcular_resumen` (seudonimizado antes de
salir) para explicar cualquier número en lenguaje simple, por ejemplo "mañana necesitas S/ 320 porque llega el pedido de
Distribuidora Norte".

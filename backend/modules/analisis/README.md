# Módulo backend: Análisis

## Qué es

"¿El puesto es rentable?" (Fase 7, `docs/03-modulos/Modulo-Analisis.md`). Solo lee: no tiene tablas propias. Cada parte
se calcula dentro de un `try`; si un módulo falla, esa parte queda en cero y se nombra en `no_disponibles`.

## Qué datos maneja

- **Vendido**: ventas cobradas (como "Vendiste hoy": pagadas y rápidas, por `cerrada_en`) sumadas por día peruano.
- **Pagado a proveedores, gastos del puesto y de la casa**: tabla `gastos` (ADR-051).
- **Resultado del negocio** = vendido − proveedores − gastos del puesto; **libre** = resultado − gastos de la casa.
- **Fiados por cobrar**: la deuda derivada de hoy (no cuenta como vendido hasta que se abona).
- **Mejores productos**: por producto del inventario con costo, lo vendido menos cantidad × `costo_ultimo` (D-22).
  Es un estimado. Los 5 que más dejan.

## Qué acciones permite

| Endpoint | Acción |
|---|---|
| `GET /api/analisis?periodo=semana\|mes\|mes_pasado` | El período (semana desde el lunes, mes hasta hoy, o el mes pasado completo) con `por_dia` |

## Cómo interactúa la IA

El Asistente recibe en su contexto `semana` y `mes` (vendido, proveedores, gastos, resultado del negocio y libre): ya
responde "¿cuánto vendí esta semana?" o "¿cuánto gané este mes?" con cifras reales. Lleva a la pantalla
"¿Cómo me va?" y corrige hacia ella un "Ir a la Caja" cuando se habla de la semana o el mes.

# Módulo backend: Caja

## Qué es

La caja de cada día (D-24, ADR-051): empieza con un saldo en **efectivo** y otro en **Yape** (decisión del owner,
2026-11-17), sube con lo cobrado por cada medio y baja con los gastos. Responde "¿cuánto tengo ahora?" por separado en
la gaveta y en el Yape.

## Qué datos maneja (tablas)

- **`aperturas_caja`**: una por día peruano (`dia` único): `efectivo_inicial`, `yape_inicial` (céntimos, ≥ 0), `uuid`,
  `creado_en`, `actualizado_en`.

Lee, sin importarlos al cargar:

- **Ingresos**: la tabla `pagos` de Ventas (ventas cobradas y abonos de fiado) del día, agrupada por `metodo_pago`.
- **Egresos**: `gastos.servicio.total_por_medio` (gastos del puesto y del hogar, incluidos los pagos a proveedores).

Si una de las dos partes falla, queda en cero y se nombra en `no_disponibles`: la caja se muestra igual (un módulo
caído no tumba otro).

## Qué acciones permite

| Endpoint | Acción |
|---|---|
| `POST /api/caja/apertura` | Con cuánto empieza la caja hoy. Repetirla el mismo día **corrige** los saldos (gana la última) |
| `GET /api/caja?dia=AAAA-MM-DD` | `inicial`, `ingresos`, `egresos` y `en_caja` (= inicial + ingresos − egresos), por medio |

El día de la apertura sale de `ocurrido_en` (la hora del dispositivo): una caja abierta sin red cuenta para su día real.

## Cómo interactúa la IA

El Asistente recibe `caja_abierta` y `en_caja` en su contexto: responde "¿cuánto tengo en efectivo?" con esas cifras
(el verificador de cifras las acepta porque están en el contexto) y puede señalar `dashboard.en-caja`.

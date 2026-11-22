# Módulo backend: Gastos

## Qué es

Lo que **sale** de la caja (D-24, ADR-051, `docs/03-modulos/Modulo-Gastos.md`): del puesto (alquiler, transporte, luz,
pagar un pedido al proveedor) o de la casa (comida, colegio). Separarlos deja ver si el negocio gana o si la casa se lo
está comiendo. Ventas y Compras no dependen de este módulo; Compras le avisa por el evento `compra.pagada`.

## Qué datos maneja (tablas)

- **`gastos`**: `uuid` (del dispositivo), `monto` (céntimos, > 0), `medio` (`efectivo` | `yape_plin`), `ambito`
  (`puesto` | `hogar`), `categoria` (`proveedor`, `alquiler`, `servicios`, `transporte`, `alimentacion`, `educacion`,
  `otros`), `descripcion` opcional, `orden_compra_uuid` (único, solo el pago de un pedido) y `creado_en`.

Reglas clave:

- Idempotente por `uuid`: la cola offline puede reenviar sin duplicar (`201` la primera vez, `200` las siguientes).
- Un pedido se paga una sola vez: `orden_compra_uuid` es único y el suscriptor revisa antes de insertar.
- Un gasto no se rechaza aunque la caja quede negativa: es un hecho; la Caja lo muestra en rojo.
- Borrar un gasto mal anotado lo elimina (no movió stock ni deuda, solo la caja). Borrar dos veces no hace nada.

## Qué acciones permite

| Endpoint | Acción |
|---|---|
| `POST /api/gastos` | Anotar un gasto (`GastoEntrada`) |
| `DELETE /api/gastos/{uuid}` | Borrar un gasto mal anotado (`204`, idempotente) |
| `GET /api/gastos?dia=AAAA-MM-DD` | Los gastos de un día peruano (hoy por defecto) con totales por medio y por ámbito |
| Evento `compra.pagada` | Lo pagado a un proveedor se anota como gasto del puesto, categoría `proveedor` |

`servicio.total_por_medio(sesion, dia)` es lo que lee la Caja, sin que la Caja importe este módulo al cargar.

## Cómo interactúa la IA

El Asistente puede llevar a la pantalla Gastos ("quiero anotar un gasto") y señalar `gastos.anotar`. No anota gastos por
su cuenta. Las cifras de gastos le llegan solo dentro de `en_caja` (lo que queda), no la lista de gastos.

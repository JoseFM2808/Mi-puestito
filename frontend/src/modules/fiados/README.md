# Módulo: Fiados (frontend)

## Qué es

Quién debe y cuánto, y registrar lo que cada cliente abona. La deuda la calcula el servidor (Σ fiado − Σ abonos); aquí
no se guarda ningún saldo.

## Qué datos maneja

- `GET /api/ventas/fiados`: clientes con deuda, del que más debe al que menos, con su límite de crédito si tiene.
- Un abono se encola (`sincronizacion/cola.ts`) con su propio `uuid`, así que se guarda aunque no haya red; la deuda se
  descuenta en pantalla al instante y el servidor la confirma al sincronizar.

## Qué acciones permite

| Acción                           | Botón                                     |
| -------------------------------- | ----------------------------------------- |
| Registrar lo que pagó un cliente | **Registrar un pago** → **Guardar abono** |
| Ver el total que te deben        | Card "Te deben en total"                  |

Si alguien paga de más, el servidor avisa que tiene saldo a favor.

## Cómo interactúa la IA

`data-ai-id`: `fiados`, `fiados.total`, `fiados.sin-conexion`, `fiados.cliente-<uuid>` y sus `.abonar`,
`.monto-abono`, `.guardar-abono`, `.cancelar-abono`. El Asistente responde "¿quién me debe más?" con el resumen de caja
(nombres seudonimizados hacia el modelo) y puede sugerir "Ir a Fiados".

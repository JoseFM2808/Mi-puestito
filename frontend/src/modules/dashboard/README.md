# Módulo: Dashboard / Caja Diaria (frontend)

## Qué es

Pantalla principal ("Caja de hoy", `docs/03-modulos/Modulo-Dashboard.md`): resumen del día y proyección de mañana, con
las cifras reales del proyecto que vienen de `GET /api/dashboard/resumen`.

## Qué datos maneja

- Lee el resumen con `api/cliente.ts` y lo convierte con `leerResumen` (céntimos enteros, ADR-033).
- Guarda la última caja conocida en IndexedDB (`instantaneas`): **sin conexión** la muestra y dice de qué hora es.
- Se vuelve a leer al abrir y cada vez que la cola offline termina de enviar cambios.
- Si el backend no pudo leer una sección (`secciones_no_disponibles`), lo dice en palabras y muestra el resto.
- Fechas en `formato.ts` (`es-PE`, zona `America/Lima`); un pedido vencido dice "Debió llegar … (atrasado)", nunca "Llega
  hoy".

## Qué acciones permite

| Acción                                       | Resultado                                             |
| -------------------------------------------- | ----------------------------------------------------- |
| Tocar una orden abierta, **Registrar venta** | Va a Ventas                                           |
| **Venta rápida**                             | Va a Ventas con el formulario de venta rápida abierto |
| Tocar **Fiados por cobrar**                  | Va a Fiados                                           |
| **Llegó un pedido**                          | Aviso: llega con el módulo Compras (Fase 4)           |
| **Volver a intentar**                        | Relee la caja tras un error                           |

## Cómo interactúa la IA

`data-ai-id` disponibles: `dashboard`, `dashboard.fecha`, `dashboard.ventas-hoy`, `dashboard.proyeccion-manana`,
`dashboard.ordenes-activas`, `dashboard.orden-activa-<uuid>`, `dashboard.fiados`, `dashboard.ventas-rapidas`,
`dashboard.pedidos-por-llegar`, `dashboard.pedido-<id>`, `dashboard.registrar-venta`, `dashboard.venta-rapida`,
`dashboard.llego-pedido`, `dashboard.sin-conexion`, `dashboard.error`. El Asistente explica estas cifras con el mismo
resumen y puede sugerir "Ir a la Caja de hoy".

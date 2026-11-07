# Componente: Menú lateral

## Qué es

La navegación de toda la app, siempre a la izquierda (Design-System §6). En pantalla ancha (desde 1000 px) está fija y a
la vista; en la angosta entra desde la izquierda con el botón **Menú** de la barra superior.

## Qué datos maneja

- La pantalla actual y si el panel está abierto (`stores/navegacion.ts`). Las opciones salen de `PANTALLAS`, cada una con
  nombre y para qué sirve.
- El nombre del negocio activo (`stores/sesion.ts`).

## Qué acciones permite

| Acción                | Control                                                        |
| --------------------- | -------------------------------------------------------------- |
| Ir a una pantalla     | Una opción grande por pantalla: ícono, nombre y para qué sirve |
| Saber dónde estoy     | La opción actual va en color fuerte y dice "Aquí estás"        |
| Copia de los datos    | **Guardar una copia de mis datos** / **Recuperar una copia**   |
| Reiniciar la práctica | Solo en demo, con confirmación en dos pasos                    |
| Salir                 | **Salir de este negocio**                                      |
| Cerrar (teléfono)     | **Cerrar menú**, tocar fuera, Escape o elegir una pantalla     |

## Cómo interactúa la IA

`data-ai-id`: `menu`, `menu.negocio`, `menu.ir-<pantalla>` (`caja`, `ventas`, `fiados`, `compras`, `inventario`,
`asistente`), `menu.cerrar`, `menu.salir`. La opción actual lleva `aria-current="page"`. El Asistente nunca navega solo:
sugiere un botón y el operador decide.

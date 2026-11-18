# Módulo: ¿Cómo me va? (Análisis)

## Qué es

La pantalla que responde "¿el puesto es rentable?" (Fase 7). Opción **¿Cómo me va?** del menú.

## Qué datos maneja

- `GET /api/analisis?periodo=` con **Esta semana**, **Este mes** o **El mes pasado**. Sin red muestra el último análisis
  guardado en IndexedDB (`analisis`, por período) y dice de cuándo es.
- Se recalcula al abrir y cada vez que la cola termina de enviar cambios.

## Qué acciones permite

| Acción            | Resultado                                          |
| ----------------- | -------------------------------------------------- |
| Elegir el período | **Esta semana** / **Este mes** / **El mes pasado** |

Se ve: **Te quedó libre** con una frase en palabras simples (`resumenEnPalabras`), lo vendido, lo pagado a proveedores,
los gastos del puesto y de la casa, los fiados, el día por día (barras con la cifra escrita al lado: el color acompaña,
no reemplaza) y lo que más ganancia deja.

## Cómo interactúa la IA

`data-ai-id`: `analisis`, `analisis.periodo-<periodo>`, `analisis.libre`, `analisis.cuentas`, `analisis.vendido`,
`analisis.proveedores`, `analisis.gastos-puesto`, `analisis.gastos-casa`, `analisis.fiados`, `analisis.por-dia`,
`analisis.mejores-productos`. El Asistente tiene las cifras de la semana y del mes y lleva aquí.

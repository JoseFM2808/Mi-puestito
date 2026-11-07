# Componente: Barra superior

## Qué es

Franja fija (`sticky top`) presente en **toda** la experiencia, definida en
`docs/06-diseno/Design-System.md` (sección 6). No pertenece a ningún módulo:
es el punto de anclaje de la navegación, del AI Companion y del selector de
tamaño de letra.

## Qué datos maneja

- **Tamaño de letra** del operador, leído/escrito en el store Zustand
  `src/stores/preferencias.ts`. Tres niveles: Normal (20px), Grande (23px),
  Muy grande (27px). Se persiste en `sessionStorage` (dura la sesión; vuelve a
  Normal en una sesión nueva). El cambio escribe `data-letra` en `<html>` y
  toda la UI re-escala vía la escala rem de `tokens.css`.

## Qué acciones permite

| Acción              | Resultado                                                                                                                                                                       |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Menú**            | Abre el panel lateral izquierdo: el negocio activo, las pantallas, la copia de los datos y **Salir de este negocio**. Se cierra con **Cerrar menú**, tocando fuera o con Escape |
| **Asistente**       | Abre o cierra el panel del Asistente (`componentes/asistente`)                                                                                                                  |
| **Tamaño de letra** | Cambia entre los 3 niveles; persiste durante la sesión                                                                                                                          |

Debajo de la barra aparece el estado de conexión cuando hay cambios por enviar o no hay red
(`componentes/sincronizacion/EstadoSincronizacion.tsx`).

## Cómo interactúa la IA

`data-ai-id` disponibles para que el AI Companion identifique y accione:

- `barra` — el contenedor completo
- `barra.menu`, `barra.menu-abierto`, `barra.negocio` — Menú y su contenido
- `barra.ir-caja`, `barra.ir-ventas`, `barra.ir-fiados`, `barra.salir` — navegación
- `barra.asistente` — botón Asistente (color `--ia`, identidad del Companion)
- `barra.letra-normal`, `barra.letra-grande`, `barra.letra-muygrande` — selector

Si el usuario pide "letra más grande", la IA puede sugerir el siguiente nivel del selector. El botón Asistente es el
hogar visual permanente del Companion: mismo color y lugar siempre.

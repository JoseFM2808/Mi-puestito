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

| Acción                                            | Estado en Demo 1                                       |
| ------------------------------------------------- | ------------------------------------------------------ |
| **Menú** — abrir navegación entre módulos         | Muestra un aviso: se activa cuando existan más módulos |
| **Asistente** — abrir el AI Companion             | Muestra un aviso: llega con la capa de IA              |
| **Tamaño de letra** — cambiar entre los 3 niveles | Funcional y persistente por sesión                     |

## Cómo interactúa la IA

`data-ai-id` disponibles para que el AI Companion identifique y accione:

- `barra` — el contenedor completo
- `barra.menu` — botón Menú
- `barra.asistente` — botón Asistente (color `--ia`, identidad del Companion)
- `barra.letra-normal`, `barra.letra-grande`, `barra.letra-muygrande` — selector
- `barra.aviso` — texto del aviso visible (región `aria-live`)

Si el usuario pide "letra más grande", la IA puede pulsar el siguiente nivel
del selector. El botón Asistente es el hogar visual permanente del Companion:
mismo color y lugar siempre.

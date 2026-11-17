---
id: mi-puestito.nucleo.readme
proyecto: Mi-puestito
medio: nucleo
nucleo: propio
nombre: "Mi Puestito"
concepto: "Paleta Mercado: cálida y familiar, con el color reservado al dinero y letra Lexend que se lee de lejos."
estado: aceptado
version: 1.0.0
actualizado: 2026-11-08
dueno: José
tokens: []
prompt: no
---

# Design System · Mi Puestito

Núcleo de marca del estándar de Design System por carpetas (alternativa C, ADR-008 de Estudio-Contenido): identidad,
logo y tokens viven aquí; las aplicaciones por medio (social, video, web…) viven en el hub y heredan de este núcleo.

| Archivo | Qué es |
|---|---|
| [tokens/tokens.json](tokens/tokens.json) | **Fuente única** de color, tipografía y forma (W3C DTCG 2025.10, roles comunes) |
| `tokens/tokens.css` (gen) | Variables para el código: roles (`--color-fondo`) y alias con los nombres del producto |
| `DESIGN.md` (gen) | Resumen para agentes de código y Google Stitch |
| [marca/](marca/) | Esencia, voz y tono, logo, color, tipografía, iconografía e imagen |
| [CHANGELOG.md](CHANGELOG.md) | Cambios con fecha y motivo |

Aplicaciones por medio en el hub: `Estudio-Contenido/docs/design-system/proyectos/mi-puestito/` (medios activos: social, video, web).
Después de cambiar `tokens/tokens.json` o un `.md` de `marca/`, corre `py run.py ds-generar` en Estudio-Contenido: regenera
`tokens.css`, `DESIGN.md` y los prompts. `py run.py ds-validar --proyecto "Mi-puestito"` revisa este núcleo (también lo
hace el sync de contexto).

**Copia, no traslado.** El documento de diseño del producto sigue en [docs/06-diseno/Design-System.md](../06-diseno/Design-System.md)
y el frontend importa [docs/06-diseno/tokens.css](../06-diseno/tokens.css) (alias `@tokens`). Este núcleo reúne lo de
marca con el formato del estándar (enlaces markdown normales, sin wikilinks); el validador comprueba que los colores de
`tokens.css` sigan iguales a `tokens.json`. Mover `06-diseno/` aquí espera la aprobación de José (ADR-048).

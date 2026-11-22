---
id: mi-puestito.nucleo.readme
proyecto: Mi-puestito
medio: nucleo
nucleo: propio
nombre: "Mi Puestito"
concepto: "Paleta Mercado: cálida y familiar, con el color reservado al dinero y letra Lexend que se lee de lejos."
estado: aceptado
version: 1.0.0
actualizado: 2026-11-17
dueno: José
tokens: []
prompt: no
---

# Design System · Mi Puestito

Núcleo de marca del estándar de Design System por carpetas (alternativa C, ADR-008 de Estudio-Contenido): identidad,
logo y tokens viven aquí; las aplicaciones por medio (social, video, web…) viven en el hub y heredan de este núcleo.

| Archivo                                  | Qué es                                                                                                                                                                                                                                      |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [tokens/tokens.json](tokens/tokens.json) | **Fuente única** de color, tipografía y forma (W3C DTCG 2025.10, roles comunes)                                                                                                                                                             |
| `tokens/tokens.css` (gen)                | Variables para el código: roles (`--color-fondo`) y alias con los nombres del producto                                                                                                                                                      |
| `DESIGN.md` (gen)                        | Resumen para agentes de código y Google Stitch                                                                                                                                                                                              |
| [marca/](marca/)                         | Esencia, voz y tono, logo, color, tipografía, iconografía e imagen                                                                                                                                                                          |
| [CHANGELOG.md](CHANGELOG.md)             | Cambios con fecha y motivo                                                                                                                                                                                                                  |
| [producto/](producto/)                   | Lo propio de la interfaz: [Design-System.md](producto/Design-System.md) (documento de diseño del producto, bóveda Obsidian) y [tokens-producto.css](producto/tokens-producto.css) (espaciado, escala tipográfica, tamaños táctiles, tintes) |

Aplicaciones por medio en el hub: `Estudio-Contenido/docs/design-system/proyectos/mi-puestito/` (medios activos: social, video, web).
Después de cambiar `tokens/tokens.json` o un `.md` de `marca/`, corre `py run.py ds-generar` en Estudio-Contenido: regenera
`tokens.css`, `DESIGN.md` y los prompts. `py run.py ds-validar --proyecto "Mi-puestito"` revisa este núcleo (también lo
hace el sync de contexto).

**Una sola fuente de color (ADR-050).** El frontend importa, en este orden, `tokens/tokens.css` (generado desde
`tokens.json`: colores, fuente y radios, con los alias del producto como `--fondo`, `--primario`, `--ia`) y
[producto/tokens-producto.css](producto/tokens-producto.css), que no define colores de marca. Cambiar un color es cambiar
`tokens.json` y correr `py run.py ds-generar`; un test del frontend falla si un CSS usa un token que no existe.

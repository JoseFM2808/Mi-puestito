---
id: mi-puestito.nucleo.tipografia
proyecto: Mi-puestito
medio: nucleo
estado: aceptado
version: 1.0.0
actualizado: 2026-11-08
dueno: José
tokens: [tipo.cuerpo]
prompt: si
---

# Mi Puestito · Tipografía

## Regla
Una sola familia, Lexend, con una jerarquía que se lee de lejos: monto > título > subtítulo > nota.

## Valores
| Elemento | Tamaño (en Normal, raíz de 20 px) | Peso |
|---|---|---|
| Monto principal (caja) | 2.5rem (50 px) | 700 |
| Título de página | 1.8rem (36 px) | 700 |
| Título de sección | 1.45rem (29 px) | 700 |
| Nombre de cliente / monto de orden | 1.25–1.7rem | 600–700 |
| Subtítulo de tarjeta | 1.15rem (23 px) | 600 |
| Botón | 1.2rem (24 px) | 600 |
| Nota | 1.05rem (21 px) | 400–500 |

Tres tamaños de letra siempre visibles (Normal 20 px, Grande 23 px, Muy grande 27 px) re-escalan toda la interfaz.

## Así sí / Así no
- Así sí: montos con números tabulares
- Así no: una segunda familia

## Para el modelo
- Una sola familia, {tipo.cuerpo}; montos con números tabulares; jerarquía que se lee de lejos: monto > título > subtítulo > nota.

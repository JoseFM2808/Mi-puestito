---
id: mi-puestito.nucleo.color
proyecto: Mi-puestito
medio: nucleo
estado: aceptado
version: 1.0.0
actualizado: 2026-11-08
dueno: José
tokens: [color.accion, color.aviso, color.peligro, color.info]
prompt: si
---

# Mi Puestito · Color

## Regla
Salvo el azul del Asistente, el color solo comunica dinero: verde entra, ámbar pendiente, rojo deuda o vencido. Nunca va
solo: siempre con palabra (también cubre el daltonismo).

## Valores
| Rol | Valor | Uso |
|---|---|---|
| `color.fondo` | `#FAF7F2` | Fondo general |
| `color.superficie` | `#FFFFFF` | Tarjetas, barra superior, campos |
| `color.tinta` / `color.texto` | `#2B2620` | Texto principal |
| `color.texto-suave` | `#6E6357` | Notas, rótulos secundarios |
| `color.linea` | `#E8E0D4` | Bordes suaves |
| `color.accion` | `#1E6E42` | Acciones principales e ingresos |
| `color.aviso` | `#B45F06` | Por cobrar, órdenes abiertas |
| `color.peligro` | `#A33A2E` | Fiado, vencidos, errores |
| `color.info` | `#1A5A8A` | Identidad del Asistente |

Los tintes suaves (`--tinte-*`), `--borde-fuerte` y las sombras son del producto y siguen en `docs/06-diseno/tokens.css`.

## Así sí / Así no
- Así sí: "Te deben S/ 45" en rojo ladrillo y con la palabra
- Así no: verde para decorar un título

## Para el modelo
- Salvo el azul del Asistente {color.info}, el color solo comunica dinero: verde {color.accion} entra, ámbar {color.aviso} pendiente, rojo {color.peligro} deuda o vencido.
- El color nunca va solo: siempre acompañado de la palabra.

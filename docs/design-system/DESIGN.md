---
version: alpha
name: "Mi Puestito"
description: "Paleta Mercado: cálida y familiar, con el color reservado al dinero y letra Lexend que se lee de lejos."
colors:
  primary: "#1E6E42"
  fondo: "#FAF7F2"
  superficie: "#FFFFFF"
  tinta: "#2B2620"
  texto: "#2B2620"
  texto-suave: "#6E6357"
  linea: "#E8E0D4"
  accion: "#1E6E42"
  sobre-accion: "#FFFFFF"
  acento: "#1E6E42"
  sobre-acento: "#FFFFFF"
  exito: "#1E6E42"
  aviso: "#B45F06"
  peligro: "#A33A2E"
  info: "#1A5A8A"
typography:
  cuerpo:
    fontFamily: "Lexend"
  display:
    fontFamily: "Lexend"
  datos:
    fontFamily: "Lexend"
rounded:
  s: 11px
  m: 14px
  l: 14px
spacing:
  base: 8px
---

<!-- (gen) Generado por `py run.py ds-generar` (Estudio-Contenido) desde tokens/tokens.json y marca/*.md. No lo edites: cambia la fuente y vuelve a generar. -->

# Mi Puestito · DESIGN.md

## Overview

Paleta Mercado: cálida y familiar, con el color reservado al dinero y letra Lexend que se lee de lejos.

- Usa el lenguaje de la persona, no del sistema: "Anotar un pago", "Llegó un pedido", "Cuánto te queda".
- Los botones llevan siempre texto completo; un ícono nunca reemplaza la palabra.

Tema principal: claro. Fuente única: `tokens/tokens.json` (W3C DTCG 2025.10); `tokens/tokens.css` es la salida para el código.

## Colors

| Rol | claro | Alias en el producto | Uso |
|---|---|---|---|
| `color.fondo` | `#FAF7F2` | `--fondo` | Blanco hueso cálido: no brilla bajo luz natural |
| `color.superficie` | `#FFFFFF` | `--superficie` | Tarjetas, barra superior, campos |
| `color.tinta` | `#2B2620` | `--texto` | Marrón casi negro: contraste alto sin dureza |
| `color.texto` | `#2B2620` | — | Texto de lectura |
| `color.texto-suave` | `#6E6357` | `--texto-suave` | Notas y rótulos secundarios |
| `color.linea` | `#E8E0D4` | `--borde` | Bordes suaves de tarjetas |
| `color.accion` | `#1E6E42` | `--primario` | Verde billete: acciones principales e ingresos |
| `color.sobre-accion` | `#FFFFFF` | — | Texto sobre color.accion |
| `color.acento` | `#1E6E42` | — | Lo que hay que recordar va en el mismo verde |
| `color.sobre-acento` | `#FFFFFF` | — | Texto sobre color.acento |
| `color.exito` | `#1E6E42` | — | Entra dinero |
| `color.aviso` | `#B45F06` | `--pendiente` | Ámbar tierra: por cobrar, órdenes abiertas |
| `color.peligro` | `#A33A2E` | `--deuda` | Rojo ladrillo: fiado, vencidos, errores |
| `color.info` | `#1A5A8A` | `--ia` | Azul del Asistente: el único color fuera de la lógica del dinero |

- Salvo el azul del Asistente color.info (#1A5A8A), el color solo comunica dinero: verde color.accion (#1E6E42) entra, ámbar color.aviso (#B45F06) pendiente, rojo color.peligro (#A33A2E) deuda o vencido.
- El color nunca va solo: siempre acompañado de la palabra.

## Typography

- `tipo.cuerpo`: "Lexend", sans-serif (Familia única: mejora la lectura con baja fluidez lectora)
- `tipo.display`: "Lexend", sans-serif
- `tipo.datos`: "Lexend", sans-serif (Montos en Lexend con números tabulares)
- Una sola familia, tipo.cuerpo ("Lexend", sans-serif); montos con números tabulares; jerarquía que se lee de lejos: monto > título > subtítulo > nota.

## Layout

- Contraste de texto de 4,5:1 o más (3:1 en texto grande, iconos y bordes de controles).
- Foco visible en todo control; respeta prefers-reduced-motion.
- El color nunca va solo: acompáñalo de una palabra o un icono con nombre accesible.
- Usa los componentes que el producto ya documenta antes de crear uno nuevo.
- Todo estado (reposo, hover, foco, activo, deshabilitado, error, cargando) usa tokens, nunca valores sueltos.
- Mobile first: funciona desde 360 px de ancho; breakpoints en 768, 1024 y 1440 px. Sin scroll horizontal de la página.
- Espacios en múltiplos de 8 px. Controles de 44 × 44 px o más.
- Claro y oscuro salen de los mismos roles de color; nunca colores sueltos en el código.

## Shapes

- `radio.s`: 11px
- `radio.m`: 14px
- `radio.l`: 14px
- Cada ícono va con su nombre y para qué sirve; nunca cambia entre versiones ni reemplaza la palabra.

## Components

Los componentes del producto se documentan en su repo (ver `README.md` de esta carpeta). Usa solo tokens: nunca colores ni medidas sueltos.

## Do's and Don'ts

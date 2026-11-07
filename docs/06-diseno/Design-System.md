# Design System

#diseno

Documento de diseño centralizado y **fuente de verdad visual** del proyecto: si un token cambia aquí, cambia en toda la interfaz. Los componentes React importan estos valores desde un punto central (variables CSS, ver `tokens.css`); ningún componente usa colores, tamaños ni espaciados "a mano".

> Paleta elegida: **A — "Mercado"** (cálida, familiar). Validada en preview (`assets/preview-caja-diaria.html`) sobre la pantalla de [[Modulo-Dashboard]].

## 1. Colores (tokens)

| Token | Hex | Uso |
|---|---|---|
| `--fondo` | `#FAF7F2` | Fondo general (blanco hueso cálido, no brilla bajo luz natural) |
| `--texto` | `#2B2620` | Texto principal (marrón casi negro, contraste alto sin dureza) |
| `--texto-suave` | `#6E6357` | Notas, rótulos secundarios |
| `--primario` | `#1E6E42` | Acciones principales e ingresos (verde billete) |
| `--pendiente` | `#B45F06` | Montos por cobrar / órdenes abiertas (ámbar tierra) |
| `--deuda` | `#A33A2E` | Fiado, vencidos, errores (rojo ladrillo) |
| `--superficie` | `#FFFFFF` | Cards, barra superior, campos |
| `--borde` | `#E8E0D4` | Bordes suaves de cards |
| `--borde-fuerte` | `#C9BFAF` | Bordes de campos y separadores |
| `--ia` | `#1A5A8A` | Identidad del [[AI-Companion]] (azul, único color fuera de la lógica del dinero) |

**Regla del color:** salvo el azul del Asistente, el color SOLO comunica dinero — verde entra, ámbar pendiente, rojo deuda/vencido. El color nunca va solo: siempre acompañado de palabra (también cubre daltonismo).

## 2. Tipografía

- **Familia única: Lexend** — diseñada para mejorar la lectura en personas con baja fluidez lectora (nuestro [[Publico-Objetivo]]).
- **Escala en `rem`** sobre una raíz de 20px (tamaño "Normal"). Toda la UI escala desde la raíz — ver selector de tamaño (sección 5).
- **Números tabulares** (`font-variant-numeric: tabular-nums`) en todos los montos.

| Elemento | Tamaño (en Normal) | Peso |
|---|---|---|
| Monto principal (caja) | 2.5rem (50px) | 700 |
| Título de página | 1.8rem (36px) | 700 |
| Título de sección | 1.45rem (29px) | 700 |
| Nombre de cliente / monto de orden | 1.25–1.7rem | 600–700 |
| Subtítulo de card (etiqueta) | 1.15rem (23px) | 600 |
| Botón | 1.2rem (24px) | 600 |
| Nota / texto suave | 1.05rem (21px) | 400–500 |

**Jerarquía que debe leerse de lejos:** monto > título > subtítulo > nota.

## 3. Espaciado y controles táctiles

- Base de espaciado: **8px** (múltiplos: 0.4rem, 0.8rem, 1.2rem…).
- **Objetivos táctiles ≥ 56px** de alto (botones de acción 3.2rem; controles de barra ~2.9rem).
- Aire generoso entre cards (gap ~0.8–0.9rem) para evitar toques accidentales.
- Los botones crecen con la letra (padding en rem): nunca quedan chicos para su texto al subir el tamaño.

## 4. Texto sobre íconos (regla dura)

- **Botones siempre con texto completo:** "Registrar venta", "Cerrar orden", "Llegó un pedido". Nunca un ícono solo.
- Si se acompaña con ícono: el ícono **jamás** reemplaza la palabra y **jamás** cambia entre versiones.
- Razón: el [[Publico-Objetivo]] no descifra significados por logo.

## 5. Selector de tamaño de letra (decisión de UX)

- **Presente en toda la experiencia**, en la barra superior fija — nunca enterrado en configuración.
- Tres niveles **siempre visibles**: Normal (20px), Grande (23px), Muy grande (27px). Cada botón muestra "Aa" al tamaño real.
- Cambia el `font-size` de la raíz → **toda la interfaz re-escala** proporcionalmente.
- **Persistencia:** se conserva durante toda la sesión del operador. Por defecto, Normal.

## 6. Menú lateral y barra superior

- **Menú siempre a la izquierda**, en el mismo lugar en todas las pantallas:
  - Pantalla ancha (desde 1000 px: computadora, tablet echada): fijo y siempre visible.
  - Pantalla angosta (teléfono, tablet parada): el mismo panel entra desde la izquierda con el botón **Menú**, sobre la
    pantalla y con el fondo oscurecido. Se cierra con "Cerrar menú", tocando fuera, con Escape o al elegir una pantalla.
- Cada opción lleva **ícono + nombre + para qué sirve** ("Fiados · Quién te debe"). La pantalla actual se marca con
  color fuerte **y** con las palabras "Aquí estás".
- Al final del menú, separadas, las acciones del negocio: copia de los datos, reiniciar la práctica y **Salir**.
- **Barra superior** (`sticky top`, fondo `--superficie`, borde y `--sombra-barra`): a la izquierda **Menú** (solo en
  pantalla angosta) y **Asistente**; a la derecha "Tamaño de letra" con los tres tamaños. En pantalla angosta el selector
  baja a una segunda fila.

## 6 bis. Pensado para personas mayores

Criterios tomados de apps diseñadas para personas mayores (teléfonos y launchers simplificados, banca y salud para
adultos mayores) y de las pautas WCAG 2.2:

- **Siempre se sabe dónde se está:** cada pantalla abre con su título y una frase de para qué sirve
  (`TituloPagina ayuda=…`), y el menú dice "Aquí estás".
- **Lo frecuente, primero y grande:** la Caja de hoy empieza con "¿Qué quieres hacer?": accesos grandes con dibujo,
  nombre y explicación. El más usado (Registrar venta) va relleno; en teléfono ocupa la fila entera.
- **Nada escondido:** sin gestos, sin menús de tres puntos, sin íconos sin texto. Lo destructivo pide confirmar en dos
  pasos con palabras ("Sí, reiniciar" / "No, dejarlo así").
- **Controles grandes y separados:** mínimo `--tactil-min` (56 px en Normal); las opciones del menú y los accesos, más.
- **Lenguaje de la persona, no del sistema:** "Anotar un pago", "Llegó un pedido", "Cuánto te queda".
- **Volver al inicio siempre a mano:** el menú lateral está a la vista en pantalla ancha y a un toque en la angosta.

## 6 ter. Asistente: apartado propio y ventana flotante

El [[AI-Companion]] tiene dos formas, con **la misma conversación**:

- **Apartado** (opción "Asistente" del menú): chat a pantalla completa, con quién habla dicho con palabras ("Tú",
  "Asistente"), preguntas sugeridas para empezar, la caja para escribir fija abajo y "Empezar una conversación nueva".
- **Ventana flotante** (botón "Asistente" de la barra): sobre la pantalla actual, abajo a la derecha en pantalla ancha y
  como hoja en la parte de abajo en el teléfono. **Sigue abierta al cambiar de pantalla**: si el Asistente lleva a
  Fiados, el operador ve Fiados detrás. Así podrá observar al Asistente cuando, más adelante, guíe paso a paso o actúe
  en la app. Botones "Pantalla completa" y "Cerrar"; desde el apartado, "Usar en ventana mientras trabajo".
- La ventana no tapa la barra ni el menú, que quedan por encima.

## 7. Teclado

- Se usa **el teclado nativo de la tablet** (Android / iPad), que aparece al tocar un campo de texto.
- No se construye ni se fuerza un teclado propio: el nativo ya respeta la accesibilidad del SO. Forzar lo contrario complicaría al usuario y contradice el propósito del proyecto.

## 8. Identidad del Asistente

- Color `--ia` (`#1A5A8A`) reservado para el [[AI-Companion]].
- Siempre el mismo color y lugar (botón "Asistente" en la barra y su opción en el menú). Única excepción a la regla
  del color del dinero.

## Implementación

- Los tokens se materializan en `tokens.css` (en esta misma carpeta), importado una vez al iniciar el frontend ([[Stack-Tecnologico]]).
- Cada componente expone su `data-ai-id` para el [[AI-Companion]].
- Decisiones registradas en [[Decisiones-Tecnicas]] (entradas 11–17 y 19–20).

## Estado
- Paleta, tipografía, escala, reglas de UX: **definidas y aprobadas**.
- Pendiente: tokens finos de componentes específicos (modales, tablas) se definirán al construir cada módulo.

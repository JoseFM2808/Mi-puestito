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

## 6. Barra superior fija

- Franja propia (`sticky top`), fondo `--superficie`, separada del contenido por borde y sombra sutil (token `--sombra-barra`). No invade contenido.
- **Izquierda:** botones de texto **Menú** (navegación) y **Asistente** ([[AI-Companion]], en color `--ia`), siempre visibles.
- **Derecha:** rótulo "Tamaño de letra" + los tres tamaños.
- En pantalla angosta, el selector de letra baja a una segunda fila sin pisar los botones.

## 7. Teclado

- Se usa **el teclado nativo de la tablet** (Android / iPad), que aparece al tocar un campo de texto.
- No se construye ni se fuerza un teclado propio: el nativo ya respeta la accesibilidad del SO. Forzar lo contrario complicaría al usuario y contradice el propósito del proyecto.

## 8. Identidad del Asistente

- Color `--ia` (`#1A5A8A`) reservado para el [[AI-Companion]].
- Siempre el mismo color y lugar (botón "Asistente" en la barra). Única excepción a la regla del color del dinero.

## Implementación

- Los tokens se materializan en `tokens.css` (en esta misma carpeta), importado una vez al iniciar el frontend ([[Stack-Tecnologico]]).
- Cada componente expone su `data-ai-id` para el [[AI-Companion]].
- Decisiones registradas en [[Decisiones-Tecnicas]] (entradas 11–17 y 19–20).

## Estado
- Paleta, tipografía, escala, reglas de UX: **definidas y aprobadas**.
- Pendiente: tokens finos de componentes específicos (modales, tablas) se definirán al construir cada módulo.

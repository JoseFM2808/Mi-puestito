# Cambios del Design System · Mi Puestito

Cada cambio dice qué se cambió, cuándo y por qué.

## 2026-11-08

- 2026-11-17 · Traslado (ADR-050): `docs/06-diseno/` pasa a `producto/`. El frontend toma los colores solo de `tokens/tokens.css` (generado desde `tokens.json`) y lo propio de `producto/tokens-producto.css`; se quita `css_producto`, que comparaba dos copias de los colores que ya no existen. Colores sin cambios.
- Núcleo en el estándar (ADR-048): `tokens/tokens.json` (W3C DTCG) con los roles comunes y `marca/` 01–07 a partir de `docs/06-diseno/Design-System.md`, con enlaces markdown normales. Colores sin cambios; el frontend sigue importando `docs/06-diseno/tokens.css`.
- Capa nueva en el Estudio (`proyectos/mi-puestito/`): social, video y web, con Lexend.

# Conexión Agnóstica al Modelo

#ia

**Principio:** cualquier modelo debe poder ejecutarse junto al programa. No se designa ningún proveedor (comercial o local) como permanente.

## Implementación

- Toda llamada a un modelo pasa por **una capa de abstracción única** (interfaz estándar de chat/completions).
- Cambiar de proveedor = cambiar configuración, **nunca** refactorizar código.
- Fase inicial: API comercial (por costo/simplicidad, un solo usuario).
- Fase futura: modelo local en hardware del usuario — el que sea. La elección concreta **está por definirse** y no condiciona la arquitectura.

## Por qué importa

1. El proyecto es open source: cada quien lo conecta al modelo que tenga.
2. Los precios y capacidades de los modelos cambian rápido; la app no debe quedar rehén de ninguno.
3. La documentación MD del proyecto es el contexto que cualquier modelo recibe — por eso es agnóstica por diseño. Ver [[AI-Companion]].

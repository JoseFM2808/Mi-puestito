# Conexión Agnóstica al Modelo

#ia

**Principio:** cualquier modelo debe poder ejecutarse junto al programa. No se designa ningún proveedor (comercial o local) como permanente.

## Implementación

- Toda llamada a un modelo pasa por **una capa de abstracción única** (interfaz estándar de chat/completions).
- Cambiar de proveedor = cambiar configuración, **nunca** refactorizar código.
- Fase inicial (implementada): NVIDIA NIM, por medio de un cliente genérico compatible con OpenAI
  (`backend/ia/compatible_openai.py`). El orden de modelos se mide con la llave del operador
  (`python -m ia.verificar`): primero los que responden **bien** una suma de prueba, luego por velocidad. Un modelo rápido
  que suma mal no sirve en una caja. `python -m ia.evaluar` mide además navegación, memoria y honestidad, y un verificador
  en el servidor descarta cualquier monto que no esté en los datos (decisión 42).
- El vendedor pone su llave en la pantalla del Asistente, cifrada en su computadora (decisión 43); no necesita tocar
  variables de entorno.
- Fase futura: modelo local en el dispositivo (Ollama o llama.cpp) con `MI_PUESTITO_IA_PROVEEDOR=local`, sin cambiar
  código. La dirección preferida es la familia Gemma 4 en su versión más pequeña, ajustada con fine-tuning a partir de
  intercambios reales seudonimizados (decisiones 36–39 de [[Decisiones-Tecnicas]]).

## Por qué importa

1. El proyecto es open source: cada quien lo conecta al modelo que tenga.
2. Los precios y capacidades de los modelos cambian rápido; la app no debe quedar rehén de ninguno.
3. La documentación MD del proyecto es el contexto que cualquier modelo recibe — por eso es agnóstica por diseño. Ver [[AI-Companion]].

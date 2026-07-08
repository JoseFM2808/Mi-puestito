# Orquestación de IA en Runtime

#ia

> **Runtime** = cuando la app está corriendo y siendo usada (la mamá de José en la tablet). Distinto del *development time* (José construyendo la app con Claude Code, ver [[Metodologia-Desarrollo]]).

## LangGraph como orquestador

El [[AI-Companion]] no es una sola llamada a un modelo: es un flujo con pasos (entender la pregunta → consultar datos/documentación → decidir si navegar → confirmar con el usuario → ejecutar). LangGraph modela esto como un **grafo con estado**:

- **Nodos:** clasificar intención, consultar contexto MD, generar respuesta, ejecutar navegación, rellenar formulario.
- **Checkpointing:** si la conexión se corta a mitad de un flujo, se retoma donde quedó (coherente con [[Sincronizacion-Offline]]).
- **Human-in-the-loop:** la IA siempre confirma antes de ejecutar acciones en la UI.

## Por qué LangGraph y no CrewAI

Menor consumo de tokens (importante: la IA inicial corre sobre API comercial), control explícito del flujo, y mejor integración con modelos locales para el futuro. Registrado en [[Decisiones-Tecnicas]].

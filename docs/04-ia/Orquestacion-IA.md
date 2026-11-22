# Orquestación de IA en Runtime

#ia

> **Runtime** = cuando la app está corriendo y siendo usada (la mamá de José en la tablet). Distinto del *development time* (José construyendo la app con Claude Code, ver [[Metodologia-Desarrollo]]).

## LangGraph como orquestador

El [[AI-Companion]] no es una sola llamada a un modelo: es un flujo con pasos (entender la pregunta → consultar datos/documentación → decidir si navegar → confirmar con el usuario → ejecutar). LangGraph modela esto como un **grafo con estado**:

- **Nodos:** clasificar intención, consultar contexto MD, generar respuesta, ejecutar navegación, rellenar formulario.
- **Checkpointing:** si la conexión se corta a mitad de un flujo, se retoma donde quedó (coherente con [[Sincronizacion-Offline]]).
- **Human-in-the-loop:** la IA siempre confirma antes de ejecutar acciones en la UI.

## Cómo está hoy (2026-11-22, ADR-057)

El grafo vive en `backend/ia/servicio.py` (`grafo()`):

`preparar` (configuración, prompt con datos, recuerdos, pantalla y manual) → `generar` (el siguiente modelo por
prioridad, con reintento si el fallo es pasajero) → `verificar` (separa las líneas de control y descarta un monto sin
respaldo) → fin. Si un modelo falla o inventa, vuelve a `generar` con el siguiente; si no queda ninguno, `sin_respuesta`
dice que no tiene la cifra o que no pudo responder.

- **Consultar contexto MD:** si el operador pide ayuda, el prompt lleva la tabla "Qué acciones permite" del README de la
  pantalla (ADR-056).
- **Human-in-the-loop:** el Asistente llena (órdenes, pagos, gastos, mermas, pedidos) y el operador guarda; navegar y
  señalar no cambian datos.
- **Checkpointing:** no hace falta dentro de una pregunta (dura segundos); lo que se retoma tras un corte es la
  conversación, guardada en el dispositivo (ADR-052).
- Si LangGraph faltara en un empaquetado, `preguntar` recorre los mismos nodos en orden: el Asistente no se cae.

## Por qué LangGraph y no CrewAI

Menor consumo de tokens (importante: la IA inicial corre sobre API comercial), control explícito del flujo, y mejor integración con modelos locales para el futuro. Registrado en [[Decisiones-Tecnicas]].

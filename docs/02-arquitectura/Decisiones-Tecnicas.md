# Registro de Decisiones Técnicas

#arquitectura

> Registro histórico. Cada decisión nueva se agrega aquí con alternativas consideradas y razón.

| # | Decisión | Alternativas | Razón |
|---|---|---|---|
| 1 | React sobre Vue | Vue, HTML vanilla | Ecosistema AI-first más maduro; asistentes generan React más preciso; más datos de entrenamiento para una IA local futura |
| 2 | TypeScript | JavaScript puro | Tipado explícito = mayor legibilidad para IA y menos errores |
| 3 | FastAPI sobre Django | Django, Flask | Ligero, async nativo, OpenAPI automático |
| 4 | SQLite → PostgreSQL | MySQL, MongoDB | Desarrollo local sin infraestructura; mismo ORM (SQLAlchemy) al migrar a nube |
| 5 | Offline-first con IndexedDB | Solo cloud | Conectividad variable en mercados. Ver [[Sincronizacion-Offline]] |
| 6 | Documentación en Markdown | JSDoc, solo Swagger | El MD es contexto directo para la IA ([[AI-Companion]] y agentes de desarrollo) |
| 7 | AGENTS.md + Claude Code como base de desarrollo | BMAD-METHOD, Spec Kit total | Mínimo overhead para 1 dev; estándar portable cross-tool. Ver [[Metodologia-Desarrollo]] |
| 8 | Spec Kit solo selectivo | Spec Kit como flujo total | Útil en módulos grandes; pesado para fixes pequeños |
| 9 | LangGraph para runtime de IA | CrewAI, llamadas directas | Menor consumo de tokens, checkpointing, mejor soporte de modelos locales. Ver [[Orquestacion-IA]] |
| 10 | Conexión agnóstica al modelo | Acoplarse a un proveedor | Cualquier modelo debe poder ejecutarse junto al programa. Ver [[Conexion-Agnostica]] |
| 11 | Paleta "A — Mercado" (cálida) | Paleta C austera, B fría | Calidez familiar, bajo brillo bajo luz natural; validada en preview. Ver [[Design-System]] |
| 12 | Tipografía Lexend | Inter, system fonts | Diseñada para baja fluidez lectora ([[Publico-Objetivo]]) |
| 13 | Escala tipográfica en rem desde raíz | px fijos | Permite re-escalar toda la UI con un solo cambio (selector de letra) |
| 14 | Selector de tamaño de letra siempre visible y persistente | Enterrarlo en configuración | Decisión de UX para adulto mayor. Ver [[Design-System]] |
| 15 | Texto sobre íconos (regla dura) | Íconos | El usuario no descifra significados por logo |
| 16 | Teclado nativo de la tablet | Teclado propio | El nativo respeta accesibilidad del SO; uno propio complicaría al usuario |
| 17 | Barra superior fija (no lateral) | Barra lateral flotante | La lateral tapaba contenido y caía en zona de pulgares |
| 18 | Zustand para estado global del frontend | Redux, Context API | Mínimo boilerplate para 1 dev; middleware `persist` resuelve la persistencia por sesión del selector de letra. Ver [[Stack-Tecnologico]] |
| 19 | `tokens.css` se importa directo desde `docs/06-diseno/` (alias de Vite) | Copiarlo al frontend | Una sola fuente de verdad visual: si se copiara, las versiones se desviarían. Ver [[Design-System]] |
| 20 | Fuente Lexend empaquetada localmente (`@fontsource/lexend`) | Google Fonts CDN | Offline-first: la app debe verse igual sin internet |
| 21 | Tipo propio `FechaHoraUTC` para todas las fechas | `DateTime(timezone=True)` a secas | SQLite ignora la zona y devuelve fechas "ingenuas"; mezclarlas con fechas con zona rompe al sincronizar con PostgreSQL. Ver [[Sincronizacion-Offline]] |
| 22 | Límite de errores por módulo (React error boundary) | Un solo límite global | Materializa la regla "el fallo de un módulo no derriba otro": el resto de la app sigue viva |
| 23 | Zona horaria fija `America/Lima` al presentar fechas | Zona del dispositivo | Una tablet mal configurada no debe cambiar qué día muestra la caja |
| 24 | Ejecutable de escritorio con PyInstaller (backend + frontend en un archivo) | Electron, Tauri, instalador MSI | Sin segundo runtime ni segunda copia de la UI: reusa el backend y el build que ya existen. Ver [[Distribucion-Escritorio]] |
| 25 | Datos en la carpeta del usuario, no junto al ejecutable | Base de datos al lado del .exe | El .exe puede estar en una carpeta protegida; así los datos sobreviven al actualizar la app |
| 26 | Puerto recordado entre arranques (`puerto.txt`) | Puerto nuevo cada vez, puerto fijo a la fuerza | El puerto es parte del origen del navegador: si cambiara, IndexedDB y las preferencias quedarían huérfanas en cada arranque. Ver [[Distribucion-Escritorio]] |
| 27 | Restricciones e índices en el esquema desde el inicio | Añadirlos al llegar el volumen | Con datos reales exigirían migraciones; hoy son gratis y evitan pagos sin destino, filas huérfanas y proveedores duplicados |

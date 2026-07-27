# Distribución como aplicación de escritorio

#arquitectura

Además de la PWA para tablet ([[Stack-Tecnologico]]), el programa se distribuye
como **un solo archivo ejecutable** que el usuario descarga y abre con doble
clic. No hay que instalar Python, ni Node, ni configurar nada.

## Cómo funciona

El ejecutable contiene tres cosas empaquetadas juntas:

1. El intérprete de Python y el backend FastAPI.
2. El frontend ya construido (`frontend/dist`), servido por el mismo servidor.
3. Un lanzador (`backend/escritorio.py`) que:
   - usa **siempre el mismo puerto** (guardado en `puerto.txt` junto a los
     datos), y solo busca otro si quedó ocupado,
   - arranca el servidor en `127.0.0.1` — **nunca** se expone a la red,
   - espera a que responda y abre el navegador que el usuario ya usa.

> **Por qué el puerto no cambia:** el navegador identifica lo que guarda por
> *origen*, y el puerto forma parte del origen. Con un puerto nuevo en cada
> arranque, todo lo almacenado sin conexión (IndexedDB, preferencias, caché de
> la PWA) quedaría huérfano al reabrir el programa, anulando el pilar
> offline-first. Ver decisión 26 en [[Decisiones-Tecnicas]].

Al servirse todo desde una sola dirección, el frontend llama a `/api/...` sin
CORS y la aplicación **funciona sin internet**, coherente con la regla
offline-first de [[Sincronizacion-Offline]].

## Dónde se guardan los datos

Nunca junto al ejecutable (podría estar en una carpeta protegida, y el usuario
perdería todo al reemplazar el archivo por una versión nueva). La lógica vive
en `backend/rutas.py`:

| Sistema | Carpeta de datos |
|---|---|
| Windows | `%LOCALAPPDATA%\MiPuestito\mi_puestito.db` |
| macOS | `~/Library/Application Support/MiPuestito/` |
| Linux | `~/.local/share/MiPuestito/` |

El programa muestra esa ruta al arrancar, para que el vendedor sepa qué
archivo respaldar. Son datos sensibles (ventas, fiados, clientes): viven solo
en su computadora.

## Cómo se genera

```bash
cd frontend && npm ci && npm run build
cd ../backend && pip install -r requirements.txt -r requirements-empaquetado.txt
pyinstaller MiPuestito.spec --noconfirm      # → dist/MiPuestito.exe
```

**El ejecutable de Windows debe construirse en Windows:** PyInstaller no
compila para otro sistema operativo. Por eso existe el flujo
`.github/workflows/ejecutable-windows.yml`, que lo construye en una máquina
Windows, comprueba que arranca y responde, y publica el `.exe` como artefacto
descargable (o adjunto a la Release al publicar una etiqueta `v*`).

## Estado

- **Windows:** listo (receta `backend/MiPuestito.spec` + flujo automático).
- **macOS y Linux:** la misma receta funciona ejecutándola en ese sistema;
  falta añadir esos destinos al flujo automático.
- **Tablet:** se sigue usando la PWA instalable, que es el destino principal
  del [[Publico-Objetivo]].

Decisiones registradas en [[Decisiones-Tecnicas]] (entradas 24–26).

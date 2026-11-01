# Módulo backend: Respaldo

## Qué es

Guardar y recuperar una copia del archivo de datos de un negocio. Sin tablas propias: trabaja sobre el archivo SQLite
completo del proyecto autenticado, con la API de backup de SQLite. Las reglas están en `servicio.py` y la decisión en
ADR-044.

## Qué datos maneja

- La base del proyecto: ventas, fiados, clientes, proveedores, pedidos e inventario. **Son datos sensibles**: la copia
  va sin cifrar y la custodia quien la descarga.
- `respaldos/antes-de-restaurar-<proyecto>-<momento>.db`, en la carpeta de datos: lo que había antes de cada restauración.
- **No incluye** los PIN (`usuarios.json`), la llave de IA ni el secreto de sesión.

## Qué acciones permite

| Endpoint | Qué hace |
|---|---|
| `GET /api/respaldo/copia` | Descarga la copia, con `Cache-Control: no-store` |
| `POST /api/respaldo/restaurar` | Recibe el archivo en el cuerpo y reemplaza los datos (`204`) |

Rechaza un archivo que no sea de Mi Puestito o esté dañado (`400`), una copia de otro negocio o de una versión más nueva
(`409`), uno de más de 200 MB (`413`) y la falta de disco (`507`). Si falla al migrar, los datos vuelven a como estaban.

## Cómo interactúa la IA

No interactúa. El Asistente no puede descargar ni restaurar: solo el operador, desde el menú.

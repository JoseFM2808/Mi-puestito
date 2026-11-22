# Componente: Escanear código de barras (D-30)

## Qué es

`EscanearCodigo.tsx`: el botón **Escanear con la cámara**. Abre la cámara trasera dentro de la pantalla, lee el primer
código de barras con `BarcodeDetector` y lo entrega a quien lo usa. Lo usan Inventario (buscar y alta de producto) y
Ventas (elegir el producto).

## Qué datos maneja

Solo la imagen de la cámara mientras está abierta, y solo en el dispositivo: ninguna imagen se guarda ni se envía. La
cámara se apaga al leer, al tocar **Cancelar** o al salir de la pantalla. `escaner.ts` tiene la parte sin pantalla:
`escanerDisponible()`, los formatos (EAN-13/8, UPC, Code 128/39, ITF) y `limpiarCodigo()`.

## Qué acciones permite

| Acción                  | Botón                                          |
| ----------------------- | ---------------------------------------------- |
| Leer un código          | **Escanear con la cámara** y apuntar al código |
| Dejar de usar la cámara | **Cancelar**                                   |

Si el navegador no trae `BarcodeDetector` (Firefox, Safari de escritorio, Chrome en Linux), el botón no aparece: queda el
lector USB o Bluetooth, o escribir el código. Sin permiso de cámara se dice en palabras qué hacer.

## Cómo interactúa la IA

`data-ai-id`: el que le da quien lo usa (`inventario.escanear-buscar`, `inventario.escanear-codigo`,
`ventas-*.escanear`), `<id>-camara` mientras está abierta y `<id>-cancelar`. El Asistente puede señalar el botón, pero
no puede usar la cámara ni leer lo que ve.

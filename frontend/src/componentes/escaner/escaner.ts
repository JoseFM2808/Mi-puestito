/**
 * Leer un código de barras con la cámara del equipo (D-30), con `BarcodeDetector`, que
 * traen Chrome y Edge en Android y en computadoras con ChromeOS/Windows recientes. Todo
 * pasa en el dispositivo: ninguna imagen sale de él. Donde no existe (Firefox, Safari de
 * escritorio), el botón no aparece y queda el lector USB o Bluetooth, o escribir el código.
 */

/** Los códigos de productos de bodega: EAN/UPC y los de las balanzas y distribuidoras */
export const FORMATOS = ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_128', 'code_39', 'itf'] as const

export interface CodigoDetectado {
  rawValue: string
}

export interface Detector {
  detect: (fuente: HTMLVideoElement) => Promise<CodigoDetectado[]>
}

interface ConstructorDetector {
  new (opciones?: { formats: readonly string[] }): Detector
  getSupportedFormats?: () => Promise<string[]>
}

function constructorDetector(): ConstructorDetector | undefined {
  return (globalThis as unknown as { BarcodeDetector?: ConstructorDetector }).BarcodeDetector
}

/** El navegador puede leer códigos con la cámara */
export function escanerDisponible(): boolean {
  return Boolean(
    constructorDetector() && typeof navigator !== 'undefined' && navigator.mediaDevices?.getUserMedia,
  )
}

export async function crearDetector(): Promise<Detector> {
  const Constructor = constructorDetector()
  if (!Constructor) throw new Error('Este navegador no lee códigos con la cámara')
  const soportados = (await Constructor.getSupportedFormats?.()) ?? [...FORMATOS]
  const formatos = FORMATOS.filter((f) => soportados.includes(f))
  return new Constructor({ formats: formatos.length > 0 ? formatos : [...FORMATOS] })
}

/** Un código leído: sin espacios; los de producto son solo números y letras */
export function limpiarCodigo(crudo: string): string | null {
  const limpio = crudo.trim().replace(/\s+/g, '')
  return /^[0-9A-Za-z\-.]{4,64}$/.test(limpio) ? limpio : null
}

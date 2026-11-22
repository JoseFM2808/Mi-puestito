/**
 * Reconocer productos del inventario por su nombre, como lo diría una persona: sin
 * importar mayúsculas, tildes ni plurales ("3 leches gloria" → «Leche Gloria»).
 *
 * Lo usan la orden que llena el Asistente (enlazar cada línea con su producto, ADR-049) y
 * la conversación (el nombre de un producto se vuelve un enlace a su tarjeta del
 * inventario). Funciones puras: sin red ni estado.
 */

/** Lo mínimo que hace falta de un producto para reconocerlo */
export interface ConNombre {
  nombre: string
}

/** Un nombre de menos letras se parece a demasiadas palabras ("té" en "té lo marqué") */
const LARGO_MINIMO = 3

const PALABRA = /[\p{L}\p{N}]+/gu

function normal(palabra: string): string {
  return palabra.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase()
}

function palabras(texto: string): string[] {
  return (texto.match(PALABRA) ?? []).map(normal)
}

/** "leches" = "leche", "panes" = "pan", "papas" = "papa" (plurales simples del castellano) */
function mismaPalabra(a: string, b: string): boolean {
  return a === b || a === `${b}s` || a === `${b}es` || b === `${a}s` || b === `${a}es`
}

function coinciden(texto: string[], desde: number, nombre: string[]): boolean {
  return nombre.every((palabra, i) => desde + i < texto.length && mismaPalabra(texto[desde + i], palabra))
}

/**
 * El producto al que se refiere un nombre escrito, o null si no hay uno claro:
 * 1. el que tiene ese mismo nombre (con plurales y tildes de más o de menos);
 * 2. si no, el ÚNICO cuyo nombre contiene esas palabras seguidas ("arroz" → «Arroz Costeño»).
 * Si dos productos calzan, no se adivina.
 */
export function productoPorNombre<P extends ConNombre>(productos: P[], escrito: string): P | null {
  const buscado = palabras(escrito)
  if (buscado.length === 0) return null
  const exacto = productos.find((producto) => {
    const nombre = palabras(producto.nombre)
    return nombre.length === buscado.length && coinciden(buscado, 0, nombre)
  })
  if (exacto) return exacto
  const contienen = productos.filter((producto) => {
    const nombre = palabras(producto.nombre)
    return nombre.some((_, desde) => coinciden(nombre, desde, buscado))
  })
  return contienen.length === 1 ? contienen[0] : null
}

export interface Trozo<P> {
  texto: string
  /** Si este trozo nombra un producto del inventario */
  producto?: P
}

/**
 * Parte un texto en trozos, marcando dónde se nombra un producto del inventario. Gana el
 * nombre más largo ("Leche Gloria" antes que "Leche") y un trozo nunca se marca dos veces.
 */
export function trozosConProductos<P extends ConNombre>(texto: string, productos: P[]): Trozo<P>[] {
  const candidatos = productos
    .map((producto) => ({ producto, nombre: palabras(producto.nombre) }))
    .filter(({ nombre }) => nombre.join(' ').length >= LARGO_MINIMO)
    .sort((a, b) => b.nombre.length - a.nombre.length)
  if (candidatos.length === 0) return [{ texto }]

  const encontradas = [...texto.matchAll(PALABRA)].map((m) => ({
    normal: normal(m[0]),
    inicio: m.index ?? 0,
    fin: (m.index ?? 0) + m[0].length,
  }))
  const lista = encontradas.map((p) => p.normal)

  const trozos: Trozo<P>[] = []
  let cursor = 0
  let i = 0
  while (i < encontradas.length) {
    const hallado = candidatos.find(({ nombre }) => coinciden(lista, i, nombre))
    if (!hallado) {
      i += 1
      continue
    }
    const inicio = encontradas[i].inicio
    const fin = encontradas[i + hallado.nombre.length - 1].fin
    if (inicio > cursor) trozos.push({ texto: texto.slice(cursor, inicio) })
    trozos.push({ texto: texto.slice(inicio, fin), producto: hallado.producto })
    cursor = fin
    i += hallado.nombre.length
  }
  if (cursor < texto.length) trozos.push({ texto: texto.slice(cursor) })
  return trozos
}

/**
 * El producto con ese código de barras (D-22, D-30), si hay uno. El código se compara tal cual,
 * sin espacios: lo da un lector, la cámara o se escribe.
 */
export function productoPorCodigo<T extends { codigo_barras: string | null }>(
  productos: T[],
  codigo: string,
): T | undefined {
  const buscado = codigo.trim()
  if (!buscado) return undefined
  return productos.find((p) => p.codigo_barras !== null && p.codigo_barras === buscado)
}

/**
 * El Asistente señala una parte de la pantalla (ADR-047): la trae a la vista y la marca
 * unos segundos con el color del Asistente, para que el operador sepa dónde mirar o qué
 * tocar. Busca por `data-ai-id`, el mismo identificador que AGENTS.md exige en todo
 * componente interactivo. Solo marca: nunca toca, llena ni guarda nada.
 */

export const DURACION_RESALTADO_MS = 4000
const ESPERA_ENTRE_INTENTOS_MS = 100
// La pantalla nueva puede tardar en dibujarse (o en traer sus datos): se reintenta un rato
const INTENTOS = 30
const MARGEN_BAJO_LA_BARRA_PX = 16
const FORMATO_APARTADO = /^[a-z0-9]+(?:[.-][a-z0-9]+)*$/

let quitarAnterior: (() => void) | null = null

/** Si esa parte está dibujada AHORA en la pantalla (sin esperar a que aparezca). */
export function estaALaVista(apartado: string): boolean {
  return FORMATO_APARTADO.test(apartado) && document.querySelector(`[data-ai-id="${apartado}"]`) !== null
}

/**
 * Señala el elemento con ese `data-ai-id`. Devuelve una promesa que dice si lo encontró:
 * una lista vacía (sin órdenes abiertas, por ejemplo) no tiene nada que señalar.
 */
export function senalar(apartado: string): Promise<boolean> {
  return new Promise((resolver) => {
    // Un data-ai-id es siempre "modulo.parte": cualquier otra cosa no se busca
    if (!FORMATO_APARTADO.test(apartado)) return resolver(false)
    let restantes = INTENTOS
    const buscar = () => {
      const elemento = document.querySelector<HTMLElement>(`[data-ai-id="${apartado}"]`)
      if (!elemento) {
        restantes -= 1
        if (restantes > 0) window.setTimeout(buscar, ESPERA_ENTRE_INTENTOS_MS)
        else resolver(false)
        return
      }
      quitarAnterior?.()
      elemento.setAttribute('data-resaltado', 'si')
      // Queda justo debajo de la barra fija, que cambia de alto según el ancho y la letra; y
      // arriba ("start") y no al centro: en teléfono la hoja del Asistente tapa la mitad de abajo
      const barra = document.querySelector('[data-ai-id="barra"]')?.getBoundingClientRect().bottom ?? 0
      elemento.style.scrollMarginTop = `${Math.max(barra, 0) + MARGEN_BAJO_LA_BARRA_PX}px`
      elemento.scrollIntoView?.({ block: 'start', behavior: 'smooth' })
      const temporizador = window.setTimeout(
        () => elemento.removeAttribute('data-resaltado'),
        DURACION_RESALTADO_MS,
      )
      quitarAnterior = () => {
        window.clearTimeout(temporizador)
        elemento.removeAttribute('data-resaltado')
      }
      resolver(true)
    }
    buscar()
  })
}

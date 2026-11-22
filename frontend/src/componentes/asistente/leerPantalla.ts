/**
 * Lectura de la pantalla para el Asistente (Fase 6, AGENTS.md: "cada componente interactivo
 * lleva data-ai-id para que el AI Companion pueda identificarlo"). Antes de cada pregunta se
 * mandan las partes que el operador tiene a la vista: su `data-ai-id`, cómo se llaman (el texto
 * del botón, la etiqueta del campo) y si un campo está lleno o vacío. Así el Asistente puede
 * decir "pon el monto aquí" y señalar justo ese campo (`ACCION: resaltar <id>`).
 *
 * Nunca se manda lo escrito en un campo, solo si está lleno. Quedan fuera la barra, el menú y
 * el propio Asistente. Lo que se manda pasa por la seudonimización del servidor (ADR-034).
 */

export interface ElementoPantalla {
  id: string
  tipo: 'boton' | 'campo' | 'zona'
  texto: string
  lleno?: boolean
}

export const MAX_ELEMENTOS = 60
const MAX_TEXTO = 80
const FORMATO_ID = /^[a-z0-9]+(?:[.-][a-z0-9]+)*$/
/** Partes que no son de la pantalla de trabajo */
const FUERA =
  '[data-ai-id="barra"], [data-ai-id="menu"], [data-ai-id="asistente"], [data-ai-id="asistente-ventana"]'

function corto(texto: string | null | undefined): string {
  return (texto ?? '').replace(/\s+/g, ' ').trim().slice(0, MAX_TEXTO)
}

function visible(elemento: Element): boolean {
  // jsdom no calcula diseño: ahí todo cuenta como visible
  const conVisibilidad = elemento as Element & { checkVisibility?: () => boolean }
  return typeof conVisibilidad.checkVisibility === 'function' ? conVisibilidad.checkVisibility() : true
}

function describir(elemento: HTMLElement): Omit<ElementoPantalla, 'id'> {
  if (elemento instanceof HTMLButtonElement || elemento.getAttribute('role') === 'button') {
    return { tipo: 'boton', texto: corto(elemento.textContent) }
  }
  if (
    elemento instanceof HTMLInputElement ||
    elemento instanceof HTMLTextAreaElement ||
    elemento instanceof HTMLSelectElement
  ) {
    const etiqueta = elemento.labels?.[0]?.textContent ?? elemento.getAttribute('aria-label') ?? elemento.name
    return { tipo: 'campo', texto: corto(etiqueta), lleno: elemento.value.trim() !== '' }
  }
  // Una zona (tarjeta, lista): su encabezado o etiqueta, nunca todo su contenido
  const titulo =
    elemento.getAttribute('aria-label') ?? elemento.querySelector('h1, h2, h3, legend')?.textContent
  return { tipo: 'zona', texto: corto(titulo) }
}

/** Las partes con `data-ai-id` que el operador ve ahora en su pantalla de trabajo. */
export function leerPantalla(raiz: ParentNode = document): ElementoPantalla[] {
  const vistos = new Set<string>()
  const salida: ElementoPantalla[] = []
  for (const elemento of raiz.querySelectorAll<HTMLElement>('[data-ai-id]')) {
    const id = elemento.dataset.aiId ?? ''
    if (!FORMATO_ID.test(id) || vistos.has(id) || elemento.closest(FUERA) || !visible(elemento)) continue
    vistos.add(id)
    salida.push({ id, ...describir(elemento) })
    if (salida.length >= MAX_ELEMENTOS) break
  }
  return salida
}

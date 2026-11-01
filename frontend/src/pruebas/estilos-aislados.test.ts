import { readdirSync, readFileSync } from 'node:fs'
import { join, relative } from 'node:path'
import { describe, expect, it } from 'vitest'

/**
 * Fase 2: "Cuando Ventas traiga su propio .card, uno reestilará al otro en
 * silencio". Regla: cada módulo usa CSS Modules (*.module.css); el único CSS
 * global es el reset de estilos-base.css. Y ningún color "a mano": solo
 * tokens de docs/06-diseno/tokens.css.
 */

const RAIZ = join(__dirname, '..')
const GLOBALES_PERMITIDOS = ['estilos-base.css']

function archivosCss(carpeta: string): string[] {
  return readdirSync(carpeta, { withFileTypes: true }).flatMap((entrada) => {
    const ruta = join(carpeta, entrada.name)
    if (entrada.isDirectory()) return archivosCss(ruta)
    return entrada.name.endsWith('.css') ? [ruta] : []
  })
}

describe('estilos aislados por módulo', () => {
  const todos = archivosCss(RAIZ)

  it('no hay CSS global salvo el reset', () => {
    const globales = todos
      .filter((ruta) => !ruta.endsWith('.module.css'))
      .map((ruta) => relative(RAIZ, ruta).replaceAll('\\', '/'))
    expect(globales).toEqual(GLOBALES_PERMITIDOS)
  })

  it('ningún CSS escribe colores a mano', () => {
    const conColores = todos.filter((ruta) =>
      /#[0-9a-fA-F]{3,8}\b|rgba?\(/.test(readFileSync(ruta, 'utf8').replace(/\/\*[\s\S]*?\*\//g, '')),
    )
    expect(conColores.map((ruta) => relative(RAIZ, ruta))).toEqual([])
  })
})

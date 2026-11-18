import { readdirSync, readFileSync } from 'node:fs'
import { join, relative } from 'node:path'
import { describe, expect, it } from 'vitest'

/**
 * Fase 2: "Cuando Ventas traiga su propio .card, uno reestilará al otro en
 * silencio". Regla: cada módulo usa CSS Modules (*.module.css); el único CSS
 * global es el reset de estilos-base.css. Y ningún color "a mano": solo tokens de
 * docs/design-system/ (tokens/tokens.css generado + producto/tokens-producto.css, ADR-050).
 */

const RAIZ = join(__dirname, '..')
const DISENO = join(RAIZ, '..', '..', 'docs', 'design-system')
const ARCHIVOS_DE_TOKENS = [
  join(DISENO, 'tokens', 'tokens.css'),
  join(DISENO, 'producto', 'tokens-producto.css'),
]
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

  it('todo token que usa un CSS existe en el sistema de diseño', () => {
    const definidos = new Set(
      ARCHIVOS_DE_TOKENS.flatMap((ruta) =>
        [...readFileSync(ruta, 'utf8').matchAll(/(--[\w-]+)\s*:/g)].map((m) => m[1]),
      ),
    )
    const faltan = todos.flatMap((ruta) => {
      const texto = readFileSync(ruta, 'utf8')
      // Un módulo puede declarar sus propias variables locales: también cuentan como definidas
      const locales = new Set([...texto.matchAll(/(--[\w-]+)\s*:/g)].map((m) => m[1]))
      return [...texto.matchAll(/var\((--[\w-]+)/g)]
        .map((m) => m[1])
        .filter((nombre) => !definidos.has(nombre) && !locales.has(nombre))
        .map((nombre) => `${relative(RAIZ, ruta)}: ${nombre}`)
    })
    expect([...new Set(faltan)]).toEqual([])
  })
})

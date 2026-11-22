import { describe, expect, it } from 'vitest'
import { categoriasParaElegir, normalizarCategoria } from '../inventario/almacen'
import { lineaKardex, mesPeruano } from './Kardex'

describe('kardex mensual', () => {
  it('el mes es el de Lima, aunque en UTC ya sea el siguiente', () => {
    // 1 de diciembre 03:00 UTC = 30 de noviembre 22:00 en Lima
    const ahora = new Date('2026-12-01T03:00:00Z')
    expect(mesPeruano(0, ahora)).toBe('2026-11')
    expect(mesPeruano(-1, ahora)).toBe('2026-10')
    expect(mesPeruano(-1, new Date('2026-01-15T12:00:00Z'))).toBe('2025-12')
  })

  it('cada producto se dice con palabras y en su unidad', () => {
    const linea = lineaKardex({
      nombre: 'Arroz',
      unidad: 'kg',
      inicial: '45.000',
      registrado: '0.000',
      compras: '20.000',
      vendido: '7.000',
      mermas: '2.000',
      ajustes: '-1.000',
      final: '55.000',
    })
    expect(linea).toBe('Había 45 kg · entró 20 kg · vendiste 7 kg · se perdió 2 kg · restaste 1 kg al contar')
    expect(
      lineaKardex({
        nombre: 'Leche',
        unidad: 'unidad',
        inicial: '0.000',
        registrado: '12.000',
        compras: '0.000',
        vendido: '0.000',
        mermas: '0.000',
        ajustes: '-2.000',
        final: '10.000',
      }),
    ).toBe('Había 0 unidades · lo registraste con 12 unidades · restaste 2 unidades al contar')
  })
})

describe('categorías de producto', () => {
  it('se escriben como sea y se guardan iguales', () => {
    expect(normalizarCategoria('  lácteos  y  huevos ')).toBe('Lácteos y huevos')
    expect(normalizarCategoria('   ')).toBeNull()
    expect(normalizarCategoria(undefined)).toBeNull()
  })

  it('primero las que ya usa, luego las sugeridas sin repetir', () => {
    const opciones = categoriasParaElegir([
      { categoria: 'Panadería' },
      { categoria: 'Bebidas' },
      { categoria: null },
    ])
    expect(opciones.slice(0, 3)).toEqual(['Bebidas', 'Panadería', 'Abarrotes'])
    expect(opciones.filter((c) => c === 'Bebidas')).toHaveLength(1)
  })
})

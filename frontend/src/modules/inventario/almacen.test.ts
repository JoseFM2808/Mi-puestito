import { describe, expect, it } from 'vitest'
import type { ProductoCable } from '../../api/contrato'
import { aCantidad, aMilesimas, conEstado, formatearCantidad, leerCantidadEscrita } from './almacen'

describe('cantidades en milésimas', () => {
  it.each([
    ['5.000', 5000],
    ['5', 5000],
    ['0.250', 250],
    ['-2.500', -2500],
  ])('%s → %i', (texto, milesimas) => {
    expect(aMilesimas(texto)).toBe(milesimas)
  })

  it('ida y vuelta sin decimales sobrantes', () => {
    expect(aCantidad(5000)).toBe('5')
    expect(aCantidad(5250)).toBe('5.25')
    expect(aCantidad(-2500)).toBe('-2.5')
    expect(aCantidad(1)).toBe('0.001')
  })

  it('lee lo que escribe el operador y no adivina', () => {
    expect(leerCantidadEscrita('1,5')).toBe(1500)
    expect(leerCantidadEscrita(' 12 ')).toBe(12000)
    expect(leerCantidadEscrita('0')).toBe(0)
    expect(leerCantidadEscrita('-1')).toBeNull()
    expect(leerCantidadEscrita('1.2345')).toBeNull()
    expect(leerCantidadEscrita('dos')).toBeNull()
  })

  it('muestra la unidad en palabras', () => {
    expect(formatearCantidad(1000, 'unidad')).toBe('1 unidad')
    expect(formatearCantidad(12000, 'unidad')).toBe('12 unidades')
    expect(formatearCantidad(2500, 'kg')).toBe('2.5 kg')
    expect(formatearCantidad(1000, 'litro')).toBe('1 litro')
  })
})

describe('estado del producto, igual que el backend', () => {
  const base: ProductoCable = {
    uuid: 'p',
    nombre: 'Arroz',
    unidad: 'kg',
    precio_venta: null,
    stock_actual: '5.000',
    stock_minimo: '5.000',
    codigo_barras: null,
    tiene_vencimiento: false,
    bajo_minimo: false,
    descuadre: false,
  }

  it('en el mínimo ya es "queda poco"', () => {
    expect(conEstado(base).bajo_minimo).toBe(true)
    expect(conEstado({ ...base, stock_actual: '5.001' }).bajo_minimo).toBe(false)
  })

  it('stock negativo es descuadre; sin mínimo no avisa poco', () => {
    const negativo = conEstado({ ...base, stock_actual: '-1.000', stock_minimo: null })
    expect(negativo.descuadre).toBe(true)
    expect(negativo.bajo_minimo).toBe(false)
  })
})

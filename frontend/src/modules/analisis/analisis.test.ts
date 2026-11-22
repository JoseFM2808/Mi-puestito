import { describe, expect, it } from 'vitest'
import type { AnalisisCable } from '../../api/contrato'
import { resumenEnPalabras } from './Analisis'

const base: AnalisisCable = {
  periodo: 'semana',
  desde: '2026-11-16',
  hasta: '2026-11-17',
  vendido: '100.00',
  ventas: 3,
  pagado_a_proveedores: '40.00',
  gastos_del_puesto: '10.00',
  gastos_de_la_casa: '20.00',
  resultado_del_negocio: '50.00',
  libre: '30.00',
  fiados_por_cobrar: '0.00',
  por_dia: [],
  mejores_productos: [],
  por_categoria: [],
  no_disponibles: [],
}

describe('¿cómo me va?, en palabras simples', () => {
  it('si quedó plata libre, lo dice', () => {
    expect(resumenEnPalabras(base)).toMatch(/te quedó S\/\s?30\.00 libre/)
  })

  it('si el negocio dejó pero la casa gastó más, lo separa', () => {
    expect(resumenEnPalabras({ ...base, libre: '-5.00' })).toMatch(
      /El negocio dejó S\/\s?50\.00.*faltan S\/\s?5\.00/,
    )
  })

  it('si se gastó más de lo vendido, lo dice', () => {
    expect(resumenEnPalabras({ ...base, resultado_del_negocio: '-10.00', libre: '-30.00' })).toMatch(
      /gastaste más de lo que vendiste: faltan S\/\s?30\.00/,
    )
  })

  it('sin ventas no inventa conclusiones', () => {
    expect(resumenEnPalabras({ ...base, vendido: '0.00' })).toBe(
      'Todavía no hay ventas cobradas en este período.',
    )
  })
})

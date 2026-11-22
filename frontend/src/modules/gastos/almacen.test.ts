import { describe, expect, it } from 'vitest'
import type { GastoCable } from '../../api/contrato'
import { diaPeruano, totales } from './almacen'

const gasto = (monto: string, medio: GastoCable['medio'], ambito: GastoCable['ambito']): GastoCable => ({
  uuid: crypto.randomUUID(),
  monto,
  medio,
  ambito,
  categoria: 'otros',
  descripcion: null,
  orden_compra_uuid: null,
  creado_en: '2026-11-17T15:00:00Z',
})

describe('gastos del día', () => {
  it('suma por medio y separa el puesto de la casa, en céntimos exactos', () => {
    const suma = totales([
      gasto('0.10', 'efectivo', 'puesto'),
      gasto('0.20', 'efectivo', 'hogar'),
      gasto('12.50', 'yape_plin', 'puesto'),
    ])
    expect(suma).toEqual({ efectivo: 30, yape: 1250, puesto: 1260, hogar: 20 })
  })

  it('el día es el de Lima, no el del reloj UTC', () => {
    // 2026-11-18 03:00 UTC todavía es 17 de noviembre en Lima (UTC-5)
    expect(diaPeruano(new Date('2026-11-18T03:00:00Z'))).toBe('2026-11-17')
  })
})

import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  diasHastaHoy,
  estaAtrasado,
  formatearFechaRelativa,
  formatearMonto,
} from './formato'

function enDias(dias: number): Date {
  const fecha = new Date()
  fecha.setDate(fecha.getDate() + dias)
  return fecha
}

describe('formato de montos', () => {
  it('muestra soles con dos decimales', () => {
    expect(formatearMonto(485.5)).toContain('485.50')
    expect(formatearMonto(0)).toContain('0.00')
  })
})

describe('fechas relativas', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('nombra los próximos días en lenguaje simple', () => {
    expect(formatearFechaRelativa(enDias(0))).toBe('hoy')
    expect(formatearFechaRelativa(enDias(1))).toBe('mañana')
    expect(formatearFechaRelativa(enDias(2))).toBe('pasado mañana')
    expect(formatearFechaRelativa(enDias(5))).toMatch(/^el /)
  })

  it('NUNCA muestra una fecha pasada como "hoy"', () => {
    // Un pedido vencido presentado como que llega hoy engaña al vendedor
    // justo en la cifra con la que planifica su caja
    for (const dias of [-1, -2, -7, -30]) {
      const texto = formatearFechaRelativa(enDias(dias))
      expect(texto).not.toBe('hoy')
      expect(texto).toMatch(/atrasado/)
    }
  })

  it('distingue el atraso de ayer del de varios días', () => {
    expect(formatearFechaRelativa(enDias(-1))).toBe('ayer (atrasado)')
    expect(formatearFechaRelativa(enDias(-3))).toMatch(/atrasado 3 días/)
  })

  it('marca como atrasado solo lo que ya pasó', () => {
    expect(estaAtrasado(enDias(-1))).toBe(true)
    expect(estaAtrasado(enDias(0))).toBe(false)
    expect(estaAtrasado(enDias(1))).toBe(false)
  })

  it('usa el calendario de Perú, no el de la tablet', () => {
    // 04:00 UTC del 8 de julio = 23:00 del 7 de julio en Lima.
    // Para el vendedor sigue siendo el día 7: "hoy", no "mañana".
    vi.setSystemTime(new Date('2026-07-08T04:00:00Z'))
    expect(diasHastaHoy(new Date('2026-07-08T04:30:00Z'))).toBe(0)
    expect(formatearFechaRelativa(new Date('2026-07-08T04:30:00Z'))).toBe('hoy')
    // El día siguiente en Lima empieza a las 05:00 UTC
    expect(formatearFechaRelativa(new Date('2026-07-08T06:00:00Z'))).toBe('mañana')
  })
})

import { describe, expect, it } from 'vitest'
import {
  CAMPOS_DEL_CONTRATO,
  aCentimos,
  aSoles,
  formatearCentimos,
  leerMontoEscrito,
  leerResumen,
  type ResumenDashboardCable,
} from './contrato'
import openapi from './openapi.json'

describe('dinero en céntimos (ADR-033)', () => {
  it.each([
    ['485.50', 48550],
    ['0', 0],
    ['0.00', 0],
    ['12', 1200],
    ['12.5', 1250],
    ['-3.00', -300],
    ['132.50', 13250],
  ])('%s → %i céntimos', (texto, centimos) => {
    expect(aCentimos(texto)).toBe(centimos)
  })

  it('no adivina montos inválidos', () => {
    expect(() => aCentimos('1.234')).toThrow()
    expect(() => aCentimos('abc')).toThrow()
  })

  it('ida y vuelta exacta', () => {
    for (const centimos of [0, 1, 5, 99, 100, 48550, -300]) {
      expect(aCentimos(aSoles(centimos))).toBe(centimos)
    }
  })

  it('sumar céntimos es exacto donde los floats fallan', () => {
    const suma = ['0.10', '0.20'].map(aCentimos).reduce((a, b) => a + b, 0)
    expect(aSoles(suma)).toBe('0.30')
  })

  it('lee lo que escribe el operador, con punto o coma', () => {
    expect(leerMontoEscrito('12')).toBe(1200)
    expect(leerMontoEscrito('12,50')).toBe(1250)
    expect(leerMontoEscrito(' 7.5 ')).toBe(750)
    expect(leerMontoEscrito('')).toBeNull()
    expect(leerMontoEscrito('-5')).toBeNull()
    expect(leerMontoEscrito('3.999')).toBeNull()
  })

  it('formatea en soles peruanos', () => {
    expect(formatearCentimos(48550)).toMatch(/S\/\s?485\.50/)
  })
})

describe('contrato con el backend', () => {
  const esquemas = openapi as Record<string, { properties: string[]; required: string[] }>

  it.each(Object.entries(CAMPOS_DEL_CONTRATO))(
    '%s tiene exactamente los campos del API real',
    (nombre, campos) => {
      expect(esquemas[nombre], `openapi.json no tiene el esquema ${nombre}`).toBeDefined()
      expect([...campos].sort()).toEqual(esquemas[nombre].properties)
    },
  )

  it('convierte el resumen de caja', () => {
    const cable: ResumenDashboardCable = {
      ventas_hoy: '485.50',
      ventas_cerradas: 12,
      proyeccion_manana: '320.00',
      motivo_proyeccion: 'Llega pedido de Distribuidora Norte',
      ordenes_activas: [
        { uuid: 'u', nombre: 'Sra. Flora', tipo: 'fiado', monto: '12.00', deuda_cliente: '45.00' },
      ],
      fiados_por_cobrar: '132.50',
      clientes_con_fiado: 4,
      ventas_rapidas_pendientes: 3,
      pedidos_por_llegar: [{ id: 1, proveedor: 'Norte', fecha_estimada: '2026-09-29', monto: '320.00' }],
      secciones_no_disponibles: [],
    }
    const resumen = leerResumen(cable)
    expect(resumen.ventasHoy).toBe(48550)
    expect(resumen.ordenesActivas[0]).toMatchObject({ deudaCliente: 4500, monto: 1200 })
    // La fecha de llegada es el día peruano, no se corre por zona horaria
    expect(resumen.pedidosPorLlegar[0].fechaEstimada.toISOString().slice(0, 10)).toBe('2026-09-29')
  })
})

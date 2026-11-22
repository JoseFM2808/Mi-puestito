import { describe, expect, it } from 'vitest'
import type { ProveedorCable } from '../../api/contrato'
import { buscarProveedor, porAcabarse, repartirLlenado } from './formularios'

const proveedor = (nombre: string, empresa: string | null = null): ProveedorCable => ({
  uuid: nombre,
  nombre,
  empresa,
  ruc: null,
  telefono: null,
  categoria: null,
  creado_en: '',
})

describe('pedido que llenó el Asistente', () => {
  it('lo que tiene monto va al pedido y lo demás espera al operador', () => {
    const { listos, sinMonto } = repartirLlenado({
      proveedor: 'Distribuidora Norte',
      items: [
        { producto: 'Arroz', cantidad: '2 sacos', monto: '180.00' },
        { producto: 'Azúcar', cantidad: '1 saco', monto: null },
      ],
    })
    expect(listos).toEqual([{ nombre: 'Arroz', cantidad: '2 sacos', centimos: 18000 }])
    expect(sinMonto.map((i) => i.producto)).toEqual(['Azúcar'])
  })

  it('el proveedor se reconoce por nombre o empresa, sin importar mayúsculas', () => {
    const lista = [proveedor('Juan Pérez', 'Distribuidora Norte'), proveedor('Avícola Sur')]
    expect(buscarProveedor(lista, 'distribuidora norte')?.nombre).toBe('Juan Pérez')
    expect(buscarProveedor(lista, 'Avícola Sur')?.nombre).toBe('Avícola Sur')
    expect(buscarProveedor(lista, 'Otro')).toBeNull()
    expect(buscarProveedor(lista, null)).toBeNull()
  })
})

describe('lo que se está acabando (sugerencia por stock bajo)', () => {
  const productos = [
    { nombre: 'Arroz Costeño', bajo_minimo: true },
    { nombre: 'Leche Gloria', bajo_minimo: true },
    { nombre: 'Fideos Anita', bajo_minimo: false },
  ]

  it('solo lo que está bajo el mínimo y aún no está en el pedido', () => {
    expect(porAcabarse(productos, ['leche gloria ']).map((p) => p.nombre)).toEqual(['Arroz Costeño'])
    expect(porAcabarse(productos, []).map((p) => p.nombre)).toEqual(['Arroz Costeño', 'Leche Gloria'])
  })
})

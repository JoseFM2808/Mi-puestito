import { describe, expect, it } from 'vitest'
import type { ProveedorCable } from '../../api/contrato'
import { buscarProveedor, repartirLlenado } from './formularios'

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

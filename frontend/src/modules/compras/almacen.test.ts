import { describe, expect, it } from 'vitest'
import type { OrdenCompraCable } from '../../api/contrato'
import { aplicarRecepcion, diaPeruano } from './almacen'

function item(uuid: string, monto: string): OrdenCompraCable['items'][number] {
  return {
    uuid,
    nombre_producto: uuid,
    cantidad: null,
    monto,
    estado_recepcion: 'pendiente',
    producto_sustituto: null,
    monto_sustituto: null,
  }
}

const orden: OrdenCompraCable = {
  uuid: 'o',
  proveedor_uuid: 'p',
  proveedor: 'Sur',
  proveedor_telefono: null,
  estado: 'en_camino',
  fecha_estimada_llegada: null,
  monto_total: '180.00',
  monto_real: null,
  notas: null,
  items: [item('arroz', '100.00'), item('azucar', '50.00'), item('aceite', '30.00')],
}

// Mismos casos que tests/test_compras.py: lo que se ve sin red debe coincidir con el servidor
describe('recepción mostrada al instante', () => {
  it('el monto real cuenta solo lo que llegó', () => {
    const resultado = aplicarRecepcion(orden, [
      { itemUuid: 'arroz', estado: 'recibido' },
      { itemUuid: 'azucar', estado: 'no_recibido' },
      {
        itemUuid: 'aceite',
        estado: 'cambiado',
        productoSustituto: 'Aceite Sol',
        montoSustitutoCentimos: 3550,
      },
    ])
    expect(resultado.estado).toBe('recibida')
    expect(resultado.monto_real).toBe('135.50')
    expect(resultado.monto_total).toBe('180.00')
  })

  it('lo dejado pendiente mantiene el pedido abierto', () => {
    const resultado = aplicarRecepcion(orden, [
      { itemUuid: 'arroz', estado: 'recibido' },
      { itemUuid: 'azucar', estado: 'pendiente' },
      { itemUuid: 'aceite', estado: 'no_recibido' },
    ])
    expect(resultado.estado).toBe('en_camino')
    expect(resultado.monto_real).toBe('100.00')
  })

  it('completar lo pendiente después suma a lo ya recibido', () => {
    const parcial = aplicarRecepcion(orden, [
      { itemUuid: 'arroz', estado: 'recibido' },
      { itemUuid: 'azucar', estado: 'pendiente' },
      { itemUuid: 'aceite', estado: 'no_recibido' },
    ])
    const final = aplicarRecepcion(parcial, [{ itemUuid: 'azucar', estado: 'recibido' }])
    expect(final.estado).toBe('recibida')
    expect(final.monto_real).toBe('150.00')
  })
})

describe('día peruano', () => {
  it('tiene el formato que espera el API y mañana es otro día', () => {
    expect(diaPeruano()).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(diaPeruano(1) > diaPeruano()).toBe(true)
  })
})

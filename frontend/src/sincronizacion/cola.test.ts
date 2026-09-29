import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { ErrorApi, SinConexion } from '../api/cliente'
import { baseDe, cerrarBases, type Operacion } from './base-local'
import { alAplicarOperacion, encolar, esperarCola, procesarCola, useSincronizacion } from './cola'

const PROYECTO = 'prueba'

async function borrarBase() {
  cerrarBases()
  await baseDe(PROYECTO).delete()
  cerrarBases()
}

function operacion(ruta: string) {
  return { metodo: 'POST' as const, ruta, descripcion: `Operación ${ruta}`, cuerpo: { uuid: ruta } }
}

describe('cola offline', () => {
  beforeEach(borrarBase)
  afterEach(borrarBase)

  it('envía en orden y vacía la cola', async () => {
    const enviadas: string[] = []
    const enviar = async (op: Operacion) => void enviadas.push(op.ruta)
    await encolar(PROYECTO, operacion('/1'), async () => {
      throw new SinConexion()
    })
    await esperarCola()
    await encolar(PROYECTO, operacion('/2'), async () => {
      throw new SinConexion()
    })
    await esperarCola()
    await procesarCola(PROYECTO, enviar)

    expect(enviadas).toEqual(['/1', '/2'])
    expect(useSincronizacion.getState().pendientes).toBe(0)
  })

  it('sin red conserva todo y avisa que no hay conexión', async () => {
    await encolar(PROYECTO, operacion('/venta'), async () => {
      throw new SinConexion()
    })
    await esperarCola()
    expect(useSincronizacion.getState()).toMatchObject({ pendientes: 1, sinConexion: true })
    const [guardada] = await baseDe(PROYECTO).operaciones.toArray()
    expect(guardada).toMatchObject({ ruta: '/venta', estado: 'pendiente', intentos: 1 })
  })

  it('guarda la hora del dispositivo dentro de la operación', async () => {
    await encolar(PROYECTO, operacion('/venta'), async () => {
      throw new SinConexion()
    })
    await esperarCola()
    const [guardada] = await baseDe(PROYECTO).operaciones.toArray()
    expect(guardada.cuerpo?.ocurrido_en).toBe(guardada.creadaEn)
  })

  it('un rechazo del servidor se muestra y no frena a las demás', async () => {
    const enviadas: string[] = []
    const enviar = async (op: Operacion) => {
      if (op.ruta === '/mala') throw new ErrorApi(422, 'El detalle no cuadra')
      enviadas.push(op.ruta)
    }
    await encolar(PROYECTO, operacion('/mala'), async () => {
      throw new SinConexion()
    })
    await esperarCola()
    await encolar(PROYECTO, operacion('/buena'), async () => {
      throw new SinConexion()
    })
    await esperarCola()
    await procesarCola(PROYECTO, enviar)

    expect(enviadas).toEqual(['/buena'])
    const { rechazadas, pendientes } = useSincronizacion.getState()
    expect(pendientes).toBe(0)
    expect(rechazadas.map((r) => [r.ruta, r.error])).toEqual([['/mala', 'El detalle no cuadra']])
  })

  it('un error del servidor (5xx) se reintenta más tarde, no se descarta', async () => {
    await encolar(PROYECTO, operacion('/venta'), async () => {
      throw new ErrorApi(500, 'caído')
    })
    await esperarCola()
    expect(useSincronizacion.getState()).toMatchObject({ pendientes: 1, rechazadas: [] })
  })

  it('avisa a quien escucha con la respuesta del servidor', async () => {
    const recibidas: unknown[] = []
    const dejar = alAplicarOperacion((_op, respuesta) => recibidas.push(respuesta))
    await encolar(PROYECTO, operacion('/venta'), async () => ({ venta: { uuid: 'x' } }))
    await esperarCola()
    dejar()
    expect(recibidas).toEqual([{ venta: { uuid: 'x' } }])
  })

  it('cada proyecto tiene su propia cola', async () => {
    await encolar(PROYECTO, operacion('/demo'), async () => {
      throw new SinConexion()
    })
    await esperarCola()
    expect(await baseDe('otro').operaciones.count()).toBe(0)
    await baseDe('otro').delete()
  })
})

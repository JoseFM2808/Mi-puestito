import { beforeEach, describe, expect, it } from 'vitest'
import { baseDe, cerrarBases } from '../sincronizacion/base-local'
import { MAX_GUARDADOS, SALUDO, guardarAhora, useConversacion } from './conversacion'

async function recargarLaApp(proyecto: string) {
  // Recargar = el estado en memoria se pierde y se vuelve a abrir la base
  cerrarBases()
  useConversacion.setState({ proyecto: null, mensajes: [{ quienHabla: 'asistente', texto: SALUDO }] })
  await useConversacion.getState().usarProyecto(proyecto)
}

describe('conversación guardada en el dispositivo (D-26)', () => {
  beforeEach(async () => {
    cerrarBases()
    await baseDe('demo').delete()
    await baseDe('anita').delete()
    cerrarBases()
    useConversacion.setState({ proyecto: null, mensajes: [{ quienHabla: 'asistente', texto: SALUDO }] })
  })

  it('recargar la app no borra la conversación', async () => {
    await useConversacion.getState().usarProyecto('demo')
    useConversacion.getState().agregar({ quienHabla: 'operador', texto: '¿Cuánto vendí hoy?' })
    useConversacion
      .getState()
      .agregar({ quienHabla: 'asistente', texto: 'Vendiste S/ 485.50.', idRespuesta: 'x' })
    await guardarAhora()

    await recargarLaApp('demo')
    const textos = useConversacion.getState().mensajes.map((m) => m.texto)
    expect(textos).toEqual([SALUDO, '¿Cuánto vendí hoy?', 'Vendiste S/ 485.50.'])
  })

  it('cada negocio tiene su conversación', async () => {
    await useConversacion.getState().usarProyecto('demo')
    useConversacion.getState().agregar({ quienHabla: 'operador', texto: 'algo de demo' })
    await guardarAhora()

    await useConversacion.getState().usarProyecto('anita')
    expect(useConversacion.getState().mensajes.map((m) => m.texto)).toEqual([SALUDO])
    await useConversacion.getState().usarProyecto('demo')
    expect(useConversacion.getState().mensajes.at(-1)?.texto).toBe('algo de demo')
  })

  it('empezar una conversación nueva también la borra del dispositivo', async () => {
    await useConversacion.getState().usarProyecto('demo')
    useConversacion.getState().agregar({ quienHabla: 'operador', texto: 'hola' })
    useConversacion.getState().empezarDeNuevo()
    await guardarAhora()

    await recargarLaApp('demo')
    expect(useConversacion.getState().mensajes).toHaveLength(1)
  })

  it('se guardan solo los últimos mensajes, con el saludo al inicio', async () => {
    await useConversacion.getState().usarProyecto('demo')
    for (let i = 0; i < MAX_GUARDADOS + 10; i += 1) {
      useConversacion.getState().agregar({ quienHabla: 'operador', texto: `mensaje ${i}` })
    }
    await guardarAhora()

    await recargarLaApp('demo')
    const { mensajes } = useConversacion.getState()
    expect(mensajes).toHaveLength(MAX_GUARDADOS)
    expect(mensajes[0].texto).toBe(SALUDO)
    expect(mensajes.at(-1)?.texto).toBe(`mensaje ${MAX_GUARDADOS + 9}`)
  })
})

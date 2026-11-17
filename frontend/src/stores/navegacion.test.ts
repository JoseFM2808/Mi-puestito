import { beforeEach, describe, expect, it } from 'vitest'
import { useNavegacion } from './navegacion'

describe('navegación entre pantallas', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '#caja')
    useNavegacion.setState({ pantalla: 'caja', menuAbierto: false, abrirVentaRapida: false })
  })

  it('cada pantalla deja una entrada en el historial: Atrás vuelve a la anterior', () => {
    const antes = window.history.length
    useNavegacion.getState().irA('fiados')
    expect(window.location.hash).toBe('#fiados')
    expect(window.history.length).toBe(antes + 1)
  })

  it('ir a la pantalla actual no ensucia el historial', () => {
    const antes = window.history.length
    useNavegacion.getState().irA('caja')
    expect(window.history.length).toBe(antes)
  })

  it('la pantalla sigue al hash (Atrás, Adelante o un enlace)', () => {
    window.history.replaceState(null, '', '#ventas')
    window.dispatchEvent(new HashChangeEvent('hashchange'))
    expect(useNavegacion.getState().pantalla).toBe('ventas')
  })

  it('un hash desconocido lleva a la Caja de hoy', () => {
    useNavegacion.setState({ pantalla: 'ventas' })
    window.history.replaceState(null, '', '#no-existe')
    window.dispatchEvent(new HashChangeEvent('hashchange'))
    expect(useNavegacion.getState().pantalla).toBe('caja')
  })

  it('ir a otra pantalla cierra el menú', () => {
    useNavegacion.setState({ menuAbierto: true })
    useNavegacion.getState().irA('ventas')
    expect(useNavegacion.getState().menuAbierto).toBe(false)
  })

  it('el Asistente es un apartado propio: tiene su pantalla y su enlace', () => {
    useNavegacion.getState().irA('asistente')
    expect(useNavegacion.getState().pantalla).toBe('asistente')
    expect(window.location.hash).toBe('#asistente')
  })

  it('la ventana del Asistente sigue abierta al cambiar de pantalla', () => {
    useNavegacion.setState({ asistenteFlotante: true })
    useNavegacion.getState().irA('ventas')
    expect(useNavegacion.getState().asistenteFlotante).toBe(true)
  })

  it('del apartado a la ventana se vuelve a la pantalla de trabajo', () => {
    useNavegacion.getState().irA('fiados')
    useNavegacion.getState().irA('asistente')
    expect(useNavegacion.getState().asistenteFlotante).toBe(false)
    useNavegacion.getState().asistenteAVentana()
    expect(useNavegacion.getState().pantalla).toBe('fiados')
    expect(useNavegacion.getState().asistenteFlotante).toBe(true)
  })

  it('el Asistente lleva a una pantalla sin perder la conversación, aunque esté en su apartado', () => {
    useNavegacion.getState().irA('asistente')
    useNavegacion.setState({ asistenteAchicado: true })
    useNavegacion.getState().llevarConAsistente('compras')
    const estado = useNavegacion.getState()
    expect(estado.pantalla).toBe('compras')
    expect(window.location.hash).toBe('#compras')
    // Queda en ventana, abierta y grande: se sigue hablando mientras se llenan los datos
    expect(estado.asistenteFlotante).toBe(true)
    expect(estado.asistenteAchicado).toBe(false)
  })

  it('la ventana se achica a su barra y se vuelve a agrandar', () => {
    useNavegacion.setState({ asistenteFlotante: true, asistenteAchicado: false })
    useNavegacion.getState().alternarAchicado()
    expect(useNavegacion.getState().asistenteAchicado).toBe(true)
    useNavegacion.getState().alternarAchicado()
    expect(useNavegacion.getState().asistenteAchicado).toBe(false)
  })
})

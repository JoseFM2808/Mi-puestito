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
})

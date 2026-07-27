import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { LimiteErrores } from './LimiteErrores'

/** Módulo que falla mientras `fallando` sea true. */
let fallando = true
function ModuloDePrueba() {
  if (fallando) throw new Error('datos locales dañados')
  return <p>Contenido del módulo</p>
}

describe('LimiteErrores', () => {
  beforeEach(() => {
    fallando = true
    // React registra el error en consola: se silencia para no ensuciar la salida
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  /** El título se arma con varios nodos ("El módulo " + nombre + " tuvo…"). */
  const avisoDeFallo = () =>
    screen.getByText((_, elemento) => elemento?.className === 'titulo-error')

  it('muestra el módulo cuando todo va bien', () => {
    fallando = false
    render(
      <LimiteErrores nombreModulo="Caja de hoy" idModulo="dashboard">
        <ModuloDePrueba />
      </LimiteErrores>,
    )
    expect(screen.getByText('Contenido del módulo')).toBeDefined()
  })

  it('contiene el fallo y avisa con texto completo, sin derribar la app', () => {
    render(
      <LimiteErrores nombreModulo="Caja de hoy" idModulo="dashboard">
        <ModuloDePrueba />
      </LimiteErrores>,
    )
    expect(avisoDeFallo().textContent).toBe('El módulo Caja de hoy tuvo un problema')
    expect(screen.getByText('Volver a intentar')).toBeDefined()
  })

  it('"Volver a intentar" vuelve a montar el módulo y lo recupera', () => {
    render(
      <LimiteErrores nombreModulo="Caja de hoy" idModulo="dashboard">
        <ModuloDePrueba />
      </LimiteErrores>,
    )
    // Se resuelve la causa del fallo…
    fallando = false
    fireEvent.click(screen.getByText('Volver a intentar'))
    // …y el módulo revive sin recargar toda la aplicación
    expect(screen.getByText('Contenido del módulo')).toBeDefined()
  })

  it('si el fallo persiste, vuelve a mostrar el aviso (no queda en blanco)', () => {
    render(
      <LimiteErrores nombreModulo="Caja de hoy" idModulo="dashboard">
        <ModuloDePrueba />
      </LimiteErrores>,
    )
    fireEvent.click(screen.getByText('Volver a intentar'))
    expect(avisoDeFallo().textContent).toBe('El módulo Caja de hoy tuvo un problema')
  })
})

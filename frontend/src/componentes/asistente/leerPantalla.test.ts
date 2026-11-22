import { afterEach, describe, expect, it } from 'vitest'
import { leerPantalla } from './leerPantalla'

describe('lectura de la pantalla para el Asistente (Fase 6)', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('botones por su texto, campos por su etiqueta y si están llenos, sin el valor', () => {
    document.body.innerHTML = `
      <header data-ai-id="barra"><button data-ai-id="barra.menu">Menú</button></header>
      <main data-ai-id="ventas">
        <h1>Ventas</h1>
        <button data-ai-id="ventas.nueva">  Nueva   orden </button>
        <label for="m">Monto en soles</label><input id="m" data-ai-id="ventas-1.monto" value="12.50" />
        <label for="p">Producto</label><input id="p" data-ai-id="ventas-1.producto" value="" />
        <section data-ai-id="ventas.ordenes" aria-label="Órdenes abiertas"><p>Sra. Rosa S/ 20</p></section>
        <div data-ai-id="raro id con espacios"></div>
      </main>
      <section data-ai-id="asistente-ventana"><input data-ai-id="asistente-ventana.pregunta" /></section>`
    const leido = leerPantalla()
    expect(leido).toEqual([
      { id: 'ventas', tipo: 'zona', texto: 'Ventas' },
      { id: 'ventas.nueva', tipo: 'boton', texto: 'Nueva orden' },
      { id: 'ventas-1.monto', tipo: 'campo', texto: 'Monto en soles', lleno: true },
      { id: 'ventas-1.producto', tipo: 'campo', texto: 'Producto', lleno: false },
      { id: 'ventas.ordenes', tipo: 'zona', texto: 'Órdenes abiertas' },
    ])
    expect(JSON.stringify(leido)).not.toContain('12.50')
    expect(JSON.stringify(leido)).not.toContain('Rosa')
  })
})

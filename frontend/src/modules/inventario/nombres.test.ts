import { describe, expect, it } from 'vitest'
import { productoPorNombre, trozosConProductos } from './nombres'

const productos = [
  { nombre: 'Leche Gloria' },
  { nombre: 'Leche' },
  { nombre: 'Fideos Anita' },
  { nombre: 'Arroz Costeño' },
  { nombre: 'Papa amarilla' },
  { nombre: 'Papa blanca' },
  { nombre: 'Té' },
]

describe('reconocer un producto por cómo lo dice una persona', () => {
  it('sin importar mayúsculas, tildes ni plurales', () => {
    expect(productoPorNombre(productos, 'leches gloria')?.nombre).toBe('Leche Gloria')
    expect(productoPorNombre(productos, 'FIDEOS ANITA')?.nombre).toBe('Fideos Anita')
    expect(productoPorNombre(productos, 'arroz costeno')?.nombre).toBe('Arroz Costeño')
  })

  it('una parte del nombre basta si solo un producto la tiene', () => {
    expect(productoPorNombre(productos, 'arroz')?.nombre).toBe('Arroz Costeño')
    expect(productoPorNombre(productos, 'fideos')?.nombre).toBe('Fideos Anita')
  })

  it('si dos productos calzan, no adivina', () => {
    expect(productoPorNombre(productos, 'papa')).toBeNull()
    expect(productoPorNombre(productos, 'gaseosa')).toBeNull()
  })
})

describe('marcar productos dentro de un texto', () => {
  it('marca el nombre más largo y conserva el texto tal cual', () => {
    const trozos = trozosConProductos('Te llené 3 leches Gloria y 2 Fideos Anita.', productos)
    expect(trozos.map((t) => t.texto).join('')).toBe('Te llené 3 leches Gloria y 2 Fideos Anita.')
    expect(trozos.filter((t) => t.producto).map((t) => [t.texto, t.producto?.nombre])).toEqual([
      ['leches Gloria', 'Leche Gloria'],
      ['Fideos Anita', 'Fideos Anita'],
    ])
  })

  it('no marca nombres muy cortos ni palabras sueltas parecidas', () => {
    const trozos = trozosConProductos('Té lo marqué en la pantalla.', productos)
    expect(trozos.some((t) => t.producto)).toBe(false)
  })

  it('sin productos, el texto queda entero', () => {
    expect(trozosConProductos('Hola', [])).toEqual([{ texto: 'Hola' }])
  })
})

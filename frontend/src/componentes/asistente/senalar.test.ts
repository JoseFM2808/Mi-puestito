import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { DURACION_RESALTADO_MS, estaALaVista, senalar } from './senalar'

describe('el Asistente señala una parte de la pantalla', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    document.body.innerHTML = ''
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('marca el elemento unos segundos y luego lo deja como estaba', async () => {
    document.body.innerHTML = '<button data-ai-id="compras.nuevo-pedido">Nuevo pedido</button>'
    const boton = document.querySelector('button')
    expect(await senalar('compras.nuevo-pedido')).toBe(true)
    expect(boton?.getAttribute('data-resaltado')).toBe('si')
    vi.advanceTimersByTime(DURACION_RESALTADO_MS)
    expect(boton?.hasAttribute('data-resaltado')).toBe(false)
  })

  it('espera a que la pantalla nueva dibuje el elemento', async () => {
    const encontrado = senalar('ventas.nueva')
    vi.advanceTimersByTime(300)
    document.body.innerHTML = '<button data-ai-id="ventas.nueva">Nueva orden</button>'
    vi.advanceTimersByTime(100)
    expect(await encontrado).toBe(true)
  })

  it('si no existe, no marca nada y lo dice', async () => {
    const encontrado = senalar('ventas.ordenes')
    vi.advanceTimersByTime(5000)
    expect(await encontrado).toBe(false)
    expect(document.querySelector('[data-resaltado]')).toBeNull()
  })

  it('sabe si una parte está a la vista ahora, sin esperar', () => {
    document.body.innerHTML = '<button data-ai-id="compras.nuevo-pedido">Nuevo pedido</button>'
    expect(estaALaVista('compras.nuevo-pedido')).toBe(true)
    expect(estaALaVista('ventas.nueva')).toBe(false)
    expect(estaALaVista('a"], body, [x="')).toBe(false)
  })

  it('un apartado con formato raro no se busca', async () => {
    document.body.innerHTML = '<p data-ai-id="a">A</p>'
    expect(await senalar('a"], body, [x="')).toBe(false)
    expect(document.querySelector('[data-resaltado]')).toBeNull()
  })

  it('señalar otra parte quita la marca anterior', async () => {
    document.body.innerHTML = '<p data-ai-id="a">A</p><p data-ai-id="b">B</p>'
    await senalar('a')
    await senalar('b')
    expect(document.querySelectorAll('[data-resaltado]')).toHaveLength(1)
    expect(document.querySelector('[data-resaltado]')?.getAttribute('data-ai-id')).toBe('b')
  })
})

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { productoPorCodigo } from '../../modules/inventario/nombres'
import { EscanearCodigo } from './EscanearCodigo'
import { limpiarCodigo } from './escaner'

const detener = vi.fn()

function conCamara(codigos: string[][]) {
  let llamada = 0
  class DetectorFalso {
    static getSupportedFormats = () => Promise.resolve(['ean_13', 'code_128'])
    detect = () => Promise.resolve((codigos[llamada++] ?? []).map((rawValue) => ({ rawValue })))
  }
  vi.stubGlobal('BarcodeDetector', DetectorFalso)
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: { getUserMedia: vi.fn(() => Promise.resolve({ getTracks: () => [{ stop: detener }] })) },
  })
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue(undefined)
}

describe('escanear un código de barras con la cámara (D-30)', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
    detener.mockReset()
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: undefined })
  })

  it('sin BarcodeDetector el botón no aparece', () => {
    render(<EscanearCodigo aiId="prueba.escanear" alLeer={() => {}} />)
    expect(screen.queryByText('Escanear con la cámara')).toBeNull()
  })

  it('entrega el primer código válido y apaga la cámara', async () => {
    conCamara([[], ['  '], ['7751271001523']])
    const alLeer = vi.fn()
    render(<EscanearCodigo aiId="prueba.escanear" alLeer={alLeer} />)
    fireEvent.click(screen.getByText('Escanear con la cámara'))
    await waitFor(() => expect(alLeer).toHaveBeenCalledWith('7751271001523'), { timeout: 3000 })
    expect(alLeer).toHaveBeenCalledTimes(1)
    expect(detener).toHaveBeenCalled()
    expect(screen.getByText('Escanear con la cámara')).toBeTruthy()
  })

  it('cancelar apaga la cámara sin leer nada', async () => {
    conCamara([])
    const alLeer = vi.fn()
    render(<EscanearCodigo aiId="prueba.escanear" alLeer={alLeer} />)
    fireEvent.click(screen.getByText('Escanear con la cámara'))
    await waitFor(() => expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled())
    fireEvent.click(screen.getByText('Cancelar'))
    await waitFor(() => expect(detener).toHaveBeenCalled())
    expect(alLeer).not.toHaveBeenCalled()
  })

  it('sin permiso lo dice en palabras simples', async () => {
    conCamara([])
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia: () => Promise.reject(new DOMException('no', 'NotAllowedError')) },
    })
    render(<EscanearCodigo aiId="prueba.escanear" alLeer={() => {}} />)
    fireEvent.click(screen.getByText('Escanear con la cámara'))
    expect(await screen.findByText(/no tiene permiso para usar la cámara/)).toBeTruthy()
  })

  it('un código se limpia y se reconoce el producto', () => {
    expect(limpiarCodigo(' 7751271 001523 ')).toBe('7751271001523')
    expect(limpiarCodigo('ab')).toBeNull()
    const productos = [
      { nombre: 'Leche Gloria', codigo_barras: '7751271001523' },
      { nombre: 'Pan', codigo_barras: null },
    ]
    expect(productoPorCodigo(productos, '7751271001523 ')?.nombre).toBe('Leche Gloria')
    expect(productoPorCodigo(productos, '')).toBeUndefined()
    expect(productoPorCodigo(productos, '123')).toBeUndefined()
  })
})

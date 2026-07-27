import { useState } from 'react'
import { TAMANOS_LETRA, usePreferencias } from '../../stores/preferencias'
import './BarraSuperior.css'

/**
 * Barra superior fija de toda la experiencia (Design-System.md, sección 6).
 * Izquierda: Menú y Asistente. Derecha: selector de tamaño de letra.
 * En Demo 1, Menú y Asistente aún no navegan: muestran un aviso visible.
 */

const AVISOS = {
  menu: 'El Menú de navegación se activa cuando existan más módulos (Ventas, Compras…).',
  asistente: 'El Asistente llega con la capa de IA. Desde aquí te guiará y responderá.',
} as const

type Aviso = keyof typeof AVISOS

export function BarraSuperior() {
  const tamanoLetra = usePreferencias((estado) => estado.tamanoLetra)
  const cambiarTamanoLetra = usePreferencias((estado) => estado.cambiarTamanoLetra)
  const [avisoAbierto, setAvisoAbierto] = useState<Aviso | null>(null)

  const alternarAviso = (aviso: Aviso) => {
    setAvisoAbierto((actual) => (actual === aviso ? null : aviso))
  }

  return (
    <header className="barra-superior" data-ai-id="barra">
      <div className="barra-fila">
        <div className="barra-izq">
          <button
            type="button"
            className="btn-barra"
            data-ai-id="barra.menu"
            onClick={() => alternarAviso('menu')}
          >
            Menú
          </button>
          <button
            type="button"
            className="btn-barra asistente"
            data-ai-id="barra.asistente"
            onClick={() => alternarAviso('asistente')}
          >
            Asistente
          </button>
        </div>

        <div className="barra-der">
          <div className="grupo-letra">
            <span className="rotulo">Tamaño de letra</span>
            <div className="opciones" role="group" aria-label="Tamaño de letra">
              {TAMANOS_LETRA.map(({ valor, etiqueta }) => (
                <button
                  key={valor}
                  type="button"
                  data-tam={valor}
                  data-ai-id={`barra.letra-${valor}`}
                  className={tamanoLetra === valor ? 'activo' : ''}
                  aria-pressed={tamanoLetra === valor}
                  onClick={() => cambiarTamanoLetra(valor)}
                >
                  Aa<span className="nombre">{etiqueta}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div role="status" aria-live="polite">
        {avisoAbierto && (
          <p className="barra-aviso" data-ai-id="barra.aviso">
            {AVISOS[avisoAbierto]}
          </p>
        )}
      </div>
    </header>
  )
}

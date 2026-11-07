import { useEffect, useRef } from 'react'
import { PANTALLAS, useNavegacion } from '../../stores/navegacion'
import { TAMANOS_LETRA, usePreferencias } from '../../stores/preferencias'
import { useSesion } from '../../stores/sesion'
import { Boton } from '../../ui/componentes'
import { IndicadorConexion } from '../sincronizacion/EstadoSincronizacion'
import { AvisoVersionNueva, ReiniciarPractica } from './AccionesBarra'
import { Respaldo } from './Respaldo'
import estilos from './BarraSuperior.module.css'

/**
 * Barra superior fija de toda la experiencia (Design-System.md, sección 6).
 * Izquierda: Menú y Asistente. Derecha: selector de tamaño de letra.
 * Debajo, cuando aplica: el estado de conexión. El menú es un panel lateral que entra
 * desde la izquierda sobre la pantalla actual.
 */
export function BarraSuperior() {
  const tamanoLetra = usePreferencias((estado) => estado.tamanoLetra)
  const cambiarTamanoLetra = usePreferencias((estado) => estado.cambiarTamanoLetra)
  const { pantalla, menuAbierto, asistenteAbierto, irA, alternarMenu, alternarAsistente } = useNavegacion()
  const nombreProyecto = useSesion((estado) => estado.nombreProyecto)
  const esReal = useSesion((estado) => estado.esReal)
  const cerrarSesion = useSesion((estado) => estado.cerrarSesion)
  const panel = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!menuAbierto) return
    // El foco entra al panel (lectores de pantalla y teclado) y Escape lo cierra
    panel.current?.focus()
    const alPresionar = (evento: KeyboardEvent) => {
      if (evento.key === 'Escape') alternarMenu()
    }
    window.addEventListener('keydown', alPresionar)
    return () => window.removeEventListener('keydown', alPresionar)
  }, [menuAbierto, alternarMenu])

  return (
    <header className={estilos.barra} data-ai-id="barra">
      <div className={estilos.fila}>
        <div className={estilos.izquierda}>
          <Boton aiId="barra.menu" variante="discreto" presionado={menuAbierto} onClick={alternarMenu}>
            Menú
          </Boton>
          <Boton
            aiId="barra.asistente"
            variante="ia"
            presionado={asistenteAbierto}
            onClick={alternarAsistente}
          >
            Asistente
          </Boton>
        </div>

        <div className={estilos.derecha}>
          <div className={estilos.grupoLetra}>
            <span className={estilos.rotulo}>Tamaño de letra</span>
            <div className={estilos.opciones} role="group" aria-label="Tamaño de letra">
              {TAMANOS_LETRA.map(({ valor, etiqueta }) => (
                <button
                  key={valor}
                  type="button"
                  data-tam={valor}
                  data-ai-id={`barra.letra-${valor}`}
                  className={`${estilos.opcionLetra} ${tamanoLetra === valor ? estilos.activo : ''}`}
                  aria-pressed={tamanoLetra === valor}
                  onClick={() => cambiarTamanoLetra(valor)}
                >
                  Aa<span className={estilos.nombreLetra}>{etiqueta}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {menuAbierto && (
        <>
          {/* Tocar fuera del panel lo cierra, como en cualquier menú lateral */}
          <div className={estilos.fondoMenu} onClick={alternarMenu} aria-hidden="true" />
          <nav
            ref={panel}
            className={estilos.menu}
            data-ai-id="barra.menu-abierto"
            aria-label="Menú principal"
            tabIndex={-1}
          >
            <div className={estilos.cabeceraMenu}>
              <p className={estilos.negocio} data-ai-id="barra.negocio">
                {esReal ? `Negocio: ${nombreProyecto}` : `${nombreProyecto}: datos de práctica`}
              </p>
              <Boton aiId="barra.cerrar-menu" variante="discreto" onClick={alternarMenu}>
                Cerrar menú
              </Boton>
            </div>
            <div className={estilos.opcionesMenu}>
              {PANTALLAS.map(({ clave, nombre }) => (
                <Boton
                  key={clave}
                  aiId={`barra.ir-${clave}`}
                  variante={pantalla === clave ? 'primario' : 'secundario'}
                  presionado={pantalla === clave}
                  onClick={() => irA(clave)}
                >
                  {nombre}
                </Boton>
              ))}
              <Respaldo />
              {!esReal && <ReiniciarPractica />}
              <Boton aiId="barra.salir" variante="discreto" onClick={cerrarSesion}>
                Salir de este negocio
              </Boton>
            </div>
          </nav>
        </>
      )}
      <AvisoVersionNueva />
      <IndicadorConexion />
    </header>
  )
}

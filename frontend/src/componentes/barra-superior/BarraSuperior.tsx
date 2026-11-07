import { useNavegacion } from '../../stores/navegacion'
import { TAMANOS_LETRA, usePreferencias } from '../../stores/preferencias'
import { Boton } from '../../ui/componentes'
import { IndicadorConexion } from '../sincronizacion/EstadoSincronizacion'
import { AvisoVersionNueva } from './AccionesBarra'
import estilos from './BarraSuperior.module.css'

/**
 * Barra superior fija de toda la experiencia (Design-System.md, sección 6).
 * Izquierda: "Menú" (solo en pantalla angosta; en la ancha el menú lateral ya está a la
 * vista) y "Asistente", que abre o cierra la ventana flotante del Asistente sobre la pantalla
 * actual (su apartado completo está en el menú). Derecha: tamaño de letra.
 * Debajo, cuando aplica: el aviso de versión nueva y el estado de conexión.
 */
export function BarraSuperior() {
  const tamanoLetra = usePreferencias((estado) => estado.tamanoLetra)
  const cambiarTamanoLetra = usePreferencias((estado) => estado.cambiarTamanoLetra)
  const { pantalla, menuAbierto, asistenteFlotante, alternarMenu, alternarAsistenteFlotante } =
    useNavegacion()

  return (
    <header className={estilos.barra} data-ai-id="barra">
      <div className={estilos.fila}>
        <div className={estilos.izquierda}>
          <span className={estilos.soloAngosta}>
            <Boton aiId="barra.menu" variante="discreto" presionado={menuAbierto} onClick={alternarMenu}>
              Menú
            </Boton>
          </span>
          <Boton
            aiId="barra.asistente"
            variante="ia"
            presionado={pantalla === 'asistente' || asistenteFlotante}
            // En su apartado ya está a la vista; en cualquier otra pantalla abre o cierra la ventana
            onClick={() => pantalla !== 'asistente' && alternarAsistenteFlotante()}
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
      <AvisoVersionNueva />
      <IndicadorConexion />
    </header>
  )
}

import { registerSW } from 'virtual:pwa-register'
import { useActualizacion } from './stores/actualizacion'

/**
 * Registra el service worker. Cuando hay una versión nueva descargada no se
 * aplica sola: se avisa al operador, que decide cuándo, para no recargar la pantalla
 * en medio de una venta (D-18). Va aparte de la barra porque `virtual:pwa-register`
 * solo existe en el build de Vite, no en los tests.
 */
export function registrarActualizaciones(): void {
  const actualizar = registerSW({
    onNeedRefresh() {
      useActualizacion.setState({ hayVersionNueva: true, aplicar: () => void actualizar(true) })
    },
  })
}

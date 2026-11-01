import { useState } from 'react'
import { ErrorApi, SinConexion, pedir } from '../../api/cliente'
import { baseDe } from '../../sincronizacion/base-local'
import { useActualizacion } from '../../stores/actualizacion'
import { useSesion } from '../../stores/sesion'
import { Aviso, Boton } from '../../ui/componentes'
import estilos from './BarraSuperior.module.css'

/** Hay una versión nueva descargada: se aplica cuando el operador lo decide (D-18). */
export function AvisoVersionNueva() {
  const hayVersionNueva = useActualizacion((estado) => estado.hayVersionNueva)
  const aplicar = useActualizacion((estado) => estado.aplicar)
  if (!hayVersionNueva) return null
  return (
    <div className={estilos.avisoBarra} data-ai-id="barra.version-nueva">
      <Aviso tipo="info">Hay una versión nueva de Mi Puestito. Lo que ya registraste no se pierde.</Aviso>
      <Boton aiId="barra.actualizar" variante="secundario" onClick={aplicar}>
        Actualizar ahora
      </Boton>
    </div>
  )
}

/**
 * Vuelve a sembrar los datos de práctica con las fechas de hoy (D-19). Pide
 * confirmación en dos pasos porque borra lo practicado. Solo se muestra en demo, y
 * el backend rechaza el pedido con un token de negocio real.
 */
export function ReiniciarPractica() {
  const proyecto = useSesion((estado) => estado.proyecto)
  const [confirmando, setConfirmando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const reiniciar = async () => {
    if (!proyecto) return
    try {
      await pedir('POST', '/api/dashboard/demo/reiniciar')
      // Lo guardado en el dispositivo es de la práctica anterior: si queda, volvería a enviarse
      const base = baseDe(proyecto)
      await Promise.all([
        base.operaciones.clear(),
        base.ventasAbiertas.clear(),
        base.clientes.clear(),
        base.instantaneas.clear(),
      ])
      window.location.reload()
    } catch (fallo) {
      setError(
        fallo instanceof SinConexion
          ? 'Sin conexión: los datos de práctica se reinician cuando vuelva la red.'
          : fallo instanceof ErrorApi
            ? fallo.detalle
            : 'No se pudieron reiniciar los datos de práctica.',
      )
    }
  }

  if (!confirmando) {
    return (
      <Boton aiId="barra.reiniciar-practica" variante="discreto" onClick={() => setConfirmando(true)}>
        Reiniciar datos de práctica
      </Boton>
    )
  }
  return (
    <div className={estilos.confirmacion} data-ai-id="barra.confirmar-reinicio">
      <Aviso tipo={error ? 'error' : 'pendiente'}>
        {error ?? 'Se borra todo lo que practicaste y la demo vuelve al inicio con las fechas de hoy.'}
      </Aviso>
      <Boton aiId="barra.reiniciar-si" variante="peligro" onClick={() => void reiniciar()}>
        Sí, reiniciar
      </Boton>
      <Boton aiId="barra.reiniciar-no" variante="discreto" onClick={() => setConfirmando(false)}>
        No, dejarlo así
      </Boton>
    </div>
  )
}

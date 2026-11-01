import { useRef, useState } from 'react'
import { ErrorApi, SinConexion, enviarArchivo, recibirArchivo } from '../../api/cliente'
import { baseDe } from '../../sincronizacion/base-local'
import { useSincronizacion } from '../../sincronizacion/cola'
import { useSesion } from '../../stores/sesion'
import { Aviso, Boton } from '../../ui/componentes'
import estilos from './BarraSuperior.module.css'

function mensajeDe(fallo: unknown): string {
  if (fallo instanceof SinConexion) return 'No hay conexión con el programa. Revisa que siga abierto.'
  if (fallo instanceof ErrorApi) return fallo.detalle
  return 'No se pudo completar. Tus datos siguen como estaban.'
}

/**
 * Guardar y recuperar una copia de los datos del negocio (Fase 5, ADR-044). Recuperar pide
 * confirmación en dos pasos y no se ofrece con cambios sin enviar: se perderían.
 */
export function Respaldo() {
  const proyecto = useSesion((estado) => estado.proyecto)
  const pendientes = useSincronizacion((estado) => estado.pendientes)
  const selector = useRef<HTMLInputElement>(null)
  const [archivo, setArchivo] = useState<File | null>(null)
  const [trabajando, setTrabajando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [guardada, setGuardada] = useState(false)

  const guardar = async () => {
    setTrabajando(true)
    setError(null)
    setGuardada(false)
    try {
      const { datos, nombre } = await recibirArchivo('/api/respaldo/copia')
      const enlace = document.createElement('a')
      enlace.href = URL.createObjectURL(datos)
      enlace.download = nombre
      enlace.click()
      URL.revokeObjectURL(enlace.href)
      setGuardada(true)
    } catch (fallo) {
      setError(mensajeDe(fallo))
    } finally {
      setTrabajando(false)
    }
  }

  const recuperar = async () => {
    if (!archivo || !proyecto) return
    setTrabajando(true)
    setError(null)
    try {
      await enviarArchivo('/api/respaldo/restaurar', archivo)
      // Lo guardado en el dispositivo es de los datos anteriores
      const base = baseDe(proyecto)
      await Promise.all([
        base.ventasAbiertas.clear(),
        base.clientes.clear(),
        base.instantaneas.clear(),
        base.ordenesCompra.clear(),
        base.proveedores.clear(),
      ])
      window.location.reload()
    } catch (fallo) {
      setError(mensajeDe(fallo))
      setArchivo(null)
      setTrabajando(false)
    }
  }

  return (
    <div className={estilos.confirmacion} data-ai-id="barra.respaldo">
      {error && <Aviso tipo="error">{error}</Aviso>}
      {guardada && (
        <Aviso tipo="exito">
          Copia guardada en tus descargas. Tiene los datos de tu negocio: guárdala en un lugar seguro, como
          una memoria USB.
        </Aviso>
      )}
      <Boton
        aiId="barra.guardar-copia"
        variante="secundario"
        deshabilitado={trabajando}
        onClick={() => void guardar()}
      >
        Guardar una copia de mis datos
      </Boton>

      <input
        ref={selector}
        className={estilos.selectorArchivo}
        type="file"
        accept=".db"
        data-ai-id="barra.archivo-copia"
        aria-label="Elegir el archivo de la copia"
        onChange={(evento) => {
          setArchivo(evento.target.files?.[0] ?? null)
          evento.target.value = ''
        }}
      />
      {!archivo ? (
        <Boton
          aiId="barra.recuperar-copia"
          variante="discreto"
          deshabilitado={trabajando || pendientes > 0}
          onClick={() => selector.current?.click()}
        >
          Recuperar una copia
        </Boton>
      ) : (
        <>
          <Aviso tipo="pendiente">
            {`Todo lo que hay ahora se reemplaza por lo guardado en «${archivo.name}». Lo actual queda guardado aparte en esta computadora.`}
          </Aviso>
          <Boton
            aiId="barra.recuperar-si"
            variante="peligro"
            deshabilitado={trabajando}
            onClick={() => void recuperar()}
          >
            Sí, recuperar esta copia
          </Boton>
          <Boton
            aiId="barra.recuperar-no"
            variante="discreto"
            deshabilitado={trabajando}
            onClick={() => setArchivo(null)}
          >
            No, dejarlo así
          </Boton>
        </>
      )}
      {pendientes > 0 && <Aviso tipo="info">Hay cambios por enviar: recuperar una copia los perdería.</Aviso>}
    </div>
  )
}

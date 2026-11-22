import { useEffect, useRef, useState } from 'react'
import { Aviso, Boton, Nota } from '../../ui/componentes'
import estilos from './EscanearCodigo.module.css'
import { crearDetector, escanerDisponible, limpiarCodigo } from './escaner'

const CADA_MS = 250

/**
 * Botón «Escanear con la cámara» que abre la cámara trasera, lee el primer código de
 * barras y lo entrega (D-30). La cámara se apaga al leer, al cancelar o al salir de la
 * pantalla. Si el navegador no puede, el botón no aparece: el lector USB sigue sirviendo.
 */
export function EscanearCodigo({
  aiId,
  alLeer,
  texto = 'Escanear con la cámara',
}: {
  aiId: string
  alLeer: (codigo: string) => void
  texto?: string
}) {
  const [abierto, setAbierto] = useState(false)
  if (!escanerDisponible()) return null
  return abierto ? (
    <Camara
      aiId={aiId}
      alCerrar={() => setAbierto(false)}
      alLeer={(codigo) => {
        setAbierto(false)
        alLeer(codigo)
      }}
    />
  ) : (
    <Boton aiId={aiId} variante="secundario" onClick={() => setAbierto(true)}>
      {texto}
    </Boton>
  )
}

function Camara({
  aiId,
  alLeer,
  alCerrar,
}: {
  aiId: string
  alLeer: (c: string) => void
  alCerrar: () => void
}) {
  const video = useRef<HTMLVideoElement>(null)
  const [error, setError] = useState<string | null>(null)
  // La última función recibida, sin reiniciar la cámara si el padre se vuelve a dibujar
  const entregar = useRef(alLeer)
  entregar.current = alLeer

  useEffect(() => {
    let flujo: MediaStream | null = null
    let reloj: number | undefined
    let vigente = true

    const apagar = () => {
      if (reloj !== undefined) window.clearInterval(reloj)
      flujo?.getTracks().forEach((pista) => pista.stop())
    }

    void (async () => {
      try {
        const detector = await crearDetector()
        flujo = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: 'environment' } },
          audio: false,
        })
        if (!vigente || !video.current) return apagar()
        video.current.srcObject = flujo
        await video.current.play().catch(() => {})
        let buscando = false
        reloj = window.setInterval(() => {
          if (buscando || !video.current) return
          buscando = true
          detector
            .detect(video.current)
            .then((codigos) => {
              const leido = codigos.map((c) => limpiarCodigo(c.rawValue)).find(Boolean)
              if (leido && vigente) {
                vigente = false
                apagar()
                entregar.current(leido)
              }
            })
            .catch(() => {})
            .finally(() => {
              buscando = false
            })
        }, CADA_MS)
      } catch (fallo) {
        apagar()
        if (vigente) {
          setError(
            fallo instanceof DOMException && fallo.name === 'NotAllowedError'
              ? 'La app no tiene permiso para usar la cámara. Acéptalo en el aviso del navegador o escribe el código.'
              : 'No se pudo abrir la cámara. Escribe el código o usa el lector.',
          )
        }
      }
    })()

    return () => {
      vigente = false
      apagar()
    }
  }, [])

  return (
    <div className={estilos.camara} data-ai-id={`${aiId}-camara`}>
      {error ? (
        <Aviso tipo="error">{error}</Aviso>
      ) : (
        <>
          <video ref={video} className={estilos.video} muted playsInline aria-label="Imagen de la cámara" />
          <Nota>Apunta al código de barras y mantenlo quieto. La imagen no sale de este equipo.</Nota>
        </>
      )}
      <Boton aiId={`${aiId}-cancelar`} variante="discreto" onClick={alCerrar}>
        Cancelar
      </Boton>
    </div>
  )
}

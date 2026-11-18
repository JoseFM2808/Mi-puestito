import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { SinConexion, pedir } from '../../api/cliente'
import { aCentimos, aSoles, leerMontoEscrito, type CajaDelDiaCable } from '../../api/contrato'
import { baseDe } from '../../sincronizacion/base-local'
import { encolar, useSincronizacion } from '../../sincronizacion/cola'
import { useNavegacion } from '../../stores/navegacion'
import { useSesion } from '../../stores/sesion'
import { Aviso, Boton, Campo, Monto, Nota, Tarjeta } from '../../ui/componentes'
import estilos from './Dashboard.module.css'

/**
 * "En caja ahora" (D-24, ADR-051): la caja empieza con un saldo en efectivo y otro en Yape
 * (decisión del owner), suben con lo cobrado por cada medio y bajan con los gastos, incluido
 * lo pagado a proveedores. Sin red se muestra la última caja guardada y la apertura se encola.
 */

const NOMBRE_PARTE: Record<string, string> = { ventas: 'lo cobrado', gastos: 'los gastos' }

function diaPeruano(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima' }).format(new Date())
}

function useCaja() {
  const proyecto = useSesion((estado) => estado.proyecto)
  const pendientes = useSincronizacion((estado) => estado.pendientes)
  const [caja, setCaja] = useState<CajaDelDiaCable | null>(null)
  const [desdeDispositivo, setDesdeDispositivo] = useState(false)

  const cargar = useCallback(async () => {
    if (!proyecto) return
    const base = baseDe(proyecto)
    try {
      const cable = await pedir<CajaDelDiaCable>('GET', '/api/caja')
      setCaja(cable)
      setDesdeDispositivo(false)
      await base.cajas.put(cable)
    } catch (fallo) {
      if (!(fallo instanceof SinConexion)) return
      const guardada = await base.cajas.get(diaPeruano())
      if (guardada) setCaja(guardada)
      setDesdeDispositivo(true)
    }
  }, [proyecto])

  // Recarga al abrir y cada vez que la cola termina de enviar (una venta cobrada, un gasto)
  useEffect(() => {
    if (pendientes === 0) void cargar()
  }, [cargar, pendientes])

  /** Abre (o corrige) la caja de hoy: se ve al instante y viaja por la cola offline */
  const abrir = async (efectivo: number, yape: number) => {
    if (!proyecto) return
    const dia = diaPeruano()
    const actual = caja?.dia === dia ? caja : null
    const ingresos = actual?.ingresos ?? { efectivo: '0.00', yape_plin: '0.00' }
    const egresos = actual?.egresos ?? { efectivo: '0.00', yape_plin: '0.00' }
    const local: CajaDelDiaCable = {
      dia,
      abierta: true,
      inicial: { efectivo: aSoles(efectivo), yape_plin: aSoles(yape) },
      ingresos,
      egresos,
      en_caja: {
        efectivo: aSoles(efectivo + aCentimos(ingresos.efectivo) - aCentimos(egresos.efectivo)),
        yape_plin: aSoles(yape + aCentimos(ingresos.yape_plin) - aCentimos(egresos.yape_plin)),
      },
      no_disponibles: actual?.no_disponibles ?? [],
    }
    setCaja(local)
    await baseDe(proyecto).cajas.put(local)
    await encolar(proyecto, {
      metodo: 'POST',
      ruta: '/api/caja/apertura',
      descripcion: 'Abrir la caja de hoy',
      cuerpo: { uuid: crypto.randomUUID(), efectivo_inicial: aSoles(efectivo), yape_inicial: aSoles(yape) },
    })
  }

  return { caja, desdeDispositivo, abrir }
}

function FormularioApertura({
  inicial,
  alAbrir,
  alCancelar,
}: {
  inicial: CajaDelDiaCable['inicial'] | null
  alAbrir: (efectivo: number, yape: number) => void
  alCancelar?: () => void
}) {
  const [efectivo, setEfectivo] = useState(inicial?.efectivo ?? '')
  const [yape, setYape] = useState(inicial?.yape_plin ?? '')
  const [error, setError] = useState<string | null>(null)

  const abrir = (evento: FormEvent) => {
    evento.preventDefault()
    const enEfectivo = leerMontoEscrito(efectivo || '0')
    const enYape = leerMontoEscrito(yape || '0')
    if (enEfectivo === null || enYape === null)
      return setError('Escribe los montos en soles, por ejemplo 50 o 12.50')
    alAbrir(enEfectivo, enYape)
  }

  return (
    <form className={estilos.apertura} onSubmit={abrir} noValidate data-ai-id="dashboard.apertura">
      <Nota>¿Con cuánto empiezas hoy? Cuenta lo que hay en la gaveta y mira tu saldo de Yape.</Nota>
      {error && (
        <Aviso tipo="error" aiId="dashboard.apertura-error">
          {error}
        </Aviso>
      )}
      <div className={estilos.camposApertura}>
        <Campo
          id="apertura-efectivo"
          aiId="dashboard.apertura-efectivo"
          etiqueta="En efectivo (S/)"
          inputMode="decimal"
          placeholder="Por ejemplo: 50"
          valor={efectivo}
          alCambiar={setEfectivo}
        />
        <Campo
          id="apertura-yape"
          aiId="dashboard.apertura-yape"
          etiqueta="En Yape o Plin (S/)"
          inputMode="decimal"
          placeholder="Por ejemplo: 0"
          valor={yape}
          alCambiar={setYape}
        />
      </div>
      <div className={estilos.botonesApertura}>
        <Boton aiId="dashboard.abrir-caja" tipo="submit">
          {inicial ? 'Guardar' : 'Abrir caja'}
        </Boton>
        {alCancelar && (
          <Boton aiId="dashboard.apertura-cancelar" variante="discreto" onClick={alCancelar}>
            Cancelar
          </Boton>
        )}
      </div>
    </form>
  )
}

export function EnCaja() {
  const { caja, desdeDispositivo, abrir } = useCaja()
  const irA = useNavegacion((estado) => estado.irA)
  const [corrigiendo, setCorrigiendo] = useState(false)
  const deHoy = caja?.dia === diaPeruano() ? caja : null

  return (
    <Tarjeta aiId="dashboard.en-caja">
      <span className={estilos.etiqueta}>En caja ahora</span>
      {!deHoy?.abierta || corrigiendo ? (
        <FormularioApertura
          inicial={deHoy?.abierta ? deHoy.inicial : null}
          alAbrir={(efectivo, yape) => {
            void abrir(efectivo, yape)
            setCorrigiendo(false)
          }}
          alCancelar={corrigiendo ? () => setCorrigiendo(false) : undefined}
        />
      ) : (
        <>
          <div className={estilos.saldos}>
            <span className={estilos.saldo}>
              Efectivo
              <Monto
                centimos={aCentimos(deHoy.en_caja.efectivo)}
                tono={aCentimos(deHoy.en_caja.efectivo) < 0 ? 'deuda' : 'ingreso'}
                tamano="orden"
              />
            </span>
            <span className={estilos.saldo}>
              Yape o Plin
              <Monto
                centimos={aCentimos(deHoy.en_caja.yape_plin)}
                tono={aCentimos(deHoy.en_caja.yape_plin) < 0 ? 'deuda' : 'ingreso'}
                tamano="orden"
              />
            </span>
          </div>
          <Nota>
            {`Empezaste con ${[deHoy.inicial.efectivo, deHoy.inicial.yape_plin].map((m) => `S/ ${m}`).join(' y ')}. ` +
              `Salieron S/ ${aSoles(aCentimos(deHoy.egresos.efectivo) + aCentimos(deHoy.egresos.yape_plin))} en gastos.`}
          </Nota>
          {deHoy.no_disponibles.length > 0 && (
            <Aviso tipo="pendiente" aiId="dashboard.en-caja-incompleta">
              {`Ahora no se pudo sumar ${deHoy.no_disponibles.map((p) => NOMBRE_PARTE[p] ?? p).join(' ni ')}: el monto puede no estar completo.`}
            </Aviso>
          )}
          {desdeDispositivo && (
            <Nota>Es lo último guardado en esta tablet: se actualiza al volver la conexión.</Nota>
          )}
          <div className={estilos.botonesApertura}>
            <Boton aiId="dashboard.anotar-gasto" variante="secundario" onClick={() => irA('gastos')}>
              Anotar un gasto
            </Boton>
            <Boton
              aiId="dashboard.corregir-apertura"
              variante="discreto"
              onClick={() => setCorrigiendo(true)}
            >
              Corregir con cuánto empecé
            </Boton>
          </div>
        </>
      )}
    </Tarjeta>
  )
}

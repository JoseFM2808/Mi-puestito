import { useEffect, useState } from 'react'
import { SinConexion, pedir } from '../../api/cliente'
import type { KardexCable, KardexProductoCable, ProductoCable } from '../../api/contrato'
import { baseDe } from '../../sincronizacion/base-local'
import { useSincronizacion } from '../../sincronizacion/cola'
import { useSesion } from '../../stores/sesion'
import { Aviso, Boton, Nota, TituloSeccion } from '../../ui/componentes'
import { aMilesimas, formatearCantidad } from '../inventario/almacen'
import estilos from './Analisis.module.css'

/**
 * Kardex mensual del inventario (Modulo-Analisis): por cada producto, lo que había al empezar el
 * mes, lo que entró (compras), lo que salió (ventas, mermas), los conteos y lo que quedó. Sale del
 * mismo libro de movimientos que el stock (ADR-031): cuadra con Inventario. Se calcula en el
 * servidor; el último de cada mes queda en el dispositivo y sin red se muestra ese, diciendo de cuándo es.
 */

/** "2026-11" del mes peruano actual (desplazamiento −1 = el mes pasado) */
export function mesPeruano(desplazamiento = 0, ahora = new Date()): string {
  const [anio, mes] = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Lima',
    year: 'numeric',
    month: '2-digit',
  })
    .format(ahora)
    .split('-')
    .map(Number)
  const total = anio * 12 + (mes - 1) + desplazamiento
  return `${Math.floor(total / 12)}-${String((total % 12) + 1).padStart(2, '0')}`
}

const MESES = [
  { desplazamiento: 0, nombre: 'Este mes' },
  { desplazamiento: -1, nombre: 'El mes pasado' },
]

/** Un producto del kardex dicho en palabras, en su unidad: "Había 45 kg · entró 20 kg · …" */
export function lineaKardex(p: KardexProductoCable): string {
  const unidad = p.unidad as ProductoCable['unidad']
  const cant = (valor: string) => formatearCantidad(Math.abs(aMilesimas(valor)), unidad)
  const partes = [`Había ${cant(p.inicial)}`]
  if (aMilesimas(p.registrado) !== 0) partes.push(`lo registraste con ${cant(p.registrado)}`)
  if (aMilesimas(p.compras) !== 0) partes.push(`entró ${cant(p.compras)}`)
  if (aMilesimas(p.vendido) !== 0) partes.push(`vendiste ${cant(p.vendido)}`)
  if (aMilesimas(p.mermas) !== 0) partes.push(`se perdió ${cant(p.mermas)}`)
  const ajustes = aMilesimas(p.ajustes)
  if (ajustes !== 0) partes.push(`${ajustes > 0 ? 'sumaste' : 'restaste'} ${cant(p.ajustes)} al contar`)
  return partes.join(' · ')
}

export function Kardex() {
  const proyecto = useSesion((estado) => estado.proyecto)
  // Al terminar de enviar lo hecho sin red, se vuelve a calcular
  const alDia = useSincronizacion((estado) => estado.pendientes === 0)
  const [desplazamiento, setDesplazamiento] = useState(0)
  const [datos, setDatos] = useState<KardexCable | null>(null)
  const [guardadoEn, setGuardadoEn] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!proyecto) return
    let vigente = true
    const mes = mesPeruano(desplazamiento)
    const base = baseDe(proyecto)
    setDatos(null)
    setError(null)
    setGuardadoEn(null)
    pedir<KardexCable>('GET', `/api/analisis/kardex?mes=${mes}`)
      .then((respuesta) => {
        if (!vigente) return
        setDatos(respuesta)
        void base.kardex.put({ mes, datos: respuesta, guardadoEn: new Date().toISOString() }).catch(() => {})
      })
      .catch(async (fallo: unknown) => {
        const guardado =
          fallo instanceof SinConexion ? await base.kardex.get(mes).catch(() => undefined) : undefined
        if (!vigente) return
        if (guardado) {
          setDatos(guardado.datos)
          setGuardadoEn(guardado.guardadoEn)
          return
        }
        setError(
          fallo instanceof SinConexion
            ? 'El movimiento del inventario se ve cuando vuelva la conexión.'
            : 'No se pudo calcular el movimiento del inventario.',
        )
      })
    return () => {
      vigente = false
    }
  }, [proyecto, alDia, desplazamiento])

  return (
    <section className={estilos.kardex} data-ai-id="analisis.kardex">
      <TituloSeccion>Cómo se movió tu inventario</TituloSeccion>
      <div className={estilos.periodos}>
        {MESES.map((mes) => (
          <Boton
            key={mes.desplazamiento}
            aiId={`analisis.kardex-${mes.desplazamiento === 0 ? 'este-mes' : 'mes-pasado'}`}
            variante="secundario"
            presionado={desplazamiento === mes.desplazamiento}
            onClick={() => setDesplazamiento(mes.desplazamiento)}
          >
            {mes.nombre}
          </Boton>
        ))}
      </div>
      {error && <Aviso tipo="info">{error}</Aviso>}
      {guardadoEn && (
        <Aviso tipo="info" aiId="analisis.kardex-sin-conexion">
          {`Sin conexión: es el cálculo guardado el ${new Intl.DateTimeFormat('es-PE', {
            day: 'numeric',
            month: 'short',
            hour: 'numeric',
            minute: '2-digit',
            timeZone: 'America/Lima',
          }).format(new Date(guardadoEn))}.`}
        </Aviso>
      )}
      {!datos && !error && <Nota>Calculando…</Nota>}
      {datos?.no_disponibles.length ? (
        <Aviso tipo="pendiente">Ahora no se pudo leer el inventario.</Aviso>
      ) : datos?.productos.length === 0 ? (
        <Nota>No hubo movimientos de inventario en este mes.</Nota>
      ) : (
        <ul className={estilos.productos}>
          {datos?.productos.map((producto) => (
            <li key={producto.nombre} className={estilos.producto}>
              <span className={estilos.nombre}>
                {`${producto.nombre}: quedan ${formatearCantidad(aMilesimas(producto.final), producto.unidad as ProductoCable['unidad'])}`}
              </span>
              <span>{lineaKardex(producto)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

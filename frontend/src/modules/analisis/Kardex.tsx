import { useEffect, useState } from 'react'
import { SinConexion, pedir } from '../../api/cliente'
import type { KardexCable, KardexProductoCable, ProductoCable } from '../../api/contrato'
import { Aviso, Boton, Nota, TituloSeccion } from '../../ui/componentes'
import { aMilesimas, formatearCantidad } from '../inventario/almacen'
import estilos from './Analisis.module.css'

/**
 * Kardex mensual del inventario (Modulo-Analisis): por cada producto, lo que había al empezar el
 * mes, lo que entró (compras), lo que salió (ventas, mermas), los conteos y lo que quedó. Sale del
 * mismo libro de movimientos que el stock (ADR-031): cuadra con Inventario. Se calcula en el
 * servidor; sin red lo dice.
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
  const [desplazamiento, setDesplazamiento] = useState(0)
  const [datos, setDatos] = useState<KardexCable | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let vigente = true
    setDatos(null)
    setError(null)
    pedir<KardexCable>('GET', `/api/analisis/kardex?mes=${mesPeruano(desplazamiento)}`)
      .then((respuesta) => vigente && setDatos(respuesta))
      .catch((fallo: unknown) => {
        if (vigente)
          setError(
            fallo instanceof SinConexion
              ? 'El movimiento del inventario se ve cuando vuelva la conexión.'
              : 'No se pudo calcular el movimiento del inventario.',
          )
      })
    return () => {
      vigente = false
    }
  }, [desplazamiento])

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

import { useCallback, useEffect, useState } from 'react'
import { SinConexion, pedir } from '../../api/cliente'
import { aCentimos, formatearCentimos, type AnalisisCable, type PeriodoAnalisis } from '../../api/contrato'
import { baseDe } from '../../sincronizacion/base-local'
import { useSincronizacion } from '../../sincronizacion/cola'
import { useSesion } from '../../stores/sesion'
import { Aviso, Boton, Monto, Nota, Tarjeta, TituloPagina, TituloSeccion } from '../../ui/componentes'
import estilos from './Analisis.module.css'
import { Kardex } from './Kardex'

/**
 * ¿Cómo me va? (docs/03-modulos/Modulo-Analisis.md, Fase 7): ¿el puesto es rentable?
 * Vendido − pagado a proveedores − gastos del puesto = lo que dejó el negocio; menos los gastos
 * de la casa = lo que quedó libre. Todo lo calcula el servidor; sin red se muestra lo último
 * guardado en el dispositivo y se dice de cuándo es.
 */

const PERIODOS: { clave: PeriodoAnalisis; nombre: string }[] = [
  { clave: 'semana', nombre: 'Esta semana' },
  { clave: 'mes', nombre: 'Este mes' },
  { clave: 'mes_pasado', nombre: 'El mes pasado' },
]

const NOMBRE_PARTE: Record<string, string> = {
  ventas: 'las ventas',
  gastos: 'los gastos',
  fiados: 'los fiados',
  inventario: 'las ganancias por producto',
}

function fechaCorta(dia: string): string {
  return new Intl.DateTimeFormat('es-PE', {
    weekday: 'short',
    day: 'numeric',
    timeZone: 'America/Lima',
  }).format(new Date(`${dia}T12:00:00-05:00`))
}

/** La frase que resume el período, en palabras simples (Modulo-Analisis.md) */
export function resumenEnPalabras(datos: AnalisisCable): string {
  const libre = aCentimos(datos.libre)
  const negocio = aCentimos(datos.resultado_del_negocio)
  if (aCentimos(datos.vendido) === 0) return 'Todavía no hay ventas cobradas en este período.'
  if (libre >= 0)
    return `Vendiste más de lo que gastaste: te quedó ${formatearCentimos(libre)} libre después de los gastos de la casa.`
  if (negocio >= 0)
    return `El negocio dejó ${formatearCentimos(negocio)}, pero los gastos de la casa fueron más: faltan ${formatearCentimos(-libre)}.`
  return `Este período gastaste más de lo que vendiste: faltan ${formatearCentimos(-libre)}.`
}

function useAnalisis(periodo: PeriodoAnalisis) {
  const proyecto = useSesion((estado) => estado.proyecto)
  const pendientes = useSincronizacion((estado) => estado.pendientes)
  const [datos, setDatos] = useState<AnalisisCable | null>(null)
  const [guardadoEn, setGuardadoEn] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const cargar = useCallback(async () => {
    if (!proyecto) return
    const base = baseDe(proyecto)
    try {
      const cable = await pedir<AnalisisCable>('GET', `/api/analisis?periodo=${periodo}`)
      setDatos(cable)
      setGuardadoEn(null)
      setError(null)
      await base.analisis.put({ periodo, datos: cable, guardadoEn: new Date().toISOString() })
    } catch (fallo) {
      const guardado = await base.analisis.get(periodo)
      setDatos(guardado?.datos ?? null)
      setGuardadoEn(guardado?.guardadoEn ?? null)
      setError(
        fallo instanceof SinConexion
          ? guardado
            ? null
            : 'Sin conexión y todavía no hay un análisis guardado en este dispositivo.'
          : 'No se pudo leer el análisis.',
      )
    }
  }, [proyecto, periodo])

  useEffect(() => {
    if (pendientes === 0) void cargar()
  }, [cargar, pendientes])

  return { datos, guardadoEn, error }
}

export function Analisis() {
  const [periodo, setPeriodo] = useState<PeriodoAnalisis>('semana')
  const { datos, guardadoEn, error } = useAnalisis(periodo)
  const mayor = Math.max(
    1,
    ...(datos?.por_dia ?? []).flatMap((d) => [aCentimos(d.vendido), aCentimos(d.gastado)]),
  )

  return (
    <main className={estilos.pantalla} data-ai-id="analisis">
      <TituloPagina ayuda="Si el puesto deja ganancia: lo que vendiste, lo que pagaste y lo que te quedó libre.">
        ¿Cómo me va?
      </TituloPagina>

      <div className={estilos.periodos} role="group" aria-label="Período">
        {PERIODOS.map(({ clave, nombre }) => (
          <Boton
            key={clave}
            aiId={`analisis.periodo-${clave}`}
            variante="secundario"
            presionado={periodo === clave}
            onClick={() => setPeriodo(clave)}
          >
            {nombre}
          </Boton>
        ))}
      </div>

      {error && (
        <Aviso tipo="error" aiId="analisis.error">
          {error}
        </Aviso>
      )}
      {guardadoEn && (
        <Aviso tipo="info" aiId="analisis.sin-conexion">
          {`Sin conexión: es el análisis guardado el ${new Intl.DateTimeFormat('es-PE', {
            day: 'numeric',
            month: 'short',
            hour: 'numeric',
            minute: '2-digit',
            timeZone: 'America/Lima',
          }).format(new Date(guardadoEn))}.`}
        </Aviso>
      )}
      {!datos && !error && <Nota>Calculando…</Nota>}

      {datos && (
        <>
          {datos.no_disponibles.length > 0 && (
            <Aviso tipo="pendiente" aiId="analisis.incompleto">
              {`Ahora no se pudo sumar ${datos.no_disponibles.map((p) => NOMBRE_PARTE[p] ?? p).join(' ni ')}: las cifras pueden estar incompletas.`}
            </Aviso>
          )}

          <Tarjeta aiId="analisis.libre" className={estilos.libre}>
            <span className={estilos.rotulo}>Te quedó libre</span>
            <Monto
              centimos={aCentimos(datos.libre)}
              tamano="grande"
              tono={aCentimos(datos.libre) < 0 ? 'deuda' : 'ingreso'}
            />
            <p className={estilos.frase}>{resumenEnPalabras(datos)}</p>
          </Tarjeta>

          <div className={estilos.cuentas} data-ai-id="analisis.cuentas">
            <Tarjeta aiId="analisis.vendido">
              <span className={estilos.rotulo}>Vendiste</span>
              <Monto centimos={aCentimos(datos.vendido)} tamano="orden" tono="ingreso" />
              <Nota>{datos.ventas === 1 ? '1 venta cobrada' : `${datos.ventas} ventas cobradas`}</Nota>
            </Tarjeta>
            <Tarjeta aiId="analisis.proveedores">
              <span className={estilos.rotulo}>Pagaste a proveedores</span>
              <Monto centimos={aCentimos(datos.pagado_a_proveedores)} tamano="orden" tono="deuda" />
            </Tarjeta>
            <Tarjeta aiId="analisis.gastos-puesto">
              <span className={estilos.rotulo}>Gastos del puesto</span>
              <Monto centimos={aCentimos(datos.gastos_del_puesto)} tamano="orden" tono="deuda" />
            </Tarjeta>
            <Tarjeta aiId="analisis.gastos-casa">
              <span className={estilos.rotulo}>Gastos de la casa</span>
              <Monto centimos={aCentimos(datos.gastos_de_la_casa)} tamano="orden" tono="deuda" />
            </Tarjeta>
            <Tarjeta aiId="analisis.fiados">
              <span className={estilos.rotulo}>Te deben (fiados)</span>
              <Monto centimos={aCentimos(datos.fiados_por_cobrar)} tamano="orden" tono="pendiente" />
              <Nota>No cuenta como vendido hasta que te paguen.</Nota>
            </Tarjeta>
          </div>

          <TituloSeccion>Día por día</TituloSeccion>
          <ul className={estilos.dias} data-ai-id="analisis.por-dia">
            {datos.por_dia.map((dia) => (
              <li key={dia.dia} className={estilos.dia}>
                <span className={estilos.fecha}>{fechaCorta(dia.dia)}</span>
                <div className={estilos.barras} aria-hidden="true">
                  <span
                    className={estilos.barraVenta}
                    style={{ width: `${(aCentimos(dia.vendido) / mayor) * 100}%` }}
                  />
                  <span
                    className={estilos.barraGasto}
                    style={{ width: `${(aCentimos(dia.gastado) / mayor) * 100}%` }}
                  />
                </div>
                {/* Las barras acompañan; las cifras se dicen con palabras */}
                <span className={estilos.cifrasDia}>
                  {`Vendiste ${formatearCentimos(aCentimos(dia.vendido))} · salió ${formatearCentimos(aCentimos(dia.gastado))}`}
                </span>
              </li>
            ))}
          </ul>

          <TituloSeccion>Lo que más ganancia te deja</TituloSeccion>
          {datos.mejores_productos.length === 0 ? (
            <Nota>
              Aparece cuando vendes productos del inventario que tienen costo (el costo se toma de la última
              compra que llegó).
            </Nota>
          ) : (
            <ul className={estilos.productos} data-ai-id="analisis.mejores-productos">
              {datos.mejores_productos.map((producto) => (
                <li key={producto.nombre} className={estilos.producto}>
                  <span className={estilos.nombre}>{producto.nombre}</span>
                  <span>
                    {'Vendiste '}
                    <Monto centimos={aCentimos(producto.vendido)} />
                    {' · ganaste más o menos '}
                    <Monto
                      centimos={aCentimos(producto.ganancia_estimada)}
                      tono={aCentimos(producto.ganancia_estimada) < 0 ? 'deuda' : 'ingreso'}
                    />
                  </span>
                </li>
              ))}
            </ul>
          )}

          {datos.por_categoria.length > 0 && (
            <>
              <TituloSeccion>Por tipo de producto</TituloSeccion>
              <ul className={estilos.productos} data-ai-id="analisis.por-categoria">
                {datos.por_categoria.map((grupo) => (
                  <li key={grupo.categoria} className={estilos.producto}>
                    <span className={estilos.nombre}>{grupo.categoria}</span>
                    <span>
                      {'Vendiste '}
                      <Monto centimos={aCentimos(grupo.vendido)} />
                      {' · ganaste más o menos '}
                      <Monto
                        centimos={aCentimos(grupo.ganancia_estimada)}
                        tono={aCentimos(grupo.ganancia_estimada) < 0 ? 'deuda' : 'ingreso'}
                      />
                    </span>
                  </li>
                ))}
              </ul>
              <Nota>
                La categoría de cada producto se elige en Inventario, con «Cambiar datos del producto».
              </Nota>
            </>
          )}
        </>
      )}
      <Kardex />
    </main>
  )
}

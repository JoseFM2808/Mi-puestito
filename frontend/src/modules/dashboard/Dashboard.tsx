import { useCallback, useEffect, useState } from 'react'
import { SinConexion, pedir } from '../../api/cliente'
import { leerResumen, type ResumenCaja, type ResumenDashboardCable } from '../../api/contrato'
import { baseDe } from '../../sincronizacion/base-local'
import { useSincronizacion } from '../../sincronizacion/cola'
import { useNavegacion } from '../../stores/navegacion'
import { useSesion } from '../../stores/sesion'
import { Aviso, Boton, Monto, Nota, Tarjeta, TituloPagina, TituloSeccion } from '../../ui/componentes'
import estilos from './Dashboard.module.css'
import { estaAtrasado, formatearFechaLarga, formatearFechaRelativa } from './formato'

/**
 * Dashboard / Caja Diaria — pantalla principal (docs/03-modulos/Modulo-Dashboard.md).
 *
 * Las cifras vienen del backend, calculadas desde las ventas y pedidos
 * reales del proyecto (D-01). Sin conexión se muestra la última caja
 * conocida, guardada en la tablet, y se dice de qué hora es.
 */

interface Instantanea {
  resumen: ResumenCaja
  /** null = recién traída del servidor; si no, la hora en que se guardó */
  guardadaEn: string | null
}

const NOMBRE_SECCION: Record<string, string> = { ventas: 'Ventas', compras: 'Compras' }

function useResumen() {
  const proyecto = useSesion((estado) => estado.proyecto)
  const pendientes = useSincronizacion((estado) => estado.pendientes)
  const [datos, setDatos] = useState<Instantanea | null>(null)
  const [error, setError] = useState<string | null>(null)

  const cargar = useCallback(async () => {
    if (!proyecto) return
    const base = baseDe(proyecto)
    try {
      const cable = await pedir<ResumenDashboardCable>('GET', '/api/dashboard/resumen')
      setDatos({ resumen: leerResumen(cable), guardadaEn: null })
      setError(null)
      await base.instantaneas.put({ clave: 'resumen', resumen: cable, guardadaEn: new Date().toISOString() })
    } catch (fallo) {
      const guardada = await base.instantaneas.get('resumen')
      if (guardada) setDatos({ resumen: leerResumen(guardada.resumen), guardadaEn: guardada.guardadaEn })
      setError(
        fallo instanceof SinConexion
          ? null
          : fallo instanceof Error
            ? fallo.message
            : 'No se pudo leer la caja.',
      )
      if (!guardada && fallo instanceof SinConexion)
        setError('Sin conexión y todavía no hay una caja guardada en esta tablet.')
    }
  }, [proyecto])

  // Recarga al abrir y cada vez que la cola termina de enviar cambios
  useEffect(() => {
    if (pendientes === 0) void cargar()
  }, [cargar, pendientes])

  return { datos, error, cargar }
}

export function Dashboard() {
  const { datos, error, cargar } = useResumen()
  const irA = useNavegacion((estado) => estado.irA)
  const [avisoCompras, setAvisoCompras] = useState(false)

  return (
    <main className={estilos.pantalla} data-ai-id="dashboard">
      <div className={estilos.cabecera}>
        <TituloPagina>Caja de hoy</TituloPagina>
        <span className={estilos.fecha} data-ai-id="dashboard.fecha">
          {formatearFechaLarga(new Date())}
        </span>
      </div>

      {error && (
        <div className={estilos.filaAviso}>
          <Aviso tipo="error" aiId="dashboard.error">
            {error}
          </Aviso>
          <Boton aiId="dashboard.reintentar" variante="secundario" onClick={() => void cargar()}>
            Volver a intentar
          </Boton>
        </div>
      )}
      {datos?.guardadaEn && (
        <Aviso tipo="info" aiId="dashboard.sin-conexion">
          Sin conexión: estas cifras son de las{' '}
          {new Intl.DateTimeFormat('es-PE', {
            hour: 'numeric',
            minute: '2-digit',
            timeZone: 'America/Lima',
          }).format(new Date(datos.guardadaEn))}
          . Se actualizan solas al volver la red.
        </Aviso>
      )}
      {datos && datos.resumen.seccionesNoDisponibles.length > 0 && (
        <Aviso tipo="pendiente" aiId="dashboard.secciones-no-disponibles">
          No se pudieron leer las cifras de{' '}
          {datos.resumen.seccionesNoDisponibles.map((s) => NOMBRE_SECCION[s] ?? s).join(' y ')}. Lo demás está
          al día.
        </Aviso>
      )}

      {!datos && !error && <Nota>Leyendo la caja…</Nota>}
      {datos && <ContenidoCaja resumen={datos.resumen} />}

      <div className={estilos.acciones}>
        <Boton aiId="dashboard.registrar-venta" onClick={() => irA('ventas')}>
          Registrar venta
        </Boton>
        <Boton
          aiId="dashboard.venta-rapida"
          variante="secundario"
          onClick={() => irA('ventas', { ventaRapida: true })}
        >
          Venta rápida
        </Boton>
        <Boton aiId="dashboard.llego-pedido" variante="secundario" onClick={() => setAvisoCompras((v) => !v)}>
          Llegó un pedido
        </Boton>
      </div>
      {avisoCompras && (
        <Aviso tipo="info" aiId="dashboard.aviso-compras">
          El registro de pedidos que llegan se activa con el módulo Compras, que es el siguiente en
          construirse.
        </Aviso>
      )}
    </main>
  )
}

function ContenidoCaja({ resumen }: { resumen: ResumenCaja }) {
  const irA = useNavegacion((estado) => estado.irA)

  return (
    <>
      <section className={estilos.resumen}>
        <Tarjeta aiId="dashboard.ventas-hoy">
          <div className={estilos.etiqueta}>Vendiste hoy</div>
          <Monto centimos={resumen.ventasHoy} tamano="grande" tono="ingreso" />
          <Nota>
            {resumen.ventasCerradas} {resumen.ventasCerradas === 1 ? 'venta cobrada' : 'ventas cobradas'}
          </Nota>
        </Tarjeta>
        <Tarjeta aiId="dashboard.proyeccion-manana">
          <div className={estilos.etiqueta}>Mañana necesitas en caja</div>
          <Monto centimos={resumen.proyeccionManana} tamano="grande" tono="pendiente" />
          <Nota>{resumen.motivoProyeccion}</Nota>
        </Tarjeta>
      </section>

      <TituloSeccion>Órdenes abiertas ahora</TituloSeccion>
      {resumen.ordenesActivas.length === 0 ? (
        <Nota>No hay órdenes abiertas.</Nota>
      ) : (
        <section className={estilos.cuadricula} data-ai-id="dashboard.ordenes-activas">
          {resumen.ordenesActivas.map((orden) => (
            <button
              type="button"
              className={estilos.orden}
              key={orden.uuid}
              data-ai-id={`dashboard.orden-activa-${orden.uuid}`}
              onClick={() => irA('ventas')}
            >
              <span className={estilos.nombre}>{orden.nombre}</span>
              {orden.tipo === 'fiado' ? (
                <span className={estilos.estadoFiado}>
                  Fiado · ya debe <Monto centimos={orden.deudaCliente ?? 0} tono="deuda" />
                </span>
              ) : (
                <span className={estilos.estadoAbierta}>Sigue pidiendo</span>
              )}
              <Monto centimos={orden.monto} tamano="orden" />
            </button>
          ))}
        </section>
      )}

      <section className={`${estilos.resumen} ${estilos.resumenSecundario}`}>
        <button
          type="button"
          className={estilos.orden}
          data-ai-id="dashboard.fiados"
          onClick={() => irA('fiados')}
        >
          <span className={estilos.etiqueta}>Fiados por cobrar</span>
          <Monto centimos={resumen.fiadosPorCobrar} tamano="grande" tono="deuda" />
          <Nota>
            {resumen.clientesConFiado} {resumen.clientesConFiado === 1 ? 'cliente debe' : 'clientes deben'}
          </Nota>
        </button>
        <button
          type="button"
          className={estilos.orden}
          data-ai-id="dashboard.ventas-rapidas"
          onClick={() => irA('ventas')}
        >
          <span className={estilos.etiqueta}>Ventas rápidas por completar</span>
          <span className={estilos.conteo}>{resumen.ventasRapidasPendientes}</span>
          <Nota>Pendientes de registrar el detalle</Nota>
        </button>
      </section>

      <TituloSeccion>Pedidos por llegar</TituloSeccion>
      {resumen.pedidosPorLlegar.length === 0 ? (
        <Nota>No hay pedidos por llegar.</Nota>
      ) : (
        <section className={estilos.listaPedidos} data-ai-id="dashboard.pedidos-por-llegar">
          {resumen.pedidosPorLlegar.map((pedido) => {
            const atrasado = estaAtrasado(pedido.fechaEstimada)
            return (
              <Tarjeta key={pedido.id} aiId={`dashboard.pedido-${pedido.id}`} className={estilos.pedido}>
                <div>
                  <div className={estilos.nombre}>{pedido.proveedor}</div>
                  {/* El atraso se dice con palabras, el color solo acompaña */}
                  <div className={atrasado ? estilos.notaAtrasada : estilos.notaPedido}>
                    {atrasado ? 'Debió llegar ' : 'Llega '}
                    {formatearFechaRelativa(pedido.fechaEstimada)}
                  </div>
                </div>
                <Monto centimos={pedido.monto} tamano="orden" tono={atrasado ? 'deuda' : 'pendiente'} />
              </Tarjeta>
            )
          })}
        </section>
      )}
    </>
  )
}

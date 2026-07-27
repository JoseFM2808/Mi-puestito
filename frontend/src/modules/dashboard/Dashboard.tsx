import {
  fiadosPorCobrar,
  ordenesActivas,
  pedidosPorLlegar,
  resumenCaja,
  ventasRapidasPendientes,
} from './datos-ficticios'
import {
  estaAtrasado,
  formatearFechaLarga,
  formatearFechaRelativa,
  formatearMonto,
} from './formato'
import './Dashboard.css'

/**
 * Dashboard / Caja Diaria — pantalla principal (docs/03-modulos/Modulo-Dashboard.md).
 * Demo 1: muestra datos ficticios; los botones de acción aún no navegan.
 */
export function Dashboard() {
  return (
    <main className="pantalla" data-ai-id="dashboard">
      <div className="cabecera">
        <h1 className="titulo">Caja de hoy</h1>
        <span className="fecha" data-ai-id="dashboard.fecha">
          {formatearFechaLarga(new Date())}
        </span>
      </div>

      <section className="resumen">
        <div className="card" data-ai-id="dashboard.ventas-hoy">
          <div className="etiqueta">Vendiste hoy</div>
          <div className="monto monto-ingreso">{formatearMonto(resumenCaja.ventasHoy)}</div>
          <div className="nota">{resumenCaja.ventasCerradas} ventas cerradas</div>
        </div>
        <div className="card" data-ai-id="dashboard.proyeccion-manana">
          <div className="etiqueta">Mañana necesitas en caja</div>
          <div className="monto monto-pendiente">
            {formatearMonto(resumenCaja.proyeccionManana)}
          </div>
          <div className="nota">{resumenCaja.motivoProyeccion}</div>
        </div>
      </section>

      <h2 className="seccion-titulo">Órdenes abiertas ahora</h2>
      <section className="cuadricula-3" data-ai-id="dashboard.ordenes-activas">
        {ordenesActivas.map((orden) => (
          <button
            type="button"
            className="card orden"
            key={orden.id}
            data-ai-id={`dashboard.orden-activa-${orden.id}`}
          >
            <span className="cliente">{orden.nombre}</span>
            {orden.tipo === 'fiado' ? (
              <span className="estado estado-fiado">
                Fiado · debe {formatearMonto(orden.deudaCliente ?? 0)}
              </span>
            ) : (
              <span className="estado estado-abierta">Sigue pidiendo</span>
            )}
            <span className="monto-orden">{formatearMonto(orden.monto)}</span>
          </button>
        ))}
      </section>

      <section className="resumen resumen-secundario">
        <div className="card" data-ai-id="dashboard.fiados">
          <div className="etiqueta">Fiados por cobrar</div>
          <div className="monto monto-deuda">{formatearMonto(fiadosPorCobrar.total)}</div>
          <div className="nota">{fiadosPorCobrar.cantidadClientes} clientes deben</div>
        </div>
        <div className="card" data-ai-id="dashboard.ventas-rapidas">
          <div className="etiqueta">Ventas rápidas por completar</div>
          <div className="monto monto-pendiente">{ventasRapidasPendientes.cantidad}</div>
          <div className="nota">Pendientes de registrar el detalle</div>
        </div>
      </section>

      <h2 className="seccion-titulo">Pedidos por llegar</h2>
      <section className="lista-pedidos" data-ai-id="dashboard.pedidos-por-llegar">
        {pedidosPorLlegar.map((pedido) => {
          const atrasado = estaAtrasado(pedido.fechaEstimada)
          return (
            <div
              className="card pedido"
              key={pedido.id}
              data-ai-id={`dashboard.pedido-${pedido.id}`}
            >
              <div>
                <div className="cliente">{pedido.proveedor}</div>
                {/* El atraso se dice con palabras, el color solo acompaña */}
                <div className={atrasado ? 'nota nota-atrasada' : 'nota'}>
                  {atrasado ? 'Debió llegar ' : 'Llega '}
                  {formatearFechaRelativa(pedido.fechaEstimada)}
                </div>
              </div>
              <div className={`monto-orden ${atrasado ? 'monto-deuda' : 'monto-pendiente'}`}>
                {formatearMonto(pedido.monto)}
              </div>
            </div>
          )
        })}
      </section>

      <div className="acciones">
        <button type="button" className="btn btn-primario" data-ai-id="dashboard.registrar-venta">
          Registrar venta
        </button>
        <button type="button" className="btn btn-secundario" data-ai-id="dashboard.venta-rapida">
          Venta rápida
        </button>
        <button type="button" className="btn btn-secundario" data-ai-id="dashboard.llego-pedido">
          Llegó un pedido
        </button>
      </div>
    </main>
  )
}

import { useEffect, useState } from 'react'
import { aCentimos, formatearCentimos, type OrdenCompraCable } from '../../api/contrato'
import { OperacionesRechazadas } from '../../componentes/sincronizacion/EstadoSincronizacion'
import { useSesion } from '../../stores/sesion'
import { Aviso, Boton, Monto, Nota, Tarjeta, TituloPagina, TituloSeccion } from '../../ui/componentes'
import { estaAtrasado, formatearFechaRelativa } from '../dashboard/formato'
import { useCompras } from './almacen'
import estilos from './Compras.module.css'
import { ChecklistRecepcion, NuevoPedido } from './formularios'

/**
 * Compras: pedidos a proveedores, de la orden a la recepción (docs/03-modulos/
 * Modulo-Compras.md). Funciona sin internet, igual que Ventas: todo se guarda en
 * el dispositivo y se envía al volver la red.
 */

type Vista = { tipo: 'lista' } | { tipo: 'nuevo' } | { tipo: 'recepcion'; orden: string }

function fechaDe(texto: string): Date {
  return new Date(`${texto}T12:00:00-05:00`)
}

function LineaLlegada({ orden }: { orden: OrdenCompraCable }) {
  if (!orden.fecha_estimada_llegada) return <Nota>Sin fecha de llegada</Nota>
  const fecha = fechaDe(orden.fecha_estimada_llegada)
  const atrasado = estaAtrasado(fecha)
  return (
    <div className={atrasado ? estilos.notaAtrasada : estilos.nota}>
      {atrasado ? 'Debió llegar ' : 'Llega '}
      {formatearFechaRelativa(fecha)}
    </div>
  )
}

function Productos({ orden }: { orden: OrdenCompraCable }) {
  return (
    <ul className={estilos.productos}>
      {orden.items.map((item) => (
        <li key={item.uuid}>
          {item.nombre_producto}
          {item.cantidad ? ` · ${item.cantidad}` : ''}
          {item.estado_recepcion === 'recibido' && ' · llegó'}
          {item.estado_recepcion === 'no_recibido' && ' · no llegó'}
          {item.estado_recepcion === 'cambiado' && ` · cambió por ${item.producto_sustituto}`}
        </li>
      ))}
    </ul>
  )
}

export function Compras() {
  const proyecto = useSesion((estado) => estado.proyecto)
  const ordenes = useCompras((estado) => estado.ordenes)
  const avisos = useCompras((estado) => estado.avisos)
  const desdeDispositivo = useCompras((estado) => estado.desdeDispositivo)
  const iniciar = useCompras((estado) => estado.iniciar)
  const cargar = useCompras((estado) => estado.cargar)
  const avanzar = useCompras((estado) => estado.avanzar)
  const cerrar = useCompras((estado) => estado.cerrar)
  const descartarAviso = useCompras((estado) => estado.descartarAviso)
  const [vista, setVista] = useState<Vista>({ tipo: 'lista' })

  useEffect(() => {
    if (proyecto) void iniciar(proyecto)
  }, [proyecto, iniciar])

  const alVolver = () => setVista({ tipo: 'lista' })

  if (vista.tipo === 'nuevo') return <NuevoPedido alTerminar={alVolver} />
  if (vista.tipo === 'recepcion') {
    const orden = ordenes.find((o) => o.uuid === vista.orden)
    if (orden) return <ChecklistRecepcion orden={orden} alTerminar={alVolver} />
  }

  const porFecha = (a: OrdenCompraCable, b: OrdenCompraCable) =>
    (a.fecha_estimada_llegada ?? '9999').localeCompare(b.fecha_estimada_llegada ?? '9999')
  const borradores = ordenes.filter((o) => o.estado === 'borrador')
  const porLlegar = ordenes.filter((o) => o.estado === 'pendiente' || o.estado === 'en_camino').sort(porFecha)
  const recibidas = ordenes.filter((o) => o.estado === 'recibida')

  return (
    <main className={estilos.pantalla} data-ai-id="compras">
      <TituloPagina>Compras</TituloPagina>
      <OperacionesRechazadas alDescartar={() => void cargar()} />
      {desdeDispositivo && (
        <Aviso tipo="info" aiId="compras.sin-conexion">
          Mostrando lo guardado en este dispositivo. Lo que registres se envía cuando vuelva la red.
        </Aviso>
      )}
      {avisos.map((aviso, indice) => (
        <div key={`${indice}-${aviso}`} className={estilos.fila}>
          <Aviso tipo="pendiente">{aviso}</Aviso>
          <Boton aiId={`compras.aviso-${indice}`} variante="discreto" onClick={() => descartarAviso(indice)}>
            Entendido
          </Boton>
        </div>
      ))}

      <Boton aiId="compras.nuevo-pedido" onClick={() => setVista({ tipo: 'nuevo' })}>
        Nuevo pedido
      </Boton>

      <TituloSeccion>Pedidos por llegar</TituloSeccion>
      {porLlegar.length === 0 ? (
        <Nota>No hay pedidos por llegar.</Nota>
      ) : (
        porLlegar.map((orden) => (
          <Tarjeta key={orden.uuid} aiId={`compras.pedido-${orden.uuid}`} className={estilos.tarjeta}>
            <div className={estilos.fila}>
              <div>
                <div className={estilos.nombre}>{orden.proveedor}</div>
                <LineaLlegada orden={orden} />
                <Nota>{orden.estado === 'en_camino' ? 'En camino' : 'Pedido hecho'}</Nota>
              </div>
              <Monto centimos={aCentimos(orden.monto_total)} tamano="orden" tono="pendiente" />
            </div>
            <Productos orden={orden} />
            {orden.monto_real !== null && (
              <Nota>Ya recibido: {formatearCentimos(aCentimos(orden.monto_real))}. Falta lo demás.</Nota>
            )}
            <div className={estilos.acciones}>
              <Boton
                aiId={`compras.llego-${orden.uuid}`}
                onClick={() => setVista({ tipo: 'recepcion', orden: orden.uuid })}
              >
                Llegó este pedido
              </Boton>
              {orden.estado === 'pendiente' && (
                <Boton
                  aiId={`compras.en-camino-${orden.uuid}`}
                  variante="secundario"
                  onClick={() => void avanzar(orden.uuid, 'en_camino')}
                >
                  Ya viene en camino
                </Boton>
              )}
            </div>
          </Tarjeta>
        ))
      )}

      {recibidas.length > 0 && <TituloSeccion>Llegaron: falta pagar</TituloSeccion>}
      {recibidas.map((orden) => (
        <Tarjeta key={orden.uuid} aiId={`compras.recibido-${orden.uuid}`} className={estilos.tarjeta}>
          <div className={estilos.fila}>
            <div className={estilos.nombre}>{orden.proveedor}</div>
            <Monto centimos={aCentimos(orden.monto_real ?? orden.monto_total)} tamano="orden" tono="deuda" />
          </div>
          {orden.monto_real !== orden.monto_total && (
            <Nota>Se había pedido por {formatearCentimos(aCentimos(orden.monto_total))}.</Nota>
          )}
          <Productos orden={orden} />
          <Boton
            aiId={`compras.cerrar-${orden.uuid}`}
            variante="secundario"
            onClick={() => void cerrar(orden.uuid)}
          >
            Ya le pagué: cerrar pedido
          </Boton>
        </Tarjeta>
      ))}

      {borradores.length > 0 && <TituloSeccion>Borradores</TituloSeccion>}
      {borradores.map((orden) => (
        <Tarjeta key={orden.uuid} aiId={`compras.borrador-${orden.uuid}`} className={estilos.tarjeta}>
          <div className={estilos.fila}>
            <div className={estilos.nombre}>{orden.proveedor}</div>
            <Monto centimos={aCentimos(orden.monto_total)} tamano="orden" tono="neutro" />
          </div>
          <Productos orden={orden} />
          <Boton
            aiId={`compras.confirmar-${orden.uuid}`}
            variante="secundario"
            onClick={() => void avanzar(orden.uuid, 'pendiente')}
          >
            Confirmar pedido
          </Boton>
        </Tarjeta>
      ))}
    </main>
  )
}

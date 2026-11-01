import { useState } from 'react'
import { leerVenta, type VentaCable } from '../../api/contrato'
import { Boton, Monto, Nota, Tarjeta } from '../../ui/componentes'
import { useVentas } from './almacen'
import { FormularioProducto, SelectorCliente } from './formularios'
import estilos from './Ventas.module.css'

export function nombreVisible(venta: VentaCable, posicion: number): string {
  return venta.cliente_nombre ?? venta.nombre_orden ?? `Orden ${posicion}`
}

/** Una orden abierta: sus productos, su total y cómo cerrarla. */
export function DetalleOrden({ cable, posicion }: { cable: VentaCable; posicion: number }) {
  const venta = leerVenta(cable)
  const { agregarItem, quitarItem, cobrar, fiar, anular } = useVentas()
  const [eligiendoCliente, setEligiendoCliente] = useState(false)
  const nombre = nombreVisible(cable, posicion)
  const esFiado = venta.tipo === 'fiado'
  const vacia = venta.items.length === 0
  const id = `ventas.orden-${venta.uuid}`

  return (
    <section className={estilos.detalle} data-ai-id={id} aria-label={`Orden ${nombre}`}>
      <Tarjeta className={estilos.columna}>
        <div className={estilos.encabezadoOrden}>
          <h2 className={estilos.nombreOrden}>{nombre}</h2>
          <span className={estilos.tipoOrden}>
            {esFiado ? <span className={estilos.estadoFiado}>Fiado: se cobra después</span> : 'Orden abierta'}
          </span>
        </div>

        {vacia ? (
          <Nota>Todavía no tiene productos. Agrégalos a la derecha.</Nota>
        ) : (
          <ul className={estilos.items}>
            {venta.items.map((item) => (
              <li key={item.uuid} className={estilos.item} data-ai-id={`${id}.item-${item.uuid}`}>
                <span className={estilos.itemTexto}>
                  <span className={estilos.itemNombre}>{item.nombreProducto}</span>
                  {item.cantidad && <span className={estilos.itemCantidad}>{item.cantidad}</span>}
                </span>
                <Monto centimos={item.monto} />
                <Boton
                  aiId={`${id}.quitar-${item.uuid}`}
                  variante="discreto"
                  onClick={() => void quitarItem(venta.uuid, item.uuid)}
                >
                  Quitar
                </Boton>
              </li>
            ))}
          </ul>
        )}

        <div className={estilos.total} data-ai-id={`${id}.total`}>
          <span className={estilos.totalEtiqueta}>Total</span>
          <Monto centimos={venta.montoTotal} tamano="grande" tono={esFiado ? 'deuda' : 'pendiente'} />
        </div>
        {esFiado && venta.deudaCliente !== null && venta.deudaCliente > 0 && (
          <Nota>
            {venta.clienteNombre} ya debía <Monto centimos={venta.deudaCliente} tono="deuda" /> antes de esta
            orden.
          </Nota>
        )}
      </Tarjeta>

      <div className={estilos.columna}>
        <Tarjeta>
          <FormularioProducto
            prefijo={`ventas-orden-${venta.uuid}`}
            alAgregar={(item) => void agregarItem(venta.uuid, item)}
          />
        </Tarjeta>

        {eligiendoCliente ? (
          <SelectorCliente
            alElegir={(cliente) => {
              setEligiendoCliente(false)
              void fiar(venta.uuid, cliente)
            }}
            alCancelar={() => setEligiendoCliente(false)}
          />
        ) : (
          <Tarjeta className={estilos.cobro}>
            <Boton
              aiId={`${id}.cobrar-efectivo`}
              anchoCompleto
              deshabilitado={vacia}
              onClick={() => void cobrar(venta.uuid, 'efectivo')}
            >
              Cobrar en efectivo
            </Boton>
            <Boton
              aiId={`${id}.cobrar-yape`}
              variante="secundario"
              anchoCompleto
              deshabilitado={vacia}
              onClick={() => void cobrar(venta.uuid, 'yape_plin')}
            >
              Cobrar con Yape o Plin
            </Boton>
            <Boton
              aiId={`${id}.fiar`}
              variante="secundario"
              anchoCompleto
              deshabilitado={vacia}
              onClick={() => (esFiado ? void fiar(venta.uuid) : setEligiendoCliente(true))}
            >
              {esFiado ? `Fiar a ${venta.clienteNombre ?? 'este cliente'}` : 'Fiar a un cliente'}
            </Boton>
            {vacia && (
              <Boton
                aiId={`${id}.anular`}
                variante="peligro"
                anchoCompleto
                onClick={() => void anular(venta.uuid)}
              >
                Anular esta orden
              </Boton>
            )}
          </Tarjeta>
        )}
      </div>
    </section>
  )
}

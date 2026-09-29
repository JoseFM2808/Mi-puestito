import { useEffect, useState } from 'react'
import { formatearCentimos, leerVenta } from '../../api/contrato'
import { Boton, Monto, Nota, Tarjeta, TituloSeccion } from '../../ui/componentes'
import { useVentas } from './almacen'
import { FormularioProducto } from './formularios'
import estilos from './Ventas.module.css'

/**
 * Ventas rápidas por completar: se cobraron solo con el monto y ahora, con
 * calma, se registra qué se vendió. El detalle debe sumar lo cobrado.
 */
export function VentasRapidas() {
  const rapidas = useVentas((estado) => estado.rapidas)
  const cargarRapidas = useVentas((estado) => estado.cargarRapidas)
  const agregarItem = useVentas((estado) => estado.agregarItem)
  const quitarItem = useVentas((estado) => estado.quitarItem)
  const formalizar = useVentas((estado) => estado.formalizar)
  const [abierta, setAbierta] = useState<string | null>(null)

  useEffect(() => {
    void cargarRapidas()
  }, [cargarRapidas])

  if (rapidas.length === 0) return null

  return (
    <section data-ai-id="ventas.rapidas" aria-label="Ventas rápidas por completar">
      <TituloSeccion>Ventas rápidas por completar</TituloSeccion>
      <div className={estilos.avisos}>
        {rapidas.map((cable) => {
          const venta = leerVenta(cable)
          const detalle = venta.items.reduce((suma, item) => suma + item.monto, 0)
          const falta = venta.montoTotal - detalle
          const id = `ventas.rapida-${venta.uuid}`
          const hora = new Intl.DateTimeFormat('es-PE', {
            hour: 'numeric',
            minute: '2-digit',
            timeZone: 'America/Lima',
          }).format(new Date(venta.abiertaEn))
          return (
            <Tarjeta key={venta.uuid} aiId={id} className={estilos.columna}>
              <div className={estilos.encabezadoOrden}>
                <span className={estilos.nombreOrden}>
                  <Monto centimos={venta.montoTotal} tamano="orden" tono="ingreso" /> a las {hora}
                </span>
                {abierta !== venta.uuid && (
                  <Boton
                    aiId={`${id}.completar`}
                    variante="secundario"
                    onClick={() => setAbierta(venta.uuid)}
                  >
                    Completar el detalle
                  </Boton>
                )}
              </div>

              {abierta === venta.uuid && (
                <>
                  <ul className={estilos.items}>
                    {venta.items.map((item) => (
                      <li key={item.uuid} className={estilos.item}>
                        <span className={estilos.itemTexto}>
                          <span className={estilos.itemNombre}>{item.nombreProducto}</span>
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
                  <FormularioProducto
                    prefijo={`ventas-rapida-${venta.uuid}`}
                    alAgregar={(item) => void agregarItem(venta.uuid, item)}
                  />
                  {/* Se dice con palabras cuánto falta, no solo con color */}
                  <Nota>
                    {falta === 0
                      ? 'El detalle ya suma lo cobrado.'
                      : falta > 0
                        ? `Falta detallar ${formatearCentimos(falta)}.`
                        : `El detalle pasa lo cobrado por ${formatearCentimos(-falta)}.`}
                  </Nota>
                  <Boton
                    aiId={`${id}.guardar`}
                    deshabilitado={falta !== 0 || venta.items.length === 0}
                    onClick={() => {
                      setAbierta(null)
                      void formalizar(venta.uuid)
                    }}
                  >
                    Guardar el detalle
                  </Boton>
                </>
              )}
            </Tarjeta>
          )
        })}
      </div>
    </section>
  )
}

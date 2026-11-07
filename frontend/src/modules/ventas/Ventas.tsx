import { useEffect, useState } from 'react'
import { aCentimos, formatearCentimos } from '../../api/contrato'
import { OperacionesRechazadas } from '../../componentes/sincronizacion/EstadoSincronizacion'
import { useNavegacion } from '../../stores/navegacion'
import { useSesion } from '../../stores/sesion'
import { Aviso, Boton, Nota, TituloPagina } from '../../ui/componentes'
import { useVentas } from './almacen'
import { DetalleOrden, nombreVisible } from './DetalleOrden'
import { FormularioNuevaOrden, FormularioVentaRapida, SelectorCliente } from './formularios'
import estilos from './Ventas.module.css'
import { VentasRapidas } from './VentasRapidas'

/**
 * Ventas (docs/03-modulos/Modulo-Ventas.md): panel de órdenes activas en
 * paralelo, fiado y venta rápida. Funciona sin conexión (ver almacen.ts).
 */

type Formulario = 'ninguno' | 'orden' | 'rapida' | 'fiado'

export function Ventas() {
  const proyecto = useSesion((estado) => estado.proyecto)
  const {
    abiertas,
    seleccionada,
    avisos,
    desdeDispositivo,
    iniciar,
    cargar,
    seleccionar,
    abrirOrden,
    descartarAviso,
  } = useVentas()
  const abrirVentaRapida = useNavegacion((estado) => estado.abrirVentaRapida)
  const ventaRapidaAtendida = useNavegacion((estado) => estado.ventaRapidaAtendida)
  const [formulario, setFormulario] = useState<Formulario>('ninguno')

  useEffect(() => {
    if (proyecto) void iniciar(proyecto)
  }, [proyecto, iniciar])

  // "Venta rápida" desde la Caja de hoy abre directo el formulario
  useEffect(() => {
    if (abrirVentaRapida) {
      setFormulario('rapida')
      ventaRapidaAtendida()
    }
  }, [abrirVentaRapida, ventaRapidaAtendida])

  const actual = abiertas.find((venta) => venta.uuid === seleccionada)
  const cerrar = () => setFormulario('ninguno')

  return (
    <main className={estilos.pantalla} data-ai-id="ventas">
      <div className={estilos.cabecera}>
        <TituloPagina ayuda="Cada mesa o cliente es una orden. Agrega lo que lleva y, al terminar, cobra o déjalo fiado.">
          Ventas
        </TituloPagina>
        <div className={estilos.accionesCabecera}>
          <Boton aiId="ventas.nueva" onClick={() => setFormulario('orden')}>
            Nueva orden
          </Boton>
          <Boton aiId="ventas.nuevo-fiado" variante="secundario" onClick={() => setFormulario('fiado')}>
            Nuevo fiado
          </Boton>
          <Boton aiId="ventas.rapida" variante="secundario" onClick={() => setFormulario('rapida')}>
            Venta rápida
          </Boton>
        </div>
      </div>

      <OperacionesRechazadas alDescartar={() => void cargar()} />
      {avisos.length > 0 && (
        <div className={estilos.avisos} data-ai-id="ventas.avisos">
          {avisos.map((aviso, indice) => (
            <div key={`${indice}-${aviso}`} className={estilos.avisoConBoton}>
              <Aviso tipo="pendiente">{aviso}</Aviso>
              <Boton
                aiId={`ventas.aviso-${indice}.entendido`}
                variante="discreto"
                onClick={() => descartarAviso(indice)}
              >
                Entendido
              </Boton>
            </div>
          ))}
        </div>
      )}
      {desdeDispositivo && (
        <Aviso tipo="info" aiId="ventas.sin-conexion">
          Mostrando lo guardado en esta tablet. Puedes seguir vendiendo: se envía al volver la conexión.
        </Aviso>
      )}

      {formulario === 'orden' && <FormularioNuevaOrden alTerminar={cerrar} />}
      {formulario === 'rapida' && <FormularioVentaRapida alTerminar={cerrar} />}
      {formulario === 'fiado' && (
        <SelectorCliente
          alElegir={(cliente) => {
            void abrirOrden({ cliente })
            cerrar()
          }}
          alCancelar={cerrar}
        />
      )}

      {abiertas.length === 0 ? (
        <div className={estilos.vacio}>
          <Nota>No hay órdenes abiertas. Toca «Nueva orden» para empezar a vender.</Nota>
        </div>
      ) : (
        <>
          <div
            className={estilos.pestanas}
            role="tablist"
            aria-label="Órdenes abiertas"
            data-ai-id="ventas.ordenes"
          >
            {abiertas.map((venta, indice) => {
              const activa = venta.uuid === seleccionada
              return (
                <button
                  key={venta.uuid}
                  type="button"
                  role="tab"
                  aria-selected={activa}
                  className={`${estilos.pestana} ${activa ? estilos.pestanaActiva : ''}`}
                  data-ai-id={`ventas.pestana-${venta.uuid}`}
                  onClick={() => seleccionar(venta.uuid)}
                >
                  <span className={estilos.pestanaNombre}>{nombreVisible(venta, indice + 1)}</span>
                  <span className={estilos.pestanaDetalle}>
                    {venta.tipo === 'fiado' ? <span className={estilos.estadoFiado}>Fiado · </span> : null}
                    {venta.items.length} {venta.items.length === 1 ? 'producto' : 'productos'} ·{' '}
                    {formatearCentimos(aCentimos(venta.monto_total))}
                  </span>
                </button>
              )
            })}
          </div>
          {actual && (
            <DetalleOrden key={actual.uuid} cable={actual} posicion={abiertas.indexOf(actual) + 1} />
          )}
        </>
      )}

      <VentasRapidas />
    </main>
  )
}

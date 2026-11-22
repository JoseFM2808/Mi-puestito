import { useEffect, useState, type FormEvent } from 'react'
import {
  aCentimos,
  leerMontoEscrito,
  type AmbitoGasto,
  type CategoriaGasto,
  type MedioPago,
} from '../../api/contrato'
import { OperacionesRechazadas } from '../../componentes/sincronizacion/EstadoSincronizacion'
import type { FormularioLlenadoCable } from '../../api/contrato'
import { useBorradorAsistente } from '../../stores/borradorAsistente'
import { useSincronizacion } from '../../sincronizacion/cola'
import { useSesion } from '../../stores/sesion'
import { Aviso, Boton, Campo, Monto, Nota, Tarjeta, TituloPagina, TituloSeccion } from '../../ui/componentes'
import { totales, useGastos } from './almacen'
import estilos from './Gastos.module.css'

/**
 * Gastos (docs/03-modulos/Modulo-Gastos.md, D-24, ADR-051): lo que sale de la caja, del puesto
 * o de la casa, y de dónde salió (gaveta o Yape). Separarlo es lo que deja ver si el negocio
 * gana. El pago de un pedido llega solo desde Compras ("Pagué en efectivo / con Yape").
 */

export const NOMBRE_CATEGORIA: Record<CategoriaGasto, string> = {
  proveedor: 'Pago a proveedor',
  alquiler: 'Alquiler',
  servicios: 'Luz, agua o internet',
  transporte: 'Transporte',
  alimentacion: 'Comida de la casa',
  educacion: 'Colegio o estudios',
  otros: 'Otro gasto',
}

/** Lo que se ofrece según para qué fue: el puesto y la casa tienen gastos distintos */
const CATEGORIAS: Record<AmbitoGasto, CategoriaGasto[]> = {
  puesto: ['alquiler', 'servicios', 'transporte', 'otros'],
  hogar: ['alimentacion', 'servicios', 'educacion', 'otros'],
}

const NOMBRE_MEDIO: Record<MedioPago, string> = { efectivo: 'Efectivo', yape_plin: 'Yape o Plin' }

function FormularioGasto({
  alTerminar,
  inicial,
}: {
  alTerminar: () => void
  /** Lo que llenó el Asistente (D-28); el operador lo revisa y lo guarda */
  inicial?: FormularioLlenadoCable | null
}) {
  const anotar = useGastos((estado) => estado.anotar)
  const ambitoInicial: AmbitoGasto = inicial?.ambito ?? 'puesto'
  const categoriaInicial = (inicial?.categoria ?? 'otros') as CategoriaGasto
  const [monto, setMonto] = useState(inicial?.monto ?? '')
  const [medio, setMedio] = useState<MedioPago>(inicial?.medio ?? 'efectivo')
  const [ambito, setAmbito] = useState<AmbitoGasto>(ambitoInicial)
  const [categoria, setCategoria] = useState<CategoriaGasto>(
    CATEGORIAS[ambitoInicial].includes(categoriaInicial) ? categoriaInicial : 'otros',
  )
  const [descripcion, setDescripcion] = useState(inicial?.nota ?? '')
  const [error, setError] = useState<string | null>(null)

  const guardar = (evento: FormEvent) => {
    evento.preventDefault()
    const centimos = leerMontoEscrito(monto)
    if (!centimos) return setError('Escribe cuánto gastaste, por ejemplo 12.50')
    void anotar({ centimos, medio, ambito, categoria, descripcion })
    alTerminar()
  }

  const elegirAmbito = (nuevo: AmbitoGasto) => {
    setAmbito(nuevo)
    if (!CATEGORIAS[nuevo].includes(categoria)) setCategoria('otros')
  }

  return (
    <Tarjeta aiId="gastos.nuevo">
      <form className={estilos.formulario} onSubmit={guardar} noValidate>
        <TituloSeccion>Anotar un gasto</TituloSeccion>
        {inicial && (
          <Nota>Lo llenó el Asistente: revísalo y toca «Guardar gasto». Aún no se guardó nada.</Nota>
        )}
        {error && (
          <Aviso tipo="error" aiId="gastos.nuevo-error">
            {error}
          </Aviso>
        )}
        <Campo
          id="gasto-monto"
          aiId="gastos.monto"
          etiqueta="¿Cuánto fue? (S/)"
          inputMode="decimal"
          placeholder="Por ejemplo: 12.50"
          valor={monto}
          alCambiar={setMonto}
        />
        <fieldset className={estilos.grupo}>
          <legend className={estilos.pregunta}>¿De dónde salió la plata?</legend>
          <div className={estilos.opciones}>
            {(['efectivo', 'yape_plin'] as const).map((opcion) => (
              <Boton
                key={opcion}
                aiId={`gastos.medio-${opcion}`}
                variante="secundario"
                presionado={medio === opcion}
                onClick={() => setMedio(opcion)}
              >
                {opcion === 'efectivo' ? 'De la gaveta (efectivo)' : 'Del Yape o Plin'}
              </Boton>
            ))}
          </div>
        </fieldset>
        <fieldset className={estilos.grupo}>
          <legend className={estilos.pregunta}>¿Para qué fue?</legend>
          <div className={estilos.opciones}>
            <Boton
              aiId="gastos.ambito-puesto"
              variante="secundario"
              presionado={ambito === 'puesto'}
              onClick={() => elegirAmbito('puesto')}
            >
              Para el puesto
            </Boton>
            <Boton
              aiId="gastos.ambito-hogar"
              variante="secundario"
              presionado={ambito === 'hogar'}
              onClick={() => elegirAmbito('hogar')}
            >
              Para la casa
            </Boton>
          </div>
          <div className={estilos.opciones}>
            {CATEGORIAS[ambito].map((opcion) => (
              <Boton
                key={opcion}
                aiId={`gastos.categoria-${opcion}`}
                variante="secundario"
                presionado={categoria === opcion}
                onClick={() => setCategoria(opcion)}
              >
                {NOMBRE_CATEGORIA[opcion]}
              </Boton>
            ))}
          </div>
        </fieldset>
        <Campo
          id="gasto-descripcion"
          aiId="gastos.descripcion"
          etiqueta="Nota (opcional)"
          placeholder="Por ejemplo: mototaxi al mercado"
          maxLength={120}
          valor={descripcion}
          alCambiar={setDescripcion}
        />
        <div className={estilos.opciones}>
          <Boton aiId="gastos.guardar" tipo="submit">
            Guardar gasto
          </Boton>
          <Boton aiId="gastos.cancelar" variante="discreto" onClick={alTerminar}>
            Cancelar
          </Boton>
        </div>
      </form>
    </Tarjeta>
  )
}

export function Gastos() {
  const proyecto = useSesion((estado) => estado.proyecto)
  const { gastos, desdeDispositivo, iniciar, cargar, anular } = useGastos()
  const pendientes = useSincronizacion((estado) => estado.pendientes)
  const [anotando, setAnotando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [llenado, setLlenado] = useState<FormularioLlenadoCable | null>(null)
  const formularioAsistente = useBorradorAsistente((estado) => estado.formulario)

  // El Asistente dejó un gasto llenado (D-28): se abre el formulario con sus datos, sin guardar
  useEffect(() => {
    if (!proyecto || formularioAsistente?.formulario.tipo !== 'gasto') return
    const pedido = useBorradorAsistente.getState().tomarFormulario('gasto', proyecto)
    if (!pedido) return
    setLlenado(pedido)
    setAnotando(true)
  }, [proyecto, formularioAsistente])

  useEffect(() => {
    if (proyecto) iniciar(proyecto).catch(() => setError('No se pudieron leer los gastos.'))
  }, [proyecto, iniciar])

  // Al terminar de enviar lo anotado sin red, se trae la versión del servidor
  useEffect(() => {
    if (proyecto && pendientes === 0) cargar().catch(() => {})
  }, [proyecto, pendientes, cargar])

  const suma = totales(gastos)

  return (
    <main className={estilos.pantalla} data-ai-id="gastos">
      <div className={estilos.cabecera}>
        <TituloPagina ayuda="Lo que sale de la caja, del puesto o de la casa. Anotarlo te deja ver cuánto gana de verdad el negocio.">
          Gastos
        </TituloPagina>
        {!anotando && (
          <Boton aiId="gastos.anotar" onClick={() => setAnotando(true)}>
            Anotar un gasto
          </Boton>
        )}
      </div>

      <OperacionesRechazadas alDescartar={() => void cargar()} />
      {error && (
        <Aviso tipo="error" aiId="gastos.error">
          {error}
        </Aviso>
      )}
      {desdeDispositivo && (
        <Aviso tipo="info" aiId="gastos.sin-conexion">
          Mostrando lo guardado en esta tablet. Puedes seguir anotando: se envía al volver la conexión.
        </Aviso>
      )}

      {anotando && (
        <FormularioGasto
          key={llenado ? JSON.stringify(llenado) : 'nuevo'}
          inicial={llenado}
          alTerminar={() => {
            setAnotando(false)
            setLlenado(null)
          }}
        />
      )}

      <div className={estilos.resumen}>
        <Tarjeta aiId="gastos.total-hoy">
          <span className={estilos.rotulo}>Hoy salió</span>
          <span className={estilos.lineaMonto}>
            Efectivo <Monto centimos={suma.efectivo} tono="deuda" />
          </span>
          <span className={estilos.lineaMonto}>
            Yape o Plin <Monto centimos={suma.yape} tono="deuda" />
          </span>
        </Tarjeta>
        <Tarjeta aiId="gastos.puesto-y-casa">
          <span className={estilos.rotulo}>¿Para qué?</span>
          <span className={estilos.lineaMonto}>
            Del puesto <Monto centimos={suma.puesto} />
          </span>
          <span className={estilos.lineaMonto}>
            De la casa <Monto centimos={suma.hogar} />
          </span>
        </Tarjeta>
      </div>

      <TituloSeccion>Gastos de hoy</TituloSeccion>
      {gastos.length === 0 ? (
        <Nota>Hoy no se anotó ningún gasto.</Nota>
      ) : (
        <ul className={estilos.lista} data-ai-id="gastos.lista">
          {gastos.map((gasto) => (
            <li key={gasto.uuid}>
              <Tarjeta aiId={`gastos.gasto-${gasto.uuid}`} className={estilos.gasto}>
                <div className={estilos.detalle}>
                  <strong>{NOMBRE_CATEGORIA[gasto.categoria]}</strong>
                  <span className={estilos.nota}>
                    {[
                      gasto.ambito === 'hogar' ? 'De la casa' : 'Del puesto',
                      NOMBRE_MEDIO[gasto.medio],
                      gasto.descripcion,
                    ]
                      .filter(Boolean)
                      .join(' · ')}
                  </span>
                </div>
                <Monto centimos={aCentimos(gasto.monto)} tono="deuda" />
                <Boton
                  aiId={`gastos.borrar-${gasto.uuid}`}
                  variante="discreto"
                  onClick={() => void anular(gasto.uuid)}
                >
                  Borrar
                </Boton>
              </Tarjeta>
            </li>
          ))}
        </ul>
      )}
    </main>
  )
}

import { useEffect, useState, type FormEvent } from 'react'
import { SinConexion, pedir } from '../../api/cliente'
import {
  aCentimos,
  aSoles,
  leerMontoEscrito,
  type MovimientoCable,
  type ProductoCable,
  type Unidad,
} from '../../api/contrato'
import { OperacionesRechazadas } from '../../componentes/sincronizacion/EstadoSincronizacion'
import { useSesion } from '../../stores/sesion'
import { Aviso, Boton, Campo, Monto, Nota, Tarjeta, TituloPagina, TituloSeccion } from '../../ui/componentes'
import { aMilesimas, formatearCantidad, leerCantidadEscrita, useInventario } from './almacen'
import estilos from './Inventario.module.css'

/**
 * Inventario: cuánto hay de cada producto (docs/03-modulos/Modulo-Inventario.md). El stock
 * no se escribe a mano: se cuenta lo que hay ("Contar lo que hay") y el servidor calcula
 * la diferencia; las ventas y las compras recibidas lo mueven solas (ADR-031).
 */

const UNIDADES: { clave: Unidad; nombre: string }[] = [
  { clave: 'unidad', nombre: 'Por unidad' },
  { clave: 'kg', nombre: 'Por kilo' },
  { clave: 'litro', nombre: 'Por litro' },
]

const MOTIVOS: Record<MovimientoCable['motivo'], string> = {
  venta: 'Venta',
  anulacion_venta: 'Venta anulada',
  compra: 'Llegó en un pedido',
  ajuste: 'Conteo',
  merma: 'Merma',
}

function NuevoProducto({ alTerminar }: { alTerminar: () => void }) {
  const productos = useInventario((estado) => estado.productos)
  const crear = useInventario((estado) => estado.crear)
  const [nombre, setNombre] = useState('')
  const [unidad, setUnidad] = useState<Unidad>('unidad')
  const [precio, setPrecio] = useState('')
  const [stock, setStock] = useState('')
  const [minimo, setMinimo] = useState('')
  const [vence, setVence] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const guardar = (evento: FormEvent) => {
    evento.preventDefault()
    const limpio = nombre.trim()
    if (!limpio) return setError('Escribe el nombre del producto.')
    if (productos.some((p) => p.nombre.toLowerCase() === limpio.toLowerCase())) {
      return setError(`Ya existe un producto llamado «${limpio}».`)
    }
    const centimos = precio.trim() ? leerMontoEscrito(precio) : null
    if (precio.trim() && !centimos) return setError('Escribe el precio en soles, por ejemplo 3.50')
    const stockInicial = stock.trim() ? leerCantidadEscrita(stock) : null
    if (stock.trim() && stockInicial === null)
      return setError('Escribe cuánto hay con números, por ejemplo 12')
    const stockMinimo = minimo.trim() ? leerCantidadEscrita(minimo) : null
    if (minimo.trim() && stockMinimo === null) return setError('Escribe el mínimo con números, por ejemplo 5')
    void crear({
      nombre: limpio,
      unidad,
      precioVenta: centimos ? aSoles(centimos) : undefined,
      stockInicial: stockInicial ?? undefined,
      stockMinimo: stockMinimo ?? undefined,
      tieneVencimiento: vence,
    })
    alTerminar()
  }

  return (
    <form className={estilos.formulario} onSubmit={guardar} data-ai-id="inventario.nuevo">
      <TituloSeccion>Nuevo producto</TituloSeccion>
      {error && <Aviso tipo="error">{error}</Aviso>}
      <Campo
        id="prod-nombre"
        aiId="inventario.nombre"
        etiqueta="Nombre"
        valor={nombre}
        alCambiar={setNombre}
      />
      <div className={estilos.opciones}>
        {UNIDADES.map(({ clave, nombre: texto }) => (
          <Boton
            key={clave}
            aiId={`inventario.unidad-${clave}`}
            variante="secundario"
            presionado={unidad === clave}
            onClick={() => setUnidad(clave)}
          >
            {texto}
          </Boton>
        ))}
      </div>
      <div className={estilos.filaCampos}>
        <Campo
          id="prod-stock"
          aiId="inventario.stock-inicial"
          etiqueta="¿Cuánto hay ahora?"
          valor={stock}
          alCambiar={setStock}
          inputMode="decimal"
        />
        <Campo
          id="prod-minimo"
          aiId="inventario.minimo"
          etiqueta="Avisarme cuando queden"
          ayuda="Opcional"
          valor={minimo}
          alCambiar={setMinimo}
          inputMode="decimal"
        />
        <Campo
          id="prod-precio"
          aiId="inventario.precio"
          etiqueta={
            unidad === 'unidad' ? 'Precio de venta' : `Precio por ${unidad === 'kg' ? 'kilo' : 'litro'}`
          }
          ayuda="Opcional, en soles"
          valor={precio}
          alCambiar={setPrecio}
          inputMode="decimal"
        />
      </div>
      <Boton
        aiId="inventario.vence"
        variante="secundario"
        presionado={vence}
        onClick={() => setVence(!vence)}
      >
        {vence ? 'Este producto vence: sí' : 'Este producto vence: no'}
      </Boton>
      <div className={estilos.acciones}>
        <Boton aiId="inventario.nuevo-guardar" tipo="submit">
          Guardar producto
        </Boton>
        <Boton aiId="inventario.nuevo-cancelar" variante="discreto" onClick={alTerminar}>
          Cancelar
        </Boton>
      </div>
    </form>
  )
}

type Accion = 'contar' | 'merma' | 'precio' | 'movimientos'

function AccionProducto({
  producto,
  accion,
  alTerminar,
}: {
  producto: ProductoCable
  accion: Accion
  alTerminar: () => void
}) {
  const contar = useInventario((estado) => estado.contar)
  const merma = useInventario((estado) => estado.merma)
  const editar = useInventario((estado) => estado.editar)
  const [valor, setValor] = useState('')
  const [minimo, setMinimo] = useState(producto.stock_minimo ?? '')
  const [nota, setNota] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [movimientos, setMovimientos] = useState<MovimientoCable[] | null>(null)

  useEffect(() => {
    if (accion !== 'movimientos') return
    pedir<MovimientoCable[]>('GET', `/api/inventario/productos/${producto.uuid}/movimientos`)
      .then(setMovimientos)
      .catch((fallo: unknown) => {
        setMovimientos([])
        setError(
          fallo instanceof SinConexion
            ? 'El historial se ve cuando vuelva la red.'
            : 'No se pudo leer el historial.',
        )
      })
  }, [accion, producto.uuid])

  if (accion === 'movimientos') {
    return (
      <div className={estilos.bloque} data-ai-id={`inventario.movimientos-${producto.uuid}`}>
        {error && <Aviso tipo="info">{error}</Aviso>}
        {movimientos === null && <Nota>Leyendo el historial…</Nota>}
        {movimientos?.length === 0 && !error && <Nota>Aún no hay movimientos.</Nota>}
        <ul className={estilos.lista}>
          {movimientos?.map((m, indice) => (
            <li key={`${m.creado_en}-${indice}`} className={estilos.fila}>
              <span>
                {/* El stock inicial se guarda como ajuste: se nombra por su origen */}
                {m.origen_tipo === 'stock_inicial' ? 'Stock inicial' : MOTIVOS[m.motivo]}
                {m.nota && m.origen_tipo !== 'stock_inicial' ? ` · ${m.nota}` : ''}
              </span>
              <span className={aMilesimas(m.delta) < 0 ? estilos.negativo : estilos.positivo}>
                {aMilesimas(m.delta) > 0 ? '+' : ''}
                {formatearCantidad(aMilesimas(m.delta), producto.unidad)}
              </span>
            </li>
          ))}
        </ul>
        <Boton aiId="inventario.movimientos-cerrar" variante="discreto" onClick={alTerminar}>
          Cerrar historial
        </Boton>
      </div>
    )
  }

  const guardar = (evento: FormEvent) => {
    evento.preventDefault()
    if (accion === 'precio') {
      const centimos = valor.trim() ? leerMontoEscrito(valor) : null
      if (valor.trim() && !centimos) return setError('Escribe el precio en soles, por ejemplo 3.50')
      const nuevoMinimo = String(minimo).trim() ? leerCantidadEscrita(String(minimo)) : null
      if (String(minimo).trim() && nuevoMinimo === null) return setError('Escribe el mínimo con números.')
      if (!centimos && nuevoMinimo === null) return setError('No hay nada que cambiar.')
      void editar(producto.uuid, {
        precioVenta: centimos ? aSoles(centimos) : undefined,
        stockMinimo: nuevoMinimo ?? undefined,
      })
      return alTerminar()
    }
    const cantidad = leerCantidadEscrita(valor)
    if (cantidad === null) return setError('Escribe la cantidad con números, por ejemplo 12 o 1.5')
    if (accion === 'contar') void contar(producto.uuid, cantidad)
    else {
      if (cantidad === 0) return setError('La merma tiene que ser más que cero.')
      void merma(producto.uuid, cantidad, nota.trim())
    }
    alTerminar()
  }

  const etiqueta =
    accion === 'contar'
      ? `¿Cuánto hay de verdad? (${formatearCantidad(2000, producto.unidad).split(' ')[1]})`
      : accion === 'merma'
        ? '¿Cuánto se perdió o venció?'
        : 'Precio de venta nuevo'

  return (
    <form className={estilos.bloque} onSubmit={guardar} data-ai-id={`inventario.${accion}-${producto.uuid}`}>
      {error && <Aviso tipo="error">{error}</Aviso>}
      {accion === 'contar' && (
        <Nota>Cuenta lo que hay en el puesto. El sistema calcula la diferencia y la guarda como conteo.</Nota>
      )}
      <div className={estilos.filaCampos}>
        <Campo
          id={`${accion}-${producto.uuid}`}
          aiId={`inventario.${accion}-valor`}
          etiqueta={etiqueta}
          valor={valor}
          alCambiar={setValor}
          inputMode="decimal"
        />
        {accion === 'merma' && (
          <Campo
            id={`nota-${producto.uuid}`}
            aiId="inventario.merma-nota"
            etiqueta="¿Qué pasó?"
            ayuda="Opcional: vencido, roto…"
            valor={nota}
            alCambiar={setNota}
            maxLength={200}
          />
        )}
        {accion === 'precio' && (
          <Campo
            id={`minimo-${producto.uuid}`}
            aiId="inventario.precio-minimo"
            etiqueta="Avisarme cuando queden"
            valor={String(minimo)}
            alCambiar={setMinimo}
            inputMode="decimal"
          />
        )}
      </div>
      <div className={estilos.acciones}>
        <Boton aiId={`inventario.${accion}-guardar`} tipo="submit">
          {accion === 'contar' ? 'Guardar conteo' : accion === 'merma' ? 'Guardar merma' : 'Guardar cambios'}
        </Boton>
        <Boton aiId={`inventario.${accion}-cancelar`} variante="discreto" onClick={alTerminar}>
          Cancelar
        </Boton>
      </div>
    </form>
  )
}

function TarjetaProducto({ producto }: { producto: ProductoCable }) {
  const [accion, setAccion] = useState<Accion | null>(null)
  const stock = aMilesimas(producto.stock_actual)
  return (
    <Tarjeta aiId={`inventario.producto-${producto.uuid}`} className={estilos.tarjeta}>
      <div className={estilos.fila}>
        <div>
          <div className={estilos.nombre}>{producto.nombre}</div>
          {producto.precio_venta && (
            <Nota>
              Precio <Monto centimos={aCentimos(producto.precio_venta)} />
              {producto.unidad === 'unidad' ? '' : producto.unidad === 'kg' ? ' el kilo' : ' el litro'}
            </Nota>
          )}
        </div>
        <div
          className={
            producto.descuadre
              ? estilos.stockDescuadre
              : producto.bajo_minimo
                ? estilos.stockBajo
                : estilos.stock
          }
        >
          {formatearCantidad(stock, producto.unidad)}
        </div>
      </div>
      {/* El estado se dice con palabras: el color solo acompaña (Design-System §1) */}
      {producto.descuadre && (
        <Aviso tipo="error">El sistema dice que hay menos de cero. Cuenta cuánto hay de verdad.</Aviso>
      )}
      {!producto.descuadre && producto.bajo_minimo && (
        <Aviso tipo="pendiente">
          Queda poco: el mínimo es{' '}
          {formatearCantidad(aMilesimas(producto.stock_minimo ?? '0'), producto.unidad)}.
        </Aviso>
      )}
      {accion ? (
        <AccionProducto producto={producto} accion={accion} alTerminar={() => setAccion(null)} />
      ) : (
        <div className={estilos.acciones}>
          <Boton
            aiId={`inventario.contar-${producto.uuid}`}
            variante="secundario"
            onClick={() => setAccion('contar')}
          >
            Contar lo que hay
          </Boton>
          <Boton
            aiId={`inventario.merma-${producto.uuid}`}
            variante="secundario"
            onClick={() => setAccion('merma')}
          >
            Registrar merma
          </Boton>
          <Boton
            aiId={`inventario.precio-${producto.uuid}`}
            variante="discreto"
            onClick={() => setAccion('precio')}
          >
            Cambiar precio o mínimo
          </Boton>
          <Boton
            aiId={`inventario.historial-${producto.uuid}`}
            variante="discreto"
            onClick={() => setAccion('movimientos')}
          >
            Ver historial
          </Boton>
        </div>
      )}
    </Tarjeta>
  )
}

export function Inventario() {
  const proyecto = useSesion((estado) => estado.proyecto)
  const productos = useInventario((estado) => estado.productos)
  const desdeDispositivo = useInventario((estado) => estado.desdeDispositivo)
  const iniciar = useInventario((estado) => estado.iniciar)
  const cargar = useInventario((estado) => estado.cargar)
  const [busqueda, setBusqueda] = useState('')
  const [soloPoco, setSoloPoco] = useState(false)
  const [creando, setCreando] = useState(false)

  useEffect(() => {
    if (proyecto) void iniciar(proyecto)
  }, [proyecto, iniciar])

  const texto = busqueda.trim().toLowerCase()
  const visibles = productos.filter(
    (p) => p.nombre.toLowerCase().includes(texto) && (!soloPoco || p.bajo_minimo || p.descuadre),
  )
  const conAviso = productos.filter((p) => p.bajo_minimo || p.descuadre).length

  return (
    <main className={estilos.pantalla} data-ai-id="inventario">
      <TituloPagina ayuda="Cuánto te queda de cada producto. Baja solo al vender y sube cuando llega un pedido.">
        Inventario
      </TituloPagina>
      <OperacionesRechazadas alDescartar={() => void cargar()} />
      {desdeDispositivo && (
        <Aviso tipo="info" aiId="inventario.sin-conexion">
          Mostrando lo guardado en este dispositivo. Lo que registres se envía cuando vuelva la red.
        </Aviso>
      )}
      {creando ? (
        <NuevoProducto alTerminar={() => setCreando(false)} />
      ) : (
        <Boton aiId="inventario.nuevo-producto" onClick={() => setCreando(true)}>
          Nuevo producto
        </Boton>
      )}

      {productos.length === 0 ? (
        <Nota>
          Aún no hay productos. El inventario es opcional: las ventas y las compras funcionan sin él. Cuando
          registres un producto, las compras que lleguen pueden sumarse a su stock.
        </Nota>
      ) : (
        <>
          <div className={estilos.filaCampos}>
            <Campo
              id="buscar-producto"
              aiId="inventario.buscar"
              etiqueta="Buscar producto"
              valor={busqueda}
              alCambiar={setBusqueda}
            />
          </div>
          <Boton
            aiId="inventario.solo-poco"
            variante="secundario"
            presionado={soloPoco}
            onClick={() => setSoloPoco(!soloPoco)}
          >
            {`Solo lo que queda poco (${conAviso})`}
          </Boton>
          {visibles.length === 0 && <Nota>Ningún producto coincide.</Nota>}
          {visibles.map((producto) => (
            <TarjetaProducto key={producto.uuid} producto={producto} />
          ))}
        </>
      )}
    </main>
  )
}

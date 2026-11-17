import { useEffect, useState } from 'react'
import { formatearCentimos, leerMontoEscrito, type ProductoCable } from '../../api/contrato'
import { useBorradorAsistente } from '../../stores/borradorAsistente'
import { useSesion } from '../../stores/sesion'
import { Aviso, Boton, Campo, Nota, Tarjeta, TituloSeccion } from '../../ui/componentes'
import {
  aMilesimas,
  formatearCantidad,
  leerCantidadEscrita,
  montoPorCantidad,
  useInventario,
} from '../inventario/almacen'
import { productoPorNombre } from '../inventario/nombres'
import { useVentas } from './almacen'
import estilos from './BorradorAsistente.module.css'

/**
 * La orden que llenó el Asistente (ADR-049): el operador la revisa, corrige lo que haga falta
 * y la guarda. Hasta tocar «Guardar orden» no existe ninguna venta.
 *
 * Cada línea se enlaza con su producto del inventario si el nombre calza
 * (`productoPorNombre`): así descuenta stock y, si el operador no dijo el precio, propone el
 * del inventario. El total lo vuelve a calcular el servidor, como en toda venta.
 */

interface Linea {
  nombre: string
  cantidad: string
  precio: string
}

/** Precio de una línea en céntimos y lo que suma, o null si falta algo */
function calcular(linea: Linea): { milesimas: number; precio: number; monto: number } | null {
  const milesimas = leerCantidadEscrita(linea.cantidad)
  const precio = leerMontoEscrito(linea.precio)
  if (!milesimas || precio === null) return null
  return { milesimas, precio, monto: montoPorCantidad(precio, milesimas) }
}

export function BorradorAsistente() {
  const proyecto = useSesion((estado) => estado.proyecto)
  const borrador = useBorradorAsistente((estado) => estado.borrador)
  const descartar = useBorradorAsistente((estado) => estado.descartar)
  const productos = useInventario((estado) => estado.productos)
  const proyectoInventario = useInventario((estado) => estado.proyecto)
  const iniciarInventario = useInventario((estado) => estado.iniciar)
  const { abrirOrden, agregarItem, seleccionar } = useVentas()
  const [lineas, setLineas] = useState<Linea[]>([])
  const [nombreOrden, setNombreOrden] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [guardando, setGuardando] = useState(false)

  useEffect(() => {
    // Sin red se usa lo guardado en el dispositivo; si falla, la orden va con texto libre
    if (proyecto && proyectoInventario !== proyecto) void iniciarInventario(proyecto).catch(() => {})
  }, [proyecto, proyectoInventario, iniciarInventario])

  // Cada borrador nuevo vuelve a llenar el formulario, con el precio del inventario si falta
  useEffect(() => {
    if (!borrador) return
    setError(null)
    setNombreOrden(borrador.para ?? '')
    setLineas(
      borrador.items.map((item) => {
        const producto = productoPorNombre(useInventario.getState().productos, item.nombre)
        return {
          nombre: producto?.nombre ?? item.nombre,
          cantidad: item.cantidad,
          precio: item.precio ?? producto?.precio_venta ?? '',
        }
      }),
    )
  }, [borrador?.version]) // eslint-disable-line react-hooks/exhaustive-deps -- solo al llegar uno nuevo

  if (!borrador || borrador.proyecto !== proyecto) return null

  const cambiar = (indice: number, campo: keyof Linea, valor: string) =>
    setLineas((actuales) => actuales.map((l, i) => (i === indice ? { ...l, [campo]: valor } : l)))
  const productoDe = (linea: Linea): ProductoCable | null => productoPorNombre(productos, linea.nombre)
  const total = lineas.reduce((suma, linea) => suma + (calcular(linea)?.monto ?? 0), 0)

  const guardar = async () => {
    if (guardando) return
    for (const linea of lineas) {
      if (!linea.nombre.trim()) return setError('Falta el nombre de un producto.')
      if (!leerCantidadEscrita(linea.cantidad))
        return setError(`Escribe cuántos de «${linea.nombre}» lleva, por ejemplo 2`)
      if (leerMontoEscrito(linea.precio) === null)
        return setError(`Escribe el precio de «${linea.nombre}», por ejemplo 4.80`)
    }
    setGuardando(true)
    try {
      const orden = await abrirOrden({ nombreOrden: nombreOrden.trim() || undefined })
      for (const linea of lineas) {
        const cuenta = calcular(linea)
        if (!cuenta) continue
        const producto = productoDe(linea)
        await agregarItem(orden, {
          nombre: producto?.nombre ?? linea.nombre.trim(),
          cantidad: producto ? formatearCantidad(cuenta.milesimas, producto.unidad) : linea.cantidad.trim(),
          centimos: cuenta.monto,
          producto: producto ? { uuid: producto.uuid, milesimas: cuenta.milesimas } : undefined,
        })
      }
      seleccionar(orden)
      descartar()
    } catch {
      setError('No se pudo guardar la orden. Inténtalo de nuevo.')
    } finally {
      setGuardando(false)
    }
  }

  return (
    <Tarjeta aiId="ventas.borrador-asistente" className={estilos.tarjeta}>
      <TituloSeccion>El Asistente llenó esta orden</TituloSeccion>
      <Nota>
        Revisa cada producto, corrige lo que haga falta y toca «Guardar orden». Aún no se guardó nada.
      </Nota>
      {error && (
        <Aviso tipo="error" aiId="ventas.borrador-error">
          {error}
        </Aviso>
      )}
      <Campo
        id="borrador-nombre-orden"
        aiId="ventas.borrador-nombre-orden"
        etiqueta="Nombre de la orden (opcional)"
        ayuda="Por ejemplo: Sra. Bertha, Mesa 2"
        valor={nombreOrden}
        alCambiar={setNombreOrden}
      />
      {lineas.map((linea, indice) => {
        const producto = productoDe(linea)
        const cuenta = calcular(linea)
        return (
          <div key={indice} className={estilos.linea} data-ai-id={`ventas.borrador-linea-${indice}`}>
            <div className={estilos.campos}>
              <Campo
                id={`borrador-nombre-${indice}`}
                aiId={`ventas.borrador-nombre-${indice}`}
                etiqueta="Producto"
                valor={linea.nombre}
                alCambiar={(valor) => cambiar(indice, 'nombre', valor)}
              />
              <Campo
                id={`borrador-cantidad-${indice}`}
                aiId={`ventas.borrador-cantidad-${indice}`}
                etiqueta={
                  producto
                    ? `Cantidad (${formatearCantidad(1000, producto.unidad).replace(/^1 /, '')})`
                    : 'Cantidad'
                }
                inputMode="decimal"
                valor={linea.cantidad}
                alCambiar={(valor) => cambiar(indice, 'cantidad', valor)}
              />
              <Campo
                id={`borrador-precio-${indice}`}
                aiId={`ventas.borrador-precio-${indice}`}
                etiqueta="Precio de cada uno (S/)"
                inputMode="decimal"
                valor={linea.precio}
                alCambiar={(valor) => cambiar(indice, 'precio', valor)}
              />
            </div>
            <span className={estilos.detalle}>
              {producto
                ? `Del inventario · quedan ${formatearCantidad(aMilesimas(producto.stock_actual), producto.unidad)}`
                : 'No está en el inventario: se anota como texto'}
              {cuenta && ` · ${formatearCentimos(cuenta.monto)}`}
            </span>
          </div>
        )
      })}
      <div className={estilos.pie}>
        <span className={estilos.total}>Total {formatearCentimos(total)}</span>
        <div className={estilos.botones}>
          <Boton aiId="ventas.borrador-guardar" deshabilitado={guardando} onClick={() => void guardar()}>
            {guardando ? 'Guardando…' : 'Guardar orden'}
          </Boton>
          <Boton aiId="ventas.borrador-descartar" variante="discreto" onClick={descartar}>
            Descartar
          </Boton>
        </div>
      </div>
    </Tarjeta>
  )
}

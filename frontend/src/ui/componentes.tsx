import type { InputHTMLAttributes, ReactNode } from 'react'
import { formatearCentimos } from '../api/contrato'
import estilos from './ui.module.css'

/**
 * Piezas base del Design System. Todos los módulos las usan en vez de
 * definir sus propios botones o campos: así un cambio de token o de regla
 * (texto sobre íconos, tamaño táctil) llega a toda la app a la vez.
 *
 * `aiId` es obligatorio en todo lo interactivo: el AI Companion ubica y
 * navega cada control por su `data-ai-id` (AGENTS.md).
 */

function unir(...clases: (string | false | undefined)[]): string {
  return clases.filter(Boolean).join(' ')
}

type VarianteBoton = 'primario' | 'secundario' | 'peligro' | 'ia' | 'discreto'

interface PropsBoton {
  /** Texto completo del botón: nunca un ícono solo (Design-System §4) */
  children: string
  aiId: string
  variante?: VarianteBoton
  onClick?: () => void
  tipo?: 'button' | 'submit'
  deshabilitado?: boolean
  anchoCompleto?: boolean
  presionado?: boolean
}

export function Boton({
  children,
  aiId,
  variante = 'primario',
  onClick,
  tipo = 'button',
  deshabilitado = false,
  anchoCompleto = false,
  presionado,
}: PropsBoton) {
  return (
    <button
      type={tipo}
      className={unir(estilos.boton, estilos[variante], anchoCompleto && estilos.anchoCompleto)}
      data-ai-id={aiId}
      onClick={onClick}
      disabled={deshabilitado}
      aria-pressed={presionado}
    >
      {children}
    </button>
  )
}

interface PropsTarjeta {
  children: ReactNode
  aiId?: string
  className?: string
}

export function Tarjeta({ children, aiId, className }: PropsTarjeta) {
  return (
    <div className={unir(estilos.tarjeta, className)} data-ai-id={aiId}>
      {children}
    </div>
  )
}

interface PropsCampo extends Omit<
  InputHTMLAttributes<HTMLInputElement>,
  'onChange' | 'value' | 'id' | 'className'
> {
  id: string
  aiId: string
  etiqueta: string
  valor: string
  alCambiar: (valor: string) => void
  ayuda?: string
  error?: string | null
}

export function Campo({ id, aiId, etiqueta, valor, alCambiar, ayuda, error, ...resto }: PropsCampo) {
  const idAyuda = ayuda ? `${id}-ayuda` : undefined
  const idError = error ? `${id}-error` : undefined
  return (
    <div className={estilos.campo}>
      <label className={estilos.etiqueta} htmlFor={id}>
        {etiqueta}
      </label>
      {ayuda && (
        <span className={estilos.ayuda} id={idAyuda}>
          {ayuda}
        </span>
      )}
      <input
        {...resto}
        id={id}
        data-ai-id={aiId}
        className={unir(estilos.control, error ? estilos.controlConError : undefined)}
        value={valor}
        onChange={(evento) => alCambiar(evento.target.value)}
        aria-invalid={error ? true : undefined}
        aria-describedby={[idAyuda, idError].filter(Boolean).join(' ') || undefined}
      />
      {error && (
        <span className={estilos.error} id={idError} role="alert">
          {error}
        </span>
      )}
    </div>
  )
}

type TipoAviso = 'info' | 'exito' | 'pendiente' | 'error'

const CLASE_AVISO: Record<TipoAviso, string> = {
  info: estilos.avisoInfo,
  exito: estilos.avisoExito,
  pendiente: estilos.avisoPendiente,
  error: estilos.avisoError,
}

export function Aviso({
  tipo = 'info',
  children,
  aiId,
}: {
  tipo?: TipoAviso
  children: ReactNode
  aiId?: string
}) {
  return (
    <p
      className={unir(estilos.aviso, CLASE_AVISO[tipo])}
      role={tipo === 'error' ? 'alert' : 'status'}
      data-ai-id={aiId}
    >
      {children}
    </p>
  )
}

type Tono = 'ingreso' | 'pendiente' | 'deuda' | 'neutro'
type TamanoMonto = 'grande' | 'orden' | 'normal'

const CLASE_TONO: Record<Tono, string> = {
  ingreso: estilos.tonoIngreso,
  pendiente: estilos.tonoPendiente,
  deuda: estilos.tonoDeuda,
  neutro: estilos.tonoNeutro,
}
const CLASE_TAMANO: Record<TamanoMonto, string> = {
  grande: estilos.montoGrande,
  orden: estilos.montoOrden,
  normal: estilos.montoNormal,
}

/** Monto en soles. Recibe céntimos enteros (ADR-033): nunca un float. */
export function Monto({
  centimos,
  tono = 'neutro',
  tamano = 'normal',
}: {
  centimos: number
  tono?: Tono
  tamano?: TamanoMonto
}) {
  return (
    <span className={unir(estilos.monto, CLASE_TONO[tono], CLASE_TAMANO[tamano])}>
      {formatearCentimos(centimos)}
    </span>
  )
}

/**
 * Título de la pantalla. `ayuda` dice en una frase para qué sirve: quien entra por
 * primera vez sabe dónde está y qué puede hacer sin tener que explorar.
 */
export function TituloPagina({ children, ayuda }: { children: ReactNode; ayuda?: string }) {
  if (!ayuda) return <h1 className={estilos.tituloPagina}>{children}</h1>
  return (
    <div className={estilos.encabezado}>
      <h1 className={estilos.tituloPagina}>{children}</h1>
      <p className={estilos.ayudaPagina}>{ayuda}</p>
    </div>
  )
}

export function TituloSeccion({ children }: { children: ReactNode }) {
  return <h2 className={estilos.tituloSeccion}>{children}</h2>
}

export function Nota({ children }: { children: ReactNode }) {
  return <p className={estilos.nota}>{children}</p>
}

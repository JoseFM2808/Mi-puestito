import { useSesion } from '../stores/sesion'

/**
 * Cliente HTTP único hacia el backend. Agrega el token, traduce errores a
 * mensajes en lenguaje simple y distingue "sin conexión" (reintentable) de
 * "el servidor dijo que no" (hay que mostrárselo al operador).
 */

/** El servidor respondió con error: `detalle` ya está en palabras simples. */
export class ErrorApi extends Error {
  readonly estado: number
  readonly detalle: string

  constructor(estado: number, detalle: string) {
    super(detalle)
    this.name = 'ErrorApi'
    this.estado = estado
    this.detalle = detalle
  }

  /** 4xx salvo sesión/espera: reintentar no lo arregla, hay que avisar. */
  get esDefinitivo(): boolean {
    return this.estado >= 400 && this.estado < 500 && ![401, 408, 429].includes(this.estado)
  }
}

/** No hubo respuesta: sin red o el programa cerrado. Se puede reintentar. */
export class SinConexion extends Error {
  constructor() {
    super('Sin conexión con el programa')
    this.name = 'SinConexion'
  }
}

interface DetalleValidacion {
  loc?: (string | number)[]
  msg?: string
}

function detalleLegible(cuerpo: unknown, estado: number): string {
  if (cuerpo && typeof cuerpo === 'object' && 'detail' in cuerpo) {
    const detalle = (cuerpo as { detail: unknown }).detail
    if (typeof detalle === 'string') return detalle
    // 422 de FastAPI: lista de campos con problema
    if (Array.isArray(detalle)) {
      const campos = (detalle as DetalleValidacion[])
        .map((error) => error.loc?.at(-1))
        .filter((campo): campo is string => typeof campo === 'string')
      return campos.length
        ? `Revisa estos datos: ${[...new Set(campos)].join(', ')}.`
        : 'Revisa los datos ingresados.'
    }
  }
  if (estado >= 500) return 'El programa tuvo un problema. Intenta de nuevo en un momento.'
  return 'No se pudo completar la operación.'
}

export type MetodoHttp = 'GET' | 'POST' | 'PATCH' | 'DELETE'

export async function pedir<T>(metodo: MetodoHttp, ruta: string, cuerpo?: unknown): Promise<T> {
  const token = useSesion.getState().token
  let respuesta: Response
  try {
    respuesta = await fetch(ruta, {
      method: metodo,
      headers: {
        ...(cuerpo === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
    })
  } catch {
    throw new SinConexion()
  }

  if (respuesta.status === 204) return undefined as T
  const datos: unknown = await respuesta.json().catch(() => null)
  if (!respuesta.ok) {
    if (respuesta.status === 401) useSesion.getState().cerrarSesion()
    throw new ErrorApi(respuesta.status, detalleLegible(datos, respuesta.status))
  }
  return datos as T
}

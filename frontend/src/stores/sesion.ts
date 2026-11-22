import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

/**
 * Sesión del operador (Zustand).
 *
 * Cada usuario entra con nombre + PIN y queda ligado a UN proyecto (demo o
 * el negocio real). El token nunca abre datos de otro proyecto (lo valida
 * el backend, ver seguridad.py). Se persiste en sessionStorage: dura la
 * sesión del operador — al abrir una pestaña/sesión nueva hay que volver a
 * ingresar, igual que el tamaño de letra (ver stores/preferencias.ts).
 */

interface EstadoSesion {
  autenticado: boolean
  proyecto: string | null
  nombreProyecto: string | null
  esReal: boolean
  token: string | null
  cargando: boolean
  error: string | null
  iniciarSesion: (nombreUsuario: string, pin: string) => Promise<boolean>
  cerrarSesion: () => void
}

export const useSesion = create<EstadoSesion>()(
  persist(
    (set) => ({
      autenticado: false,
      proyecto: null,
      nombreProyecto: null,
      esReal: false,
      token: null,
      cargando: false,
      error: null,

      iniciarSesion: async (nombreUsuario, pin) => {
        set({ cargando: true, error: null })
        try {
          const respuesta = await fetch('/api/auth/ingresar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nombre_usuario: nombreUsuario, pin }),
          })
          if (!respuesta.ok) {
            set({ cargando: false, error: await motivoDelRechazo(respuesta) })
            return false
          }
          const datos = await respuesta.json()
          set({
            autenticado: true,
            proyecto: datos.proyecto,
            nombreProyecto: datos.nombre_proyecto,
            esReal: datos.es_real,
            token: datos.token,
            cargando: false,
            error: null,
          })
          return true
        } catch {
          set({
            cargando: false,
            error: 'No se pudo conectar. Revisa que el programa esté abierto.',
          })
          return false
        }
      },

      cerrarSesion: () => {
        set({
          autenticado: false,
          proyecto: null,
          nombreProyecto: null,
          esReal: false,
          token: null,
          error: null,
        })
      },
    }),
    {
      name: 'sesion-operador',
      storage: createJSONStorage(() => sessionStorage),
      // cargando/error son estado transitorio de la petición: no se persisten
      partialize: (estado) => ({
        autenticado: estado.autenticado,
        proyecto: estado.proyecto,
        nombreProyecto: estado.nombreProyecto,
        esReal: estado.esReal,
        token: estado.token,
      }),
    },
  ),
)

/**
 * Por qué no entró, en palabras: tras varios PIN errados el servidor pide esperar (429) y hay que
 * decírselo, o la persona sigue probando sin saber que por ahora no la dejará entrar.
 */
async function motivoDelRechazo(respuesta: Response): Promise<string> {
  if (respuesta.status === 429) {
    const cuerpo = (await respuesta.json().catch(() => null)) as { detail?: unknown } | null
    return typeof cuerpo?.detail === 'string'
      ? cuerpo.detail
      : 'Demasiados intentos con PIN incorrecto. Espera un momento antes de volver a intentar.'
  }
  if (respuesta.status >= 500) return 'El programa tuvo un problema. Intenta de nuevo en un momento.'
  return 'Usuario o PIN incorrecto'
}

/** Cabecera lista para usar en cualquier fetch protegido del backend. */
export function cabeceraAutorizacion(): Record<string, string> {
  const token = useSesion.getState().token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

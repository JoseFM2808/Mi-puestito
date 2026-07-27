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
            set({ cargando: false, error: 'Usuario o PIN incorrecto' })
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

/** Cabecera lista para usar en cualquier fetch protegido del backend. */
export function cabeceraAutorizacion(): Record<string, string> {
  const token = useSesion.getState().token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

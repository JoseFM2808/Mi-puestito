import { useState } from 'react'
import { useSesion } from '../../stores/sesion'
import './Login.css'

/**
 * Pantalla de ingreso. Login simple por usuario + PIN (AGENTS.md: nada de
 * formularios complejos, el vendedor no tiene experiencia técnica).
 *
 * Dos cuentas hoy: "Demo" (datos de muestra, PIN público 0000) y el negocio
 * real. Cada una abre SOLO su propio proyecto — nunca se mezclan.
 */

const CUENTAS = [
  {
    nombreUsuario: 'demo',
    etiqueta: 'Demo',
    descripcion: 'Datos de muestra para conocer la app. PIN: 0000',
  },
  {
    nombreUsuario: 'anita',
    etiqueta: 'Anita (negocio real)',
    descripcion: 'Los datos reales del puesto de Anita.',
  },
] as const

export function Login() {
  const iniciarSesion = useSesion((estado) => estado.iniciarSesion)
  const cargando = useSesion((estado) => estado.cargando)
  const error = useSesion((estado) => estado.error)
  const [cuentaAbierta, setCuentaAbierta] = useState<string | null>(null)
  const [pin, setPin] = useState('')

  const elegirCuenta = (nombreUsuario: string) => {
    setCuentaAbierta(nombreUsuario)
    setPin('')
  }

  const ingresar = async (nombreUsuario: string) => {
    await iniciarSesion(nombreUsuario, pin)
  }

  return (
    <main className="login" data-ai-id="login">
      <h1 className="login-titulo">Mi Puestito</h1>
      <p className="login-subtitulo">¿Con qué negocio quieres entrar?</p>

      <div className="login-cuentas">
        {CUENTAS.map((cuenta) => (
          <div className="card login-cuenta" key={cuenta.nombreUsuario}>
            <button
              type="button"
              className="login-boton-cuenta"
              data-ai-id={`login.cuenta-${cuenta.nombreUsuario}`}
              onClick={() => elegirCuenta(cuenta.nombreUsuario)}
            >
              {cuenta.etiqueta}
            </button>
            <p className="login-descripcion">{cuenta.descripcion}</p>

            {cuentaAbierta === cuenta.nombreUsuario && (
              <form
                className="login-formulario"
                onSubmit={(evento) => {
                  evento.preventDefault()
                  void ingresar(cuenta.nombreUsuario)
                }}
              >
                <label className="login-etiqueta-campo" htmlFor={`pin-${cuenta.nombreUsuario}`}>
                  PIN
                </label>
                <input
                  id={`pin-${cuenta.nombreUsuario}`}
                  className="login-campo-pin"
                  data-ai-id={`login.pin-${cuenta.nombreUsuario}`}
                  type="password"
                  inputMode="numeric"
                  value={pin}
                  onChange={(evento) => setPin(evento.target.value)}
                  autoFocus
                />
                <button
                  type="submit"
                  className="btn btn-primario"
                  data-ai-id={`login.ingresar-${cuenta.nombreUsuario}`}
                  disabled={cargando}
                >
                  {cargando ? 'Ingresando…' : 'Ingresar'}
                </button>
              </form>
            )}
          </div>
        ))}
      </div>

      <div role="status" aria-live="polite">
        {error && (
          <p className="login-error" data-ai-id="login.error">
            {error}
          </p>
        )}
      </div>
    </main>
  )
}

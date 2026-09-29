import { useEffect, useState } from 'react'
import type { CuentaVisibleCable } from '../../api/contrato'
import { useSesion } from '../../stores/sesion'
import { Aviso, Boton, Campo, Nota, Tarjeta, TituloPagina } from '../../ui/componentes'
import estilos from './Login.module.css'

/**
 * Pantalla de ingreso. Login simple por usuario + PIN (AGENTS.md: nada de
 * formularios complejos, el vendedor no tiene experiencia técnica).
 *
 * Las cuentas vienen del backend (`GET /api/auth/cuentas`): el código del
 * frontend no tiene escrito el nombre de ningún negocio real (repo público).
 * Cada cuenta abre SOLO su propio proyecto — nunca se mezclan.
 */
export function Login() {
  const iniciarSesion = useSesion((estado) => estado.iniciarSesion)
  const cargando = useSesion((estado) => estado.cargando)
  const error = useSesion((estado) => estado.error)
  const [cuentas, setCuentas] = useState<CuentaVisibleCable[] | null>(null)
  const [sinConexion, setSinConexion] = useState(false)
  const [cuentaAbierta, setCuentaAbierta] = useState<string | null>(null)
  const [pin, setPin] = useState('')

  useEffect(() => {
    fetch('/api/auth/cuentas')
      .then((respuesta) => respuesta.json() as Promise<CuentaVisibleCable[]>)
      .then(setCuentas)
      .catch(() => setSinConexion(true))
  }, [])

  return (
    <main className={estilos.login} data-ai-id="login">
      <TituloPagina>Mi Puestito</TituloPagina>
      <p className={estilos.subtitulo}>¿Con qué negocio quieres entrar?</p>

      {sinConexion && (
        <Aviso tipo="error" aiId="login.sin-conexion">
          No se pudo conectar con el programa. Revisa que esté abierto.
        </Aviso>
      )}
      {!cuentas && !sinConexion && <Nota>Cargando…</Nota>}

      <div className={estilos.cuentas}>
        {cuentas?.map((cuenta) => (
          <Tarjeta key={cuenta.nombre_usuario} className={estilos.cuenta}>
            <Boton
              aiId={`login.cuenta-${cuenta.nombre_usuario}`}
              variante="secundario"
              anchoCompleto
              onClick={() => {
                setCuentaAbierta(cuenta.nombre_usuario)
                setPin('')
              }}
            >
              {cuenta.es_real ? `${cuenta.nombre_proyecto} (negocio real)` : cuenta.nombre_proyecto}
            </Boton>
            <Nota>
              {cuenta.es_real
                ? `Los datos reales del negocio ${cuenta.nombre_proyecto}.`
                : 'Datos de práctica para conocer la app. PIN: 0000'}
            </Nota>

            {cuentaAbierta === cuenta.nombre_usuario && (
              <form
                className={estilos.formulario}
                onSubmit={(evento) => {
                  evento.preventDefault()
                  void iniciarSesion(cuenta.nombre_usuario, pin)
                }}
              >
                <Campo
                  id={`pin-${cuenta.nombre_usuario}`}
                  aiId={`login.pin-${cuenta.nombre_usuario}`}
                  etiqueta="PIN"
                  type="password"
                  inputMode="numeric"
                  autoComplete="current-password"
                  valor={pin}
                  alCambiar={setPin}
                  autoFocus
                />
                <Boton
                  tipo="submit"
                  aiId={`login.ingresar-${cuenta.nombre_usuario}`}
                  deshabilitado={cargando}
                >
                  {cargando ? 'Ingresando…' : 'Ingresar'}
                </Boton>
              </form>
            )}
          </Tarjeta>
        ))}
      </div>

      {error && (
        <Aviso tipo="error" aiId="login.error">
          {error}
        </Aviso>
      )}
    </main>
  )
}

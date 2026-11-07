import { useEffect } from 'react'
import { Asistente } from './componentes/asistente/Asistente'
import { BarraSuperior } from './componentes/barra-superior/BarraSuperior'
import { LimiteErrores } from './componentes/limite-errores/LimiteErrores'
import { Login } from './componentes/login/Login'
import { Compras } from './modules/compras/Compras'
import { Dashboard } from './modules/dashboard/Dashboard'
import { Fiados } from './modules/fiados/Fiados'
import { Inventario } from './modules/inventario/Inventario'
import { Ventas } from './modules/ventas/Ventas'
import { iniciarSincronizacion } from './sincronizacion/cola'
import { useNavegacion } from './stores/navegacion'
import { useSesion } from './stores/sesion'

/**
 * Sin sesión: pantalla de ingreso. Con sesión: la barra superior y la
 * pantalla elegida, cada una aislada en su propio límite de errores (si
 * Ventas falla, la Caja de hoy y el Asistente siguen vivos).
 */
export function App() {
  const autenticado = useSesion((estado) => estado.autenticado)
  const proyecto = useSesion((estado) => estado.proyecto)
  const pantalla = useNavegacion((estado) => estado.pantalla)
  const asistenteAbierto = useNavegacion((estado) => estado.asistenteAbierto)

  // La cola de cambios offline de ESTE proyecto se envía en segundo plano
  useEffect(() => {
    if (!autenticado || !proyecto) return
    return iniciarSincronizacion(proyecto)
  }, [autenticado, proyecto])

  if (!autenticado) return <Login />

  return (
    <>
      <BarraSuperior />
      {asistenteAbierto && (
        <LimiteErrores nombreModulo="Asistente" idModulo="asistente">
          <Asistente />
        </LimiteErrores>
      )}
      {pantalla === 'caja' && (
        <LimiteErrores nombreModulo="Caja de hoy" idModulo="dashboard">
          <Dashboard />
        </LimiteErrores>
      )}
      {pantalla === 'ventas' && (
        <LimiteErrores nombreModulo="Ventas" idModulo="ventas">
          <Ventas />
        </LimiteErrores>
      )}
      {pantalla === 'fiados' && (
        <LimiteErrores nombreModulo="Fiados" idModulo="fiados">
          <Fiados />
        </LimiteErrores>
      )}
      {pantalla === 'compras' && (
        <LimiteErrores nombreModulo="Compras" idModulo="compras">
          <Compras />
        </LimiteErrores>
      )}
      {pantalla === 'inventario' && (
        <LimiteErrores nombreModulo="Inventario" idModulo="inventario">
          <Inventario />
        </LimiteErrores>
      )}
    </>
  )
}

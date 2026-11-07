import { useEffect } from 'react'
import estilos from './App.module.css'
import { Asistente, AsistenteFlotante } from './componentes/asistente/Asistente'
import { BarraSuperior } from './componentes/barra-superior/BarraSuperior'
import { LimiteErrores } from './componentes/limite-errores/LimiteErrores'
import { Login } from './componentes/login/Login'
import { MenuLateral } from './componentes/menu-lateral/MenuLateral'
import { Compras } from './modules/compras/Compras'
import { Dashboard } from './modules/dashboard/Dashboard'
import { Fiados } from './modules/fiados/Fiados'
import { Inventario } from './modules/inventario/Inventario'
import { Ventas } from './modules/ventas/Ventas'
import { iniciarSincronizacion } from './sincronizacion/cola'
import { useNavegacion } from './stores/navegacion'
import { useSesion } from './stores/sesion'

/**
 * Sin sesión: pantalla de ingreso. Con sesión: el menú a la izquierda, la barra
 * superior y la pantalla elegida, cada una aislada en su propio límite de errores
 * (si Ventas falla, la Caja de hoy y el Asistente siguen vivos).
 */
export function App() {
  const autenticado = useSesion((estado) => estado.autenticado)
  const proyecto = useSesion((estado) => estado.proyecto)
  const pantalla = useNavegacion((estado) => estado.pantalla)
  const asistenteFlotante = useNavegacion((estado) => estado.asistenteFlotante)

  // La cola de cambios offline de ESTE proyecto se envía en segundo plano
  useEffect(() => {
    if (!autenticado || !proyecto) return
    return iniciarSincronizacion(proyecto)
  }, [autenticado, proyecto])

  if (!autenticado) return <Login />

  return (
    <div className={estilos.marco}>
      <MenuLateral />
      <div className={estilos.contenido}>
        <BarraSuperior />
        {pantalla === 'asistente' && (
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
      </div>
      {/* Sobre la pantalla actual: el operador ve la app mientras el Asistente lo guía */}
      {asistenteFlotante && pantalla !== 'asistente' && (
        <LimiteErrores nombreModulo="Asistente" idModulo="asistente-ventana">
          <AsistenteFlotante />
        </LimiteErrores>
      )}
    </div>
  )
}

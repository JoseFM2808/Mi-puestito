import { BarraSuperior } from './componentes/barra-superior/BarraSuperior'
import { LimiteErrores } from './componentes/limite-errores/LimiteErrores'
import { Dashboard } from './modules/dashboard/Dashboard'

export function App() {
  return (
    <>
      <BarraSuperior />
      {/* Cada módulo va aislado: si falla, no derriba al resto de la app */}
      <LimiteErrores nombreModulo="Caja de hoy" idModulo="dashboard">
        <Dashboard />
      </LimiteErrores>
    </>
  )
}

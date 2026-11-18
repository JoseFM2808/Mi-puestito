import { useEffect, useRef } from 'react'
import { PANTALLAS, useNavegacion } from '../../stores/navegacion'
import { useSesion } from '../../stores/sesion'
import { Icono } from '../../ui/iconos'
import { ReiniciarPractica } from '../barra-superior/AccionesBarra'
import { Respaldo } from '../barra-superior/Respaldo'
import estilos from './MenuLateral.module.css'

/**
 * Menú a la izquierda, siempre en el mismo lugar (Design-System §6).
 *
 * - Pantalla ancha (computadora, tablet echada): fijo y siempre visible.
 * - Pantalla angosta (teléfono, tablet parada): el mismo panel entra desde la izquierda
 *   con el botón "Menú" y se cierra tocando fuera, con "Cerrar menú" o con Escape.
 *
 * Cada opción lleva ícono, nombre y para qué sirve, y la pantalla actual se marca
 * con color y con la palabra "Aquí estás" (no solo con color).
 */
export function MenuLateral() {
  const { pantalla, menuAbierto, irA, cerrarMenu } = useNavegacion()
  const nombreProyecto = useSesion((estado) => estado.nombreProyecto)
  const esReal = useSesion((estado) => estado.esReal)
  const cerrarSesion = useSesion((estado) => estado.cerrarSesion)
  const panel = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!menuAbierto) return
    // Al abrirse en el teléfono: el foco entra al panel y Escape lo cierra
    panel.current?.focus()
    const alPresionar = (evento: KeyboardEvent) => {
      if (evento.key === 'Escape') cerrarMenu()
    }
    window.addEventListener('keydown', alPresionar)
    return () => window.removeEventListener('keydown', alPresionar)
  }, [menuAbierto, cerrarMenu])

  return (
    <>
      {menuAbierto && <div className={estilos.fondo} onClick={cerrarMenu} aria-hidden="true" />}
      <nav
        ref={panel}
        className={`${estilos.menu} ${menuAbierto ? estilos.abierto : ''}`}
        data-ai-id="menu"
        aria-label="Menú principal"
        tabIndex={-1}
      >
        <div className={estilos.cabecera}>
          <p className={estilos.marca}>Mi Puestito</p>
          <p className={estilos.negocio} data-ai-id="menu.negocio">
            {esReal ? nombreProyecto : `${nombreProyecto}: datos de práctica`}
          </p>
          <button type="button" className={estilos.cerrar} data-ai-id="menu.cerrar" onClick={cerrarMenu}>
            Cerrar menú
          </button>
        </div>

        <ul className={estilos.opciones}>
          {PANTALLAS.map(({ clave, nombre, ayuda }) => {
            const actual = pantalla === clave
            return (
              <li key={clave}>
                <button
                  type="button"
                  className={`${estilos.opcion} ${actual ? estilos.actual : ''} ${clave === 'asistente' ? estilos.opcionIa : ''}`}
                  data-ai-id={`menu.ir-${clave}`}
                  aria-current={actual ? 'page' : undefined}
                  onClick={() => irA(clave)}
                >
                  <span className={estilos.icono}>
                    <Icono nombre={clave} />
                  </span>
                  <span className={estilos.textos}>
                    <span className={estilos.nombre}>{nombre}</span>
                    <span className={estilos.ayuda}>{actual ? 'Aquí estás' : ayuda}</span>
                  </span>
                </button>
              </li>
            )
          })}
        </ul>

        <div className={estilos.extras}>
          <Respaldo />
          {!esReal && <ReiniciarPractica />}
          <button type="button" className={estilos.salir} data-ai-id="menu.salir" onClick={cerrarSesion}>
            <Icono nombre="salir" tamano="1.4rem" />
            Salir de este negocio
          </button>
        </div>
      </nav>
    </>
  )
}

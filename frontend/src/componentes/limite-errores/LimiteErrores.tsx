import { Component, Fragment, type ErrorInfo, type ReactNode } from 'react'
import { Boton, Nota } from '../../ui/componentes'
import estilos from './LimiteErrores.module.css'

/**
 * Límite de errores por módulo.
 *
 * Regla del proyecto: el fallo de un módulo no debe derribar a otro. Si el
 * módulo envuelto lanza un error al renderizar, aquí se contiene y se muestra
 * un aviso con texto completo; el resto de la aplicación (barra superior,
 * demás módulos) sigue funcionando.
 */

interface Props {
  /** Nombre del módulo tal como lo lee el usuario: "Caja de hoy", "Ventas"… */
  nombreModulo: string
  /** Identificador para el AI Companion: error-modulo.<idModulo> */
  idModulo: string
  children: ReactNode
}

interface Estado {
  hayError: boolean
  /** Cambia en cada reintento para forzar un montaje limpio del módulo */
  intento: number
}

export class LimiteErrores extends Component<Props, Estado> {
  state: Estado = { hayError: false, intento: 0 }

  static getDerivedStateFromError(): Pick<Estado, 'hayError'> {
    return { hayError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Queda en consola para diagnóstico; el usuario solo ve el aviso simple
    console.error(`Falló el módulo ${this.props.nombreModulo}:`, error, info)
  }

  reintentar = () => {
    // Cambiar `intento` cambia la `key` del subárbol: React desmonta el módulo
    // roto y lo vuelve a montar desde cero. Sin esto, un error determinista
    // (datos locales dañados, el caso más probable) reaparecería siempre.
    this.setState((estado) => ({ hayError: false, intento: estado.intento + 1 }))
  }

  render() {
    if (!this.state.hayError) {
      return <Fragment key={this.state.intento}>{this.props.children}</Fragment>
    }

    return (
      <div className={estilos.limite} data-ai-id={`error-modulo.${this.props.idModulo}`}>
        <p className={estilos.titulo}>El módulo {this.props.nombreModulo} tuvo un problema</p>
        <Nota>Los demás módulos siguen funcionando. Puedes intentar abrirlo de nuevo.</Nota>
        <Boton
          aiId={`error-modulo.${this.props.idModulo}.reintentar`}
          variante="secundario"
          onClick={this.reintentar}
        >
          Volver a intentar
        </Boton>
      </div>
    )
  }
}

/**
 * Íconos simples, dibujados aquí para no depender de una librería. Acompañan al texto,
 * nunca lo reemplazan (Design-System §4): un mismo dibujo por pantalla, siempre igual,
 * ayuda a reconocerla de un vistazo. Toman el color del texto (`currentColor`).
 */

export type NombreIcono =
  | 'caja'
  | 'ventas'
  | 'fiados'
  | 'compras'
  | 'inventario'
  | 'asistente'
  | 'rapida'
  | 'pago'
  | 'pedido'
  | 'salir'

const TRAZOS: Record<NombreIcono, string[]> = {
  // Caja registradora: cajón y ranura de billetes
  caja: ['M3 9h18v11H3z', 'M7 9V5h10v4', 'M7 14h4', 'M7 17h2'],
  // Canasta
  ventas: ['M4 9h16l-1.6 10.5H5.6z', 'M8 9l4-5 4 5', 'M10 13v3', 'M14 13v3'],
  // Cuaderno de fiados
  fiados: ['M6 3h12v18H6z', 'M9 8h6', 'M9 12h6', 'M9 16h3', 'M4 7h2', 'M4 12h2', 'M4 17h2'],
  // Camión de reparto
  compras: [
    'M2 7h12v9H2z',
    'M14 10h4l3 3v3h-7',
    'M5 18.5a1.5 1.5 0 1 0 0.01 0',
    'M17 18.5a1.5 1.5 0 1 0 0.01 0',
  ],
  // Caja de productos
  inventario: ['M3 8l9-4 9 4v9l-9 4-9-4z', 'M3 8l9 4 9-4', 'M12 12v9'],
  // Globo de conversación
  asistente: ['M4 5h16v11H9l-5 4z', 'M8 9h8', 'M8 12h5'],
  // Rayo: venta rápida
  rapida: ['M13 3L5 14h6l-1 7 8-11h-6z'],
  // Monedas: anotar un pago
  pago: [
    'M4 9a5 3 0 1 0 10 0a5 3 0 1 0-10 0',
    'M4 9v5c0 1.7 2.2 3 5 3',
    'M10 13a5 3 0 1 0 10 0a5 3 0 1 0-10 0',
    'M10 13v4c0 1.7 2.2 3 5 3s5-1.3 5-3v-4',
  ],
  // Paquete que llega
  pedido: ['M4 8l8-4 8 4v8l-8 4-8-4z', 'M4 8l8 4 8-4', 'M12 12v8', 'M8 6l8 4'],
  // Puerta de salida
  salir: ['M14 4H5v16h9', 'M10 12h10', 'M17 9l3 3-3 3'],
}

export function Icono({ nombre, tamano = '1.6rem' }: { nombre: NombreIcono; tamano?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={tamano}
      height={tamano}
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {TRAZOS[nombre].map((d) => (
        <path key={d} d={d} />
      ))}
    </svg>
  )
}

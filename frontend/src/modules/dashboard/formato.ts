/**
 * Formato de fechas para Perú. El idioma y la zona horaria son fijos
 * (es-PE, America/Lima): el usuario nunca los configura a mano y la app no
 * depende de que la tablet tenga bien puesta su zona. Los montos se formatean
 * en api/contrato.ts (céntimos enteros, ADR-033).
 */

const ZONA_PERU = 'America/Lima'

const formatoFechaLarga = new Intl.DateTimeFormat('es-PE', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  timeZone: ZONA_PERU,
})

/** "Viernes 12 de junio" */
export function formatearFechaLarga(fecha: Date): string {
  const texto = formatoFechaLarga.format(fecha)
  return texto.charAt(0).toUpperCase() + texto.slice(1)
}

// "2026-07-08": el día calendario peruano de una fecha, para comparar días
const formatoDiaPeru = new Intl.DateTimeFormat('en-CA', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  timeZone: ZONA_PERU,
})

function diaEnPeru(fecha: Date): string {
  return formatoDiaPeru.format(fecha)
}

const formatoFechaCorta = new Intl.DateTimeFormat('es-PE', {
  weekday: 'long',
  day: 'numeric',
  timeZone: ZONA_PERU,
})

/** Días de diferencia con hoy, contados sobre el calendario peruano. */
export function diasHastaHoy(fecha: Date): number {
  // El corte del día es la medianoche de Lima, no la de la tablet
  return Math.round((Date.parse(diaEnPeru(fecha)) - Date.parse(diaEnPeru(new Date()))) / 86_400_000)
}

/**
 * "hoy", "mañana", "el sábado 14" o, si ya pasó, "ayer (atrasado)".
 *
 * Una fecha pasada NUNCA debe decir "hoy": un pedido vencido presentado como
 * que llega hoy engaña al vendedor justo en la cifra con la que planifica su
 * caja (ver Modulo-Dashboard).
 */
export function formatearFechaRelativa(fecha: Date): string {
  const dias = diasHastaHoy(fecha)

  if (dias === 0) return 'hoy'
  if (dias === 1) return 'mañana'
  if (dias === 2) return 'pasado mañana'
  if (dias > 2) return `el ${formatoFechaCorta.format(fecha)}`

  // Atrasado: siempre con la palabra, nunca solo con color
  if (dias === -1) return 'ayer (atrasado)'
  return `${formatoFechaCorta.format(fecha)} (atrasado ${Math.abs(dias)} días)`
}

/** True si la fecha ya pasó: el Dashboard lo marca como deuda/vencido. */
export function estaAtrasado(fecha: Date): boolean {
  return diasHastaHoy(fecha) < 0
}

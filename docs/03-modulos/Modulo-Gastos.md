# Módulo: Gastos Adicionales

#modulo #fase2

Registra gastos fuera de las compras de mercadería.

## Tipos

- **Gastos del puesto:** alquiler, servicios, transporte, mermas.
- **Gastos del hogar:** alimentación, servicios básicos, educación.

Clasificación manual al registrar. Alimenta el análisis de [[Modulo-Analisis]] para separar la rentabilidad del negocio de la economía familiar.

## Estado
- **Hecho (2026-11-17, ADR-051):** pantalla Gastos con monto, de dónde salió (gaveta o Yape), si es del puesto o
  de la casa y su categoría; funciona sin red. El pago de un pedido llega solo desde [[Modulo-Compras]] y la
  [[Modulo-Dashboard]] lo descuenta de "En caja ahora".

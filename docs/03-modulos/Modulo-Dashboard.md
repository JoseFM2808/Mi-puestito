# Módulo: Dashboard / Caja Diaria

#modulo #mvp

**Pantalla principal.** Resumen del día actual y proyección del día siguiente.

## Información mostrada

- Monto total de ventas cerradas en el día
- Órdenes de venta activas (abiertas) → [[Modulo-Ventas]]
- Órdenes de compra pendientes de recibir, con fecha estimada y monto → [[Modulo-Compras]]
- **Proyección:** "Mañana necesitas S/. X en caja" (según órdenes de compra próximas a llegar)
- Fiados activos y monto total por cobrar
- Ventas rápidas pendientes de formalizar

## Interacción con el AI Companion

El [[AI-Companion]] puede leer cualquier cifra del dashboard, explicarla en lenguaje simple y navegar al módulo de origen si el usuario lo pide.

## Estado
- Fase: **MVP**
- Dependencias: lee datos de Ventas y Compras, pero no bloquea su funcionamiento.

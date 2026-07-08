# Sincronización Offline-First

#arquitectura

La conectividad en mercados peruanos es variable. El sistema **nunca** puede bloquear una venta o una compra por falta de red.

## Estrategia

- **Últimas ~2 semanas** de datos (ventas, compras, sesiones) viven localmente en el dispositivo (IndexedDB).
- **Histórico anterior** vive en la nube y se solicita bajo demanda.
- **Cola de sincronización:** las operaciones hechas sin conexión se encolan y se envían automáticamente al recuperar red.
- **Conflictos:** last-write-wins en esta etapa (un solo dispositivo, una sola operadora). Revisar si se habilita multi-dispositivo.

## Reglas

1. Ninguna funcionalidad core ([[Modulo-Ventas]], [[Modulo-Compras]]) puede requerir conexión para operar.
2. El usuario debe poder ver con agilidad todo lo ocurrido en la semana actual y la anterior sin tocar la nube.
3. La fecha/hora se detecta automáticamente por zona horaria (Perú, UTC-5); el usuario nunca la digita.

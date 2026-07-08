# 🏪 Sistema de Gestión para Pequeños Vendedores

> **Punto de entrada de la bóveda.** Desde aquí se navega toda la documentación del proyecto. Abrir la carpeta `docs/` como bóveda en Obsidian para ver el grafo completo.

## ¿Qué es este proyecto?

App web tablet-first para vendedores informales en Perú, con un AI Companion integrado. Empieza con un caso real: el puesto de abarrotes de la mamá de José en un mercado de Lima. Ver [[Vision-General]].

## Mapa de la documentación

### 1. Visión
- [[Vision-General]] — qué es, por qué existe, a dónde va
- [[Publico-Objetivo]] — para quién está diseñado

### 2. Arquitectura
- [[Stack-Tecnologico]] — tecnologías elegidas y por qué
- [[Sincronizacion-Offline]] — estrategia offline-first
- [[Decisiones-Tecnicas]] — registro histórico de decisiones

### 3. Módulos
- [[Modulo-Dashboard]] — caja diaria y resumen (MVP)
- [[Modulo-Compras]] — proveedores y órdenes de pedido (MVP)
- [[Modulo-Ventas]] — órdenes activas, fiado, venta rápida (MVP)
- [[Modulo-Inventario]] — stock, vencimientos, precios (Fase 2)
- [[Modulo-Analisis]] — rentabilidad y reportes (Fase 2)
- [[Modulo-Gastos]] — gastos del puesto y del hogar (Fase 2)

### 4. Inteligencia Artificial
- [[AI-Companion]] — el asistente integrado (core del MVP)
- [[Orquestacion-IA]] — LangGraph y la capa de runtime
- [[Conexion-Agnostica]] — independencia del proveedor de modelo

### 5. Metodología de desarrollo
- [[Metodologia-Desarrollo]] — cómo se construye este proyecto
- [[Agentes-De-Desarrollo]] — roles de agentes IA en el desarrollo

### 6. Diseño
- [[Design-System]] — tokens de diseño centralizados

## Principios del proyecto

1. **Modular** — ningún módulo depende obligatoriamente de otro
2. **Documentado para IA** — cada pieza tiene su MD como contexto
3. **Agnóstico a IA** — cualquier modelo puede ejecutarse junto al programa
4. **Offline-first** — funciona sin internet, sincroniza cuando hay
5. **Accesible** — para usuarios sin experiencia tecnológica

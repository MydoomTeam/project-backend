# Arquitectura por capas

## Propósito
Definir exactamente qué hace cada capa, qué no puede hacer y qué dependencias están permitidas.

## Arquitectura real del proyecto

ArenaSync actualmente contiene dos stacks funcionales que comparten la misma base de datos:

## Stack de torneos
- src/app/api/
- src/app/services/
- src/app/repositories/
- src/app/models/
- src/app/schemas/

Responsable de:
- torneos
- partidas
- inscripciones
- rankings
- ELO

## Stack administrativo
- src/app/controllers/
- src/app/services/
- src/app/repositories/
- src/app/domain/models/
- src/app/domain/schemas/

Responsable de:
- jugadores
- autenticación
- administración
- alertas
- historial

Ambos stacks comparten:
- src/app/core/
- src/app/tasks/
- src/app/main.py
- tests/

## Presentación

Carpetas:
- src/app/main.py
- src/app/api/
- src/app/controllers/

Responsabilidad:
- recibir peticiones HTTP
- validar solo lo mínimo necesario en el borde
- llamar a servicios de aplicación
- construir respuestas HTTP
- traducir errores de aplicación a respuestas HTTP

Permitido:
- routers
- controllers
- manejo de requests/responses
- serialización/deserialización
- validación básica de interfaz

Prohibido:
- reglas de negocio
- acceso directo a repositorios
- acceso directo a ORM
- consultas SQL
- sesiones de base de datos
- lógica de orquestación que pertenece a services

## Aplicación

Carpeta:
- src/app/services/

Responsabilidad:
- orquestar casos de uso
- ejecutar flujos de negocio
- coordinar repositorios
- aplicar reglas de negocio a nivel de aplicación
- mantener los controllers delgados

Permitido:
- services
- coordinación de casos de uso
- validaciones de flujo
- orquestación de transacciones si hace falta

Prohibido:
- concerns de HTTP
- acceso directo a BD
- detalles de ORM
- SQL
- lógica de presentación
- manejo de rutas

## Dominio

Carpetas:
- src/app/domain/
- src/app/domain/models/
- src/app/domain/schemas/
- src/app/domain/constants.py

Responsabilidad:
- conservar los conceptos centrales del sistema
- definir entidades
- definir contratos de datos
- definir constantes compartidas
- realizar validaciones estructurales

IMPORTANTE:
En ArenaSync la carpeta Domain NO implementa casos de uso.
La lógica de negocio debe permanecer en: src/app/services/
Domain funciona principalmente como una capa de definición de datos.

Prohibido:
- dependencias FastAPI
- concerns HTTP
- detalles SQLAlchemy
- sesiones de BD
- implementaciones de repositorios
- lógica específica de framework

## Infraestructura

Carpetas:
- src/app/core/
- src/app/repositories/
- src/app/models/
- src/app/schemas/
- src/app/tasks/

Responsabilidad:
- persistencia
- integraciones externas
- configuración
- utilidades de autenticación
- conexión a base de datos
- trabajos en segundo plano

Permitido:
- instituciones de repositorios
- modelos ORM
- schemas técnicos de persistencia o transporte si aplica
- configuración
- manejo de sesión de BD
- helpers de auth
- schedulers/tasks

Prohibido:
- reglas de negocio
- lógica de presentación
- manejo de rutas
- decisiones de negocio
- lógica que pertenece a services o al dominio

## Nota importante sobre carpetas heredadas

Si existen conceptos duplicados entre:
- src/app/domain/models/
- src/app/models/
- src/app/domain/schemas/
- src/app/schemas/

Deben tratarse como riesgo de migración y consolidación. No debe existir más de una fuente de verdad para el mismo concepto de negocio.

## Flujo permitido de dependencias
- Presentación -> Aplicación -> Dominio -> Infraestructura

## Flujo de retorno
- Infraestructura -> Dominio -> Aplicación -> Presentación

## Dependencias prohibidas
- Presentación -> Infraestructura
- Presentación -> Base de datos
- Aplicación -> acceso directo a base de datos
- Dominio -> FastAPI
- Dominio -> SQLAlchemy
- Dominio -> sesiones ORM
- dependencias circulares entre capas
- saltarse capas intermedias

## Reglas para src/app/core/

src/app/core/ puede contener:
- config
- auth utilities
- database connection
- dependency helpers

Pero src/app/core/ no puede contener:
- reglas de negocio
- orquestación de casos de uso
- lógica de dominio

## Criterio de error
- Si una función o módulo hace trabajo de otra capa, es una violación arquitectónica.
# ArenaSync — Contexto del proyecto

## Qué es ArenaSync
ArenaSync es un backend diseñado para centralizar y simplificar la gestión de torneos de videojuegos en un solo lugar.

Permite:
- registrar y autenticar jugadores,
- crear y administrar torneos,
- generar brackets según el formato de eliminación,
- registrar resultados,
- actualizar ELO automáticamente,
- mantener historiales de partidas y jugadores,
- mostrar rankings,
- gestionar alertas y estados del torneo.

## Objetivo funcional
El sistema debe soportar el ciclo completo de un torneo de forma consistente:
1. registro y login,
2. creación de torneo,
3. inscripción,
4. generación de bracket,
5. inicio del torneo,
6. registro de resultados,
7. actualización automática de ELO,
8. generación de la siguiente ronda o cierre final,
9. consulta de ranking e historial.

## Reglas de negocio principales
- Un jugador se autentica con token Bearer.
- El creador del torneo actúa como administrador de ese torneo.
- El creador es el único que puede generar el bracket, iniciar el torneo y registrar resultados.
- Los estados del torneo deben ser explícitos y consistentes.
- Los BYE deben resolverse automáticamente cuando aplique.
- El ELO debe usar actualización adaptativa según el valor actual.
- Los rankings y el historial deben ser consultables por API.

## Formatos de eliminación soportados
- Eliminación Sencilla
- Eliminación Doble
- Round Robin
- Swiss

## Base técnica
- Backend monolítico.
- FastAPI.
- SQLAlchemy.
- PostgreSQL 16.
- Tests con Pytest.

## Qué debe mantenerse siempre
- coherencia entre reglas de negocio y endpoints,
- separación por capas,
- consistencia entre models, schemas, services, repositories y controllers,
- trazabilidad de errores y estados,
- comportamiento estable para pruebas y demo.

## Qué no se debe introducir
- sobreingeniería,
- capas nuevas innecesarias,
- lógica duplicada,
- lógica de negocio en controllers,
- acceso directo a BD desde presentación,
- dependencias circulares,
- cambios de contrato sin revisión explícita.

## Prioridad de calidad
1. Corrección funcional.
2. Arquitectura limpia por capas.
3. Semántica REST correcta.
4. Clean Code.
5. Mantenibilidad.
6. Refactor mínimo y controlado.

## Regla general
Cualquier cambio debe:
- resolver un problema real,
- mantener el comportamiento esperado,
- respetar las capas,
- evitar complejidad innecesaria.
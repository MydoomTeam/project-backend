# Estándar REST de la API

## Propósito
Verificar que la API use recursos, métodos HTTP, códigos de estado y payloads de manera correcta y consistente.

## Regla de idioma para rutas
Las rutas finales deben estar en inglés.

Si una ruta en español debe cambiarse, el cambio debe tratarse como un breaking change controlado o mediante una capa temporal de compatibilidad que esté documentada.

## Reglas de nomenclatura de rutas
- Usar sustantivos, no verbos.
- Preferir plural en colecciones.
- Usar minúsculas.
- Evitar underscores.
- Usar guiones solo si hace falta.
- Evitar nombres de rutas que parezcan acciones.

## Modelo recomendado de rutas para ArenaSync
Ejemplos de rutas objetivo en inglés:
- /users
- /sessions
- /tournaments
- /tournaments/{tournament_id}
- /tournaments/available
- /tournaments/{tournament_id}/registrations
- /tournaments/{tournament_id}/bracket
- /tournaments/{tournament_id}/matches
- /tournaments/{tournament_id}/matches/{match_id}/result
- /tournaments/{tournament_id}/ranking
- /tournaments/{tournament_id}/players/{player_id}/history
- /alerts
- /alerts/{alert_id}/ack
- /admins/password
- /health

## Semántica de métodos HTTP
- GET: leer datos.
- POST: crear recursos o disparar una acción claramente orientada a creación.
- PUT: reemplazar por completo un recurso.
- PATCH: actualizar parcialmente un recurso.
- DELETE: eliminar un recurso.

## Errores comunes que deben reportarse
- GET usado para cambiar estado del servidor.
- POST usado como falso GET.
- POST usado para búsquedas cuando un GET con query params basta.
- PATCH usado cuando se esperaba reemplazo total.
- PUT usado cuando solo se quería una parte.
- rutas que codifican acciones en lugar de recursos.

## Query params
Usar query params para:
- filtrado,
- búsqueda,
- orden,
- paginación,
- flags opcionales.

Usar parámetros de ruta para:
- identificadores obligatorios,
- relaciones jerárquicas entre recursos.

## Formato de payload
- Usar JSON de forma consistente.
- Mantener request y response explícitos.
- Mantener los nombres de campos en inglés.
- Mantener schemas previsibles y estables.

## Headers requeridos
- Content-Type: application/json
- Accept
- Authorization: Bearer <token>
- CORS cuando sea necesario
- X-Request-ID o identificador de trazabilidad equivalente cuando aplique

## Códigos de estado
- 200 OK
- 201 Created
- 204 No Content
- 400 Bad Request
- 401 Unauthorized
- 403 Forbidden
- 404 Not Found
- 409 Conflict
- 422 Unprocessable Entity
- 500 Internal Server Error

## Relación con la arquitectura
La capa de presentación recibe HTTP.
La capa de aplicación ejecuta la lógica de negocio.
La capa de repositorio maneja persistencia.
El controller no debe contener persistencia ni reglas de negocio.

## Criterio de error
Si la API tiene verbos en rutas, usa mal HTTP, tiene payloads inconsistentes o esconde lógica de negocio en controllers, debe reportarse como violación REST.
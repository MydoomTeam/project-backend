# Casos de uso - santgm56 (ArenaSync)

Este documento detalla los casos de uso asignados a santgm56 y define exactamente que se debe implementar en backend y como debe verse el flujo desde UI.

Fuentes base:

- [Documentation/User_cases/CU_01_santgm56.pdf](Documentation/User_cases/CU_01_santgm56.pdf)
- [Documentation/User_cases/CU_02_santgm56.pdf](Documentation/User_cases/CU_02_santgm56.pdf)
- [Documentation/User_cases/CU_03_santgm56.pdf](Documentation/User_cases/CU_03_santgm56.pdf)

## 1. Alcance y supuestos

- Backend monolitico en FastAPI con arquitectura por capas.
- Base de datos relacional (PostgreSQL).
- No microservicios, no event bus, no sobreingenieria.
- Clean code obligatorio: nombres claros, funciones pequenas, sin comentarios innecesarios.

## 2. Actores y roles

- Administrador: usuario autenticado con permisos para gestionar torneos y seguridad.
- Scheduler: proceso interno automatizado que dispara tareas periodicas.

## 3. Convenciones comunes

- Autenticacion y autorizacion se aplican en backend.
- Todas las operaciones criticas dejan registro en LogAuditoria.
- Errores se reportan con mensajes claros y codigos HTTP correctos.

## 4. UC-01 - Gestionar contrasena de administrador

### Objetivo

Permitir crear o actualizar la contrasena de un administrador de forma segura usando bcrypt con factor >= 12.

### Actor principal

Administrador.

### Disparador

El administrador abre el formulario de creacion/actualizacion de contrasena.

### Precondiciones

- Administrador autenticado.
- Formulario de cambio de contrasena disponible.

### Postcondiciones

- La contrasena queda almacenada solo como hash seguro en la base de datos.
- Si falla la validacion o persistencia, no se guarda ningun cambio.

### Flujo normal

1. El administrador ingresa la nueva contrasena.
2. El administrador confirma la contrasena.
3. El administrador envia el formulario.
4. El backend valida politicas de seguridad.
5. El backend valida que la confirmacion coincide.
6. El backend genera el hash bcrypt (factor >= 12).
7. El backend guarda el hash en BD.
8. El backend responde OK y registra auditoria.

### Flujos alternos

A1. Contrasena y confirmacion no coinciden:
- El backend responde 400 y no guarda cambios.

A2. Contrasena no cumple politicas:
- El backend responde 400 con detalle de reglas incumplidas.

A3. Error de persistencia:
- El backend responde 500 y registra el fallo.

### Reglas de negocio y validaciones

- Longitud minima definida por el equipo (ej. 8 o mas).
- Debe incluir al menos una mayuscula, una minuscula y un numero (si el equipo lo define).
- Prohibido almacenar contrasena en texto plano o reversible.

### Datos y entidades afectadas

- Administrador: id, password_hash, updated_at.
- LogAuditoria: actor_id, accion, entidad, timestamp.

### Endpoints y contratos

- POST /admins/password
  - Request:
    - password: string
    - password_confirm: string
  - Response 200:
    - message: "password_updated"
  - Response 400:
    - error: "validation_error"
    - details: ["..." ]

### UI/UX (criterios)

- Formulario con dos campos (password, confirm).
- Mensajes de error especificos por regla fallida.
- Mensaje de exito visible y sin revelar datos sensibles.

### Requisitos no funcionales y seguridad

- bcrypt con factor >= 12.
- Tiempo de respuesta razonable (sub-segundo en entorno local).
- No loggear contrasenas.

### Errores complejos y casos borde

- Contrasena con espacios iniciales/finales: definir si se permite o se normaliza.
- Intentos repetidos: registrar evento en auditoria.

### Dependencias e integraciones

- Libreria bcrypt.
- Sistema de autenticacion actual.

### Metricas y analitica

- Conteo de cambios de contrasena por periodo.
- Ratio de errores de validacion.

### Pruebas minimas

- Given admin autenticado, When password valida, Then se actualiza hash.
- Given password y confirm diferentes, When submit, Then 400.
- Given password debil, When submit, Then 400 con detalle.
- Given fallo de BD, When submit, Then 500 sin cambios.

## 5. UC-02 - Generar y notificar alertas de eventos

### Objetivo

Detectar eventos vencidos y registrar una alerta visible en el dashboard en menos de 30s.

### Actor principal

Scheduler (proceso interno).

### Disparador

Ejecucion periodica del scheduler (cada 30s).

### Precondiciones

- Scheduler activo.
- Torneos y enfrentamientos registrados.

### Postcondiciones

- Alerta registrada en BD y disponible para consulta en UI.
- Si falla la publicacion en UI, la alerta sigue registrada.

### Flujo normal

1. Scheduler inicia ciclo de verificacion.
2. Backend consulta torneos/enfrentamientos.
3. Backend detecta condicion de alerta.
4. Backend crea alerta en BD.
5. Backend registra auditoria.
6. UI consulta /alerts y muestra la alerta.

### Flujos alternos

A1. No hay eventos vencidos:
- No se crea alerta y se registra el ciclo como OK.

A2. Error al insertar alerta:
- Backend registra error y reintenta en el siguiente ciclo.

A3. Duplicados:
- Backend evita alertas duplicadas por la misma causa en la misma ventana de tiempo.

### Reglas de negocio y validaciones

- Tiempo maximo entre deteccion y visualizacion: 30s.
- Cada alerta debe tener tipo, timestamp y entidad asociada.

### Datos y entidades afectadas

- Alerta: id, tipo, mensaje, entidad_id, created_at, status.
- LogAuditoria: actor_id="scheduler", accion, entidad, timestamp.

### Endpoints y contratos

- GET /alerts
  - Response 200:
    - items: [ { id, tipo, mensaje, created_at, status } ]

- PATCH /alerts/{id}/ack (opcional)
  - Response 200:
    - message: "acknowledged"

### UI/UX (criterios)

- Dashboard muestra alertas nuevas sin recargar pagina (polling o refresh).
- Indicador visual de alerta nueva.

### Requisitos no funcionales y seguridad

- SLA <= 30s desde deteccion.
- Acceso a alertas solo para rol administrador.

### Errores complejos y casos borde

- Scheduler caido: alertas se generan al reactivarse y quedan trazadas como atrasadas.
- Alertas en rafaga: paginacion y limites de consulta.

### Dependencias e integraciones

- Scheduler interno (APScheduler o tarea cron en el monolito).
- Reloj del servidor sincronizado.

### Metricas y analitica

- Latencia promedio de alertas (deteccion a visibilidad).
- Numero de alertas por tipo y por torneo.

### Pruebas minimas

- Given match vencido, When scheduler corre, Then alerta creada.
- Given alerta creada, When GET /alerts, Then aparece en lista.
- Given alerta duplicada, When scheduler corre, Then no crea duplicado.

## 6. UC-03 - Crear torneo

### Objetivo

Permitir que un administrador cree un torneo en maximo 2 pasos de UI y con estado inicial Pendiente.

### Actor principal

Administrador.

### Disparador

El administrador selecciona "Crear torneo" en el panel.

### Precondiciones

- Administrador autenticado.
- Acceso al modulo de torneos.

### Postcondiciones

- Torneo registrado en BD con estado Pendiente.
- Se muestra resumen con opciones para agregar participantes y generar bracket.

### Flujo normal

1. Admin abre formulario de creacion.
2. Admin ingresa: nombre, tipo de eliminacion, duracion por ronda, numero de participantes.
3. Admin confirma.
4. Backend valida campos.
5. Backend crea torneo con estado Pendiente.
6. Backend responde con resumen del torneo.

### Flujos alternos

A1. Campos obligatorios vacios:
- Backend responde 400 con detalle.

A2. Numero de participantes invalido:
- Backend responde 400 (minimo 2, maximo definido por el equipo).

A3. Error de BD:
- Backend responde 500 sin crear torneo.

### Reglas de negocio y validaciones

- Estado inicial: Pendiente.
- Tipo de eliminacion valido (simple, doble, liga, segun definicion del equipo).
- Duracion por ronda > 0.

### Datos y entidades afectadas

- Torneo: id, nombre, tipo_eliminacion, duracion_ronda, participantes_max, estado, created_at.
- LogAuditoria: actor_id, accion, entidad, timestamp.

### Endpoints y contratos

- POST /tournaments
  - Request:
    - nombre: string
    - tipo_eliminacion: string
    - duracion_ronda_min: int
    - participantes_max: int
  - Response 201:
    - id, nombre, estado, opciones_siguientes
  - Response 400:
    - error: "validation_error"
    - details: ["..." ]

- GET /tournaments/{id}
  - Response 200:
    - id, nombre, estado, metadata

### UI/UX (criterios)

- Maximo 2 pasos de UI para completar creacion.
- Resumen visible al finalizar con acciones siguientes.

### Requisitos no funcionales y seguridad

- Solo rol administrador puede crear torneos.
- Respuesta rapida en entorno local.

### Errores complejos y casos borde

- Torneo con nombre duplicado: definir si se permite o se bloquea.
- Duracion de ronda extremadamente alta: definir limites.

### Dependencias e integraciones

- No depende de APIs externas.
- Puede necesitar validacion contra reglas internas de formato de torneo.

### Metricas y analitica

- Torneos creados por periodo.
- Tiempo promedio de creacion (formulario a confirmacion).

### Pruebas minimas

- Given admin autenticado, When POST /tournaments valido, Then 201.
- Given campo faltante, When POST, Then 400.
- Given participantes_max invalido, When POST, Then 400.
- Given error de BD, When POST, Then 500 y no crea torneo.

## 7. Dependencias generales

- FastAPI, SQLAlchemy, Alembic.
- bcrypt para contrasenas.
- Scheduler interno para alertas.

## 8. Checklist de entrega personal

- Casos de uso implementados segun reglas y flujos.
- Endpoints documentados y probados.
- Pruebas minimas en pytest.
- Registros de auditoria habilitados.

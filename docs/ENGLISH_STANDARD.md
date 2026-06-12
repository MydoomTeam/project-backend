# Estándar de idioma para el proyecto

## Objetivo
Mantener consistencia técnica en el código fuente.

La programación debe realizarse en inglés, mientras que los textos orientados al usuario final pueden permanecer en español.

---

## Debe estar en inglés

Todo elemento que forme parte directamente del código o de la estructura técnica:

### Estructura del proyecto
- nombres de archivos,
- nombres de carpetas,
- nombres de módulos,
- nombres de paquetes.

### Código fuente
- nombres de clases,
- nombres de funciones,
- nombres de métodos,
- nombres de variables,
- nombres de constantes,
- nombres de enumeraciones,
- nombres de interfaces,
- nombres de excepciones personalizadas.

### API
- rutas REST,
- nombres de endpoints,
- parámetros de ruta,
- parámetros de consulta,
- nombres internos de DTOs,
- nombres internos de schemas.

### Base de datos
- nombres de tablas nuevas,
- nombres de columnas nuevas,
- nombres de relaciones,
- nombres de entidades ORM.

### Testing
- nombres de archivos de test,
- nombres de funciones de test,
- nombres de fixtures.

---

## Puede permanecer en español

Todo texto cuyo propósito sea ser leído por usuarios o por el equipo.

### Interfaz y negocio
- mensajes mostrados al usuario,
- descripciones funcionales,
- nombres de torneos,
- nombres de jugadores,
- nombres de alertas,
- títulos de pantallas,
- contenido de respuestas funcionales.

### Documentación del equipo
- archivos README,
- documentación funcional,
- documentación académica,
- documentación de entrega.

### Logs y depuración
Los mensajes de log pueden estar en español o inglés.

La prioridad es que sean claros y consistentes para el equipo.

### Comentarios y docstrings
Pueden estar en español o inglés.

Se recomienda consistencia con el idioma que use el equipo.

---

## Prohibido

- nombres de funciones en español,
- nombres de variables en español,
- nombres de clases en español,
- nombres de archivos en español,
- mezcla de idiomas en identificadores técnicos,
- rutas REST en español.

---

## Política para la API

Las rutas deben estar en inglés.

Si una ruta en español ya existe y cambiarla afecta compatibilidad, el cambio debe evaluarse antes de aplicarse para evitar romper contratos.

---

## Convenciones de nombres

### Variables y funciones
snake_case en inglés.

### Clases
PascalCase en inglés.

### Constantes
UPPER_SNAKE_CASE en inglés.

### Tests
nombres descriptivos en inglés.

---

## Regla de migración

Si existe código en español:

1. traducir identificadores técnicos al inglés,
2. mantener el texto visible para el usuario si no existe una razón funcional para cambiarlo,
3. mantener el comportamiento actual,
4. actualizar referencias relacionadas para evitar errores.

---

## Regla de validación

Después de cualquier migración:

- verificar imports,
- verificar referencias cruzadas,
- ejecutar pruebas,
- actualizar documentación técnica afectada,
- verificar que las rutas sigan funcionando,
- verificar que no se haya modificado el comportamiento funcional.

---

## Regla de simplicidad

No realizar cambios únicamente por razones estéticas.

Toda traducción o refactor debe aportar:
- consistencia,
- claridad,
- mantenibilidad,
- o cumplimiento de estándares del proyecto.
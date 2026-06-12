# Proceso de revisión

## Regla de herramienta
Usar Claude Code en terminal para el análisis completo y el flujo de refactor.

Usar Claude dentro de VS Code solo para revisar diffs concretos después de cada lote de cambios.

## Orden obligatorio

### Fase 1: Inventario del proyecto
- Leer todos los documentos de contexto.
- Inspeccionar la estructura del repositorio.
- Detectar capas reales.
- Detectar conceptos duplicados.
- Detectar archivos activos y archivos de legado.
- No modificar archivos.

### Fase 2: Mapa de dependencias
- Identificar qué importa a qué.
- Detectar archivos vivos.
- Detectar archivos no usados.
- Detectar duplicación real de conceptos.
- Detectar módulos candidatos a consolidación.
- No modificar archivos.

### Fase 3: Revisión de arquitectura
- Verificar límites entre capas.
- Detectar violaciones cruzadas.
- Detectar dependencias circulares.
- Detectar lógica de negocio en controllers o repositories.
- No modificar archivos.

### Fase 4: Revisión REST
- Verificar rutas, métodos HTTP, payloads, headers y códigos de estado.
- No modificar archivos.

### Fase 5: Revisión Clean Code
- Verificar nombres, tamaño de funciones, responsabilidad de clases, duplicación, control de flujo y estructura.
- No modificar archivos.

### Fase 6: Refactor por capas
Refactorizar en este orden:
1. controllers
2. services
3. repositories
4. domain
5. core
6. models y schemas
7. tasks
8. tests

### Fase 7: Migración al inglés
- Traducir primero identificadores técnicos activos.
- Traducir rutas solo si el cambio fue aprobado.
- Mantener textos visibles para usuario si deben permanecer en español.
- Mantener cada lote pequeño.

### Fase 8: Validación
- Ejecutar tests.
- Verificar que el comportamiento se conserva.
- Verificar que no se introducen nuevas violaciones arquitectónicas.

## Reglas de salida
Toda revisión debe devolver:
- rutas exactas,
- símbolos o endpoints exactos,
- problema,
- impacto,
- corrección mínima,
- riesgo.

## Regla global de seguridad
Nunca resolver un problema agregando complejidad innecesaria.
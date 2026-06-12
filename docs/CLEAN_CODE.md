# Estándar Clean Code

## Propósito
Detectar y eliminar código difícil de leer, mantener o extender.

## Reglas de nombres
- Los nombres deben revelar intención.
- Usar solo inglés.
- Evitar nombres genéricos como data, temp, aux, foo, bar, x, y.
- Evitar nombres engañosos.
- Las funciones booleanas deben leerse como preguntas cuando tenga sentido.

## Reglas de funciones
- Mantener funciones pequeñas.
- Una función debe hacer una sola cosa.
- Preferir funciones de unas 20 líneas o menos cuando sea posible.
- Evitar demasiados parámetros.
- Preferir como máximo 3 parámetros salvo justificación real.
- Evitar argumentos bandera.
- Evitar mezclar niveles de abstracción en la misma función.
- Preferir retornos tempranos.
- Evitar anidación profunda.
- Evitar cadenas largas de if/elif cuando exista una estructura más clara.

## Reglas de clases
- Una clase debe tener una sola responsabilidad.
- Evitar clases gigantes.
- Evitar clases que solo agrupan lógica no relacionada.

## Reglas de comentarios
- No comentar lo obvio.
- No usar comentarios para tapar mal diseño.
- Eliminar código comentado.
- Mantener solo comentarios que aporten valor real.

## Reglas de duplicación
- No duplicar lógica.
- No duplicar validaciones.
- No duplicar mapeos si un helper claro lo resuelve.

## Reglas de estructura
- Mantener cerca los conceptos relacionados.
- Mantener archivos razonablemente pequeños.
- Organizar por responsabilidad y claridad.
- No crear capas o abstracciones extra sin necesidad real.

## Regla de simplicidad
Preferir la solución más simple que funcione.

## Regla de mejora
Cada cambio debe dejar el código mejor de lo que estaba.

## Criterios de error
Reportar:
- funciones largas,
- clases grandes,
- lógica duplicada,
- nombres sin sentido,
- nesting excesivo,
- comentarios innecesarios,
- flujo confuso,
- complejidad accidental,
- soluciones sobreingenierizadas.
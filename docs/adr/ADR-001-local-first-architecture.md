# ADR-001 Local-first architecture

## Estado
Aceptada

## Contexto
La herramienta debe ser local, trazable, versionable y orientada a cálculo estructural con documentos autorizados por el usuario.

El núcleo del sistema requiere:
- persistencia controlada por proyecto
- solver determinista cercano al modelo de dominio
- posibilidad de crecer a una interfaz visual rica

## Decisión
Se adopta una arquitectura local-first con núcleo Python para:
- modelo de dominio
- servicios de árbol
- persistencia inicial
- motor documental inicial
- solver determinista

La capa visual queda desacoplada para una iteración posterior.

## Consecuencias

### Positivas
- rapidez de arranque
- alta trazabilidad
- facilidad para modelar cálculo técnico
- control fino de persistencia y versionado

### Negativas
- la UI visual completa queda para un bloque posterior
- se requiere definir una futura interfaz de escritorio desacoplada

## Próximo paso derivado
Implementar servicios de proyecto, árbol y documentos sobre el núcleo Python antes de diseñar la interfaz visual final.

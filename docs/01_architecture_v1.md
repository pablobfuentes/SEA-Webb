# Arquitectura funcional v1

## Núcleo conceptual

La unidad principal del sistema es el árbol vivo de decisión y cálculo del problema.

Todos los demás módulos existen para alimentar, explicar, validar o exportar el contenido del árbol.

## Módulos nucleares

### 1. Gestión documental autoritativa
Responsabilidad:
- almacenar documentos aprobados por el usuario
- extraer texto y metadatos
- indexar fragmentos
- versionar documentos

### 2. Recuperación documental con citas
Responsabilidad:
- buscar únicamente dentro del corpus autorizado
- priorizar normativa activa
- devolver fragmentos con metadatos suficientes para citación inmediata

### 3. Árbol de decisiones y cálculo
Responsabilidad:
- representar problemas, bifurcaciones, hipótesis, cálculos y comprobaciones
- conservar rutas descartadas
- permitir reactivación de ramas

### 4. Solver determinista
Responsabilidad:
- ejecutar cálculos técnicos verificables
- validar unidades
- registrar fórmulas y sustituciones

### 5. Motor didáctico
Responsabilidad:
- explicar decisiones y procedimientos
- traducir criterios técnicos a una narrativa comprensible
- adaptar profundidad según perfil de usuario

### 6. Canvas interactivo
Responsabilidad:
- visualizar el árbol del problema
- permitir navegación, comparación y reactivación de ramas

### 7. Chat orientado a tareas
Responsabilidad:
- consultar norma
- proponer bifurcaciones
- explicar nodos
- solicitar datos faltantes
- nunca sustituir al árbol como estructura principal

### 8. Wiki enlazada
Responsabilidad:
- conectar procedimientos, conceptos, fórmulas y ejemplos
- vincular artículos con nodos y fragmentos documentales

### 9. Gestión de proyectos y versiones
Responsabilidad:
- encapsular documentos autorizados, árbol, cálculos, supuestos y reportes
- permitir recuperar revisiones anteriores

### 10. Reportes y auditoría
Responsabilidad:
- exportar decisiones, cálculos, referencias y comparativas
- reconstruir el estado técnico de una revisión del proyecto

## Flujo principal de usuario

1. Crear proyecto
2. Definir normativa activa, idioma y unidades
3. Cargar corpus autorizado
4. Plantear problema inicial
5. Generar primer abanico de alternativas
6. Seleccionar una rama principal
7. Expandir subdecisiones, hipótesis y cálculos
8. Comparar alternativas activas o descartadas
9. Reabrir rutas previas si cambia el criterio técnico
10. Exportar reporte

## Flujos secundarios

- consulta puntual de norma desde un nodo
- apertura de artículo relacionado en la wiki
- clonación de una rama para explorar variante
- archivado y reactivación de ramas
- cambio de profundidad didáctica

## Responsabilidades por capa lógica

### Capa documental
- ingestión
- segmentación
- indexación
- citación
- control de conflicto entre ediciones

### Capa de dominio
- proyecto
- nodo
- rama
- decisión
- alternativa
- cálculo
- comprobación

### Capa de servicio
- creación de proyectos
- expansión del árbol
- consulta documental
- evaluación y comparación de alternativas
- generación de reportes

### Capa de interfaz
- canvas
- panel de detalle técnico
- chat
- visor documental
- comparador

## Arquitectura técnica inicial propuesta

### Decisión base
Arquitectura local-first con núcleo Python para dominio, persistencia y cálculo.

### Justificación
- permite implementar rápido el núcleo técnico
- facilita solver determinista, manejo de unidades y trazabilidad
- deja abierta la futura conexión con frontend de escritorio más visual

### Estructura técnica v1
- backend local en Python
- persistencia inicial en JSON versionable por proyecto
- esquemas explícitos para entidades críticas
- futura capa visual desacoplada del dominio

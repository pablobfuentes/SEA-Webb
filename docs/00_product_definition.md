# Definición del producto v1

## Propósito exacto del sistema

La herramienta será una aplicación local de diseño estructural guiado por árbol de decisiones.

El árbol del problema es la entidad principal del producto. El chat, la wiki, el canvas y el solver son módulos de soporte al árbol.

La aplicación debe servir simultáneamente para:

- trabajo profesional con trazabilidad técnica
- aprendizaje guiado del razonamiento estructural

La aplicación debe operar exclusivamente sobre documentos autorizados por el usuario dentro del proyecto activo.

## Principios no negociables

1. Separación estricta de responsabilidades
   - motor documental: encuentra evidencia
   - motor de cálculo: produce resultados numéricos verificables
   - motor didáctico: explica y contextualiza
   - árbol: organiza el problema y sus bifurcaciones

2. Prohibición de respuestas técnicas sin evidencia trazable
   - toda afirmación técnica debe abrir su referencia documental
   - toda fórmula aplicada debe vincularse a una fuente

3. Prohibición de resultados finales críticos generados solo por el LLM
   - el LLM propone, organiza, explica y redacta
   - el solver determinista ejecuta las operaciones críticas

4. Trazabilidad completa
   - datos de entrada
   - hipótesis
   - fórmulas
   - sustituciones
   - resultados parciales
   - comprobaciones
   - referencias

5. Control de versiones obligatorio
   - proyecto
   - documento
   - cálculo
   - reporte
   - decisión de rama

6. Coherencia total de unidades
   - validación dimensional
   - conversiones registradas
   - sistema de unidades por proyecto

## Alcance de la primera versión

El MVP queda limitado al dominio inicial controlado:

- comparación y desarrollo de vigas de acero para claros simples

Alternativas mínimas contempladas:

- viga laminada convencional
- viga armada de alma llena
- viga alveolar
- celosía

Capacidades mínimas del MVP:

- crear proyecto local
- cargar corpus documental autorizado
- plantear problema inicial
- generar primer abanico de alternativas
- conservar ramas descartadas
- reactivar ramas previas
- registrar hipótesis y cálculos
- comparar alternativas en criterios homogéneos
- generar reporte básico exportable

## Criterios de éxito del producto

El producto se considera bien orientado si permite que:

1. un usuario plantee un problema y desarrolle un árbol completo sin perder trazabilidad
2. cada afirmación técnica abra su fuente documental
3. dos ramas puedan compararse con criterios homogéneos
4. un estudiante siga el razonamiento paso a paso
5. un ingeniero reabra una ruta descartada y recalcule desde allí

## Restricciones iniciales

- operación local sin dependencia obligatoria de nube
- corpus inicial en PDF autorizado por el usuario
- marco normativo activo por proyecto
- referencias fuera del marco activo solo como complemento
- crecimiento modular sin romper trazabilidad histórica

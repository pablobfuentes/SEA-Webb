# Structural Tree App Foundation · SEA Webb

Base ejecutable de la herramienta local de diseño estructural guiado por árbol de decisiones. Proyecto **SEA Webb**; en GitHub el repositorio suele llamarse `SEA-Webb` (sin espacios en la URL).

## Objetivo de esta entrega

Esta primera entrega ejecuta los primeros bloques del PBS:

- Definición del producto y reglas rectoras
- Arquitectura funcional general
- Inicio del modelo de datos maestro
- Esqueleto inicial del núcleo backend

## Block 2 — Flujo de ejecución (orden estricto)

La implementación de Block 2 sigue los prompts en `cursor_prompts/` **en este orden**:

| Paso | Archivo |
|------|---------|
| 1 | `02_repo_workflow_and_governance_prompt.txt` |
| 2 | `03_project_persistence_prompt.txt` |
| 3 | `04_tree_expansion_and_state_prompt.txt` |
| 4 | `05_document_ingestion_prompt.txt` |
| 5 | `06_document_retrieval_and_citation_prompt.txt` |
| 6 | `07_branch_comparison_v1_prompt.txt` |
| 7 | `08_validation_and_integration_prompt.txt` |

- Plan maestro: `docs/04_block_2_implementation_plan.md`
- Estado: `docs/implementation/BLOCK_2_STATUS.md`
- Pruebas: `docs/TEST_STRATEGY.md`
- Contribución y reglas: `CONTRIBUTING.md`

**Block 2 (M1–M7)** está cerrado en este repositorio: persistencia, árbol, ingesta, recuperación con `CitationPayload`, comparación de ramas v1, y **validación integrada** (`08`). Informe: `docs/05_block_2_validation_report.md`.

## Contenido

- `docs/00_product_definition.md`: definición del producto y principios no negociables
- `docs/01_architecture_v1.md`: arquitectura funcional y flujo principal de usuario
- `docs/02_master_data_model.md`: modelo de datos maestro v1
- `docs/03_mvp_scope.md`: alcance del MVP inicial
- `docs/adr/ADR-001-local-first-architecture.md`: decisión arquitectónica principal
- `schemas/`: esquemas JSON iniciales para entidades críticas
- `src/structural_tree_app/`: núcleo Python local para proyectos, árbol y documentos
- `examples/`: proyecto semilla de ejemplo

## Decisiones base implementadas

- Arquitectura local-first
- Separación entre motor documental, árbol, solver y capa didáctica
- Persistencia versionable en JSON para el núcleo inicial
- Dominio inicial controlado: vigas de acero para claros simples
- Árbol de decisiones como entidad principal del sistema

## Desarrollo local

- Python 3.11+
- Instalación editable (recomendado): `pip install -e ".[dev]"` desde la raíz del repo (incluye `pytest`).
- O bien: `set PYTHONPATH=src` (Windows) / `export PYTHONPATH=src` (Unix) y ejecutar módulos con `python -m structural_tree_app.main` según evolucione el paquete

### Layout en disco (proyecto)

Cada proyecto vive en `workspace/{project_id}/`:

- `project.json` — identidad y punteros del dominio `Project` (`branch_ids`, `root_node_id`, `version_ids`, `head_revision_id`, `active_code_context`, …); no contiene el árbol completo
- `assumptions.json` — lista validada de hipótesis
- `tree/branches|nodes|decisions|alternatives/*.json` — entidades del árbol (una rama/nodo/decisión/alternativa por archivo)
- `revisions/{revision_id}/meta.json`, `project_snapshot.json`, `assumptions_snapshot.json`, `tree/` — copia inmutable del estado técnico en ese punto
- `documents/{document_id}/document.json` + `fragments.json` — corpus registrado e fragmentos para citas (M4)
- `exports/` — reservado para hitos posteriores

Comprobación rápida de importación:

```bash
make import-check
```

Tests:

```bash
python -m pytest tests/ -q
```

(En Windows sin Make: ver `CONTRIBUTING.md`.)

## Cómo usar esta base

1. Revisar documentos en `docs/`
2. Revisar modelos de dominio en `src/structural_tree_app/domain/`
3. Revisar servicios base en `src/structural_tree_app/services/`
4. Revisar ejemplo de proyecto en `examples/example_project.json`

## Block 2 — Recorrido realista (API local)

Flujo mínimo coherente con los tests de integración (`tests/test_block2_integration.py`):

1. **Crear workspace y proyecto:** `ProjectService(workspace_root).create_project(...)` → se escribe `workspace/{project_id}/project.json` y una revisión inicial.
2. **Árbol:** `TreeWorkspace(service, project)` → `create_root_problem` (varias ramas), nodos hijos (`CRITERION`, etc.).
3. **Ingesta:** `DocumentIngestionService(service, project_id).ingest_local_file(path, ...)` → `documents/{document_id}/`.
4. **Corpus normativo:** `approve_document` y `activate_for_normative_corpus` para que la búsqueda normativa vea el documento.
5. **Recuperación:** `DocumentRetrievalService(service, project_id).search(query, citation_authority="normative_active_primary")` → hits con carga de cita estructurada (**vía autoritativa** para evidencia en texto).
6. **Revisión (opcional, estado congelado):** `create_revision(project_id, rationale)` → snapshot bajo `revisions/{revision_id}/`.
7. **Comparación de ramas:** `BranchComparisonService.for_live(service, project_id).compare_branches([id1, id2])` o `for_revision_snapshot(..., revision_id)` para repetir la comparación desde el snapshot. Las trazas `citation_traces` con `ids_only` son **solo trazas internas**; las citas para usuario siguen siendo las de **retrieval**.

Validación completa Block 2: `docs/05_block_2_validation_report.md`.

## Siguiente bloque lógico de implementación

- **Block 3 / UI** y vistas del árbol: fase posterior (no incluida en Block 2).
- Mejoras de producto pospuestas explícitamente: ver `docs/05_block_2_validation_report.md` §2(c) y `docs/CHANGELOG.md`.

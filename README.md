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
- `tree/branches|nodes|decisions|alternatives|calculations|checks|references/*.json` — entidades del árbol y registros técnicos vinculados a nodos (Block 3 M2+)
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

### Block 4A — Workbench (validación UI)

Requiere extras: `pip install -e ".[dev,workbench]"`.

#### Primera vez (Windows)

1. Abrir PowerShell en la raíz del repo (`structural_tree_app_foundation/`).
2. Crear entorno e instalar en modo editable:
   - `python -m venv .venv`
   - `.\.venv\Scripts\Activate.ps1`
   - `pip install -e ".[dev,workbench]"`

#### Arranque diario (mínima fricción, Windows)

- **Recomendado:** doble clic en `run_workbench.bat` en la raíz del repo, **o** en PowerShell: `.\scripts\run_workbench.ps1`
- El launcher usa **solo** `.\.venv\Scripts\python.exe` (no mezcla con Python global). Si falta `.venv` o el paquete no importa, muestra un mensaje claro y sale con error.
- Por defecto define `STRUCTURAL_TREE_WORKSPACE` a `<repo>\workspace` si no estaba definida, crea esa carpeta si hace falta, y tras ~2 s abre el navegador en `http://127.0.0.1:8000/workbench`.
- En consola se imprimen las URLs del **hub** y de **`/health`** (comprobación rápida).

Opciones del script:

| Opción | Efecto |
|--------|--------|
| `-Reload` | Activa recarga automática (`WORKBENCH_RELOAD=1` → `uvicorn` **reload** al cambiar código). |
| `-NoBrowser` | No abre el navegador (útil en CI o si el puerto ya está en uso). |
| `-Port N` | Fija `WORKBENCH_PORT` (por defecto 8000). |

Ejemplos: `.\scripts\run_workbench.ps1 -Reload` · `run_workbench.bat -Reload`

#### Arranque manual (sin launcher)

```bash
python -m structural_tree_app.workbench
```

Mismo módulo que usa el launcher; útil si ya tienes el venv activado y variables a mano.

#### Si el navegador muestra «connection failed» / no carga

- El servidor **no está en marcha** hasta que la ventana donde ejecutaste el launcher siga abierta y **uvicorn** esté escuchando. Sin ese proceso, `http://127.0.0.1:8000` no responde.
- Comprueba `http://127.0.0.1:8000/health` (debe devolver JSON con `"status":"ok"`). Si falla, revisa la consola del launcher (traceback, puerto ocupado, import roto).
- Asegúrate de haber hecho `pip install -e ".[dev,workbench]"` **dentro de** `.venv`.

**U3 (opcional):** síntesis acotada de `answer_text` con modelo local — activar con `STRUCTURAL_LOCAL_MODEL_ENABLED=1` y, por petición, el checkbox en chat/evidencia; `STRUCTURAL_LOCAL_MODEL_PROVIDER=stub` (determinista, sin red) o `unavailable` (pruebas de fallback). La recuperación gobernada y las citas no las genera el modelo.

Por defecto escucha en `http://127.0.0.1:8000` — rutas `GET /health`, `GET /workbench` (hub de proyecto), **`GET|POST /workbench/project/chat`** (U2: superficie principal de asistente; mismo `LocalAssistOrchestrator` que el panel de evidencia U1), `GET|POST /workbench/project/workflow` (M3: setup del flujo vano simple; M4: inspección de alternativas; **M5:** `POST /workbench/project/workflow/materialize`, `POST /workbench/project/workflow/m5-run`; **M6:** `POST /workbench/project/workflow/compare`, `POST /workbench/project/workflow/revision-create`, y `GET /workbench/project/workflow?rev=<revision_id>` para comparación en snapshot de revisión); **U1:** `GET|POST /workbench/project/evidence`, vista de cita bajo `/workbench/project/evidence/fragment/...` (texto del fragmento + archivo original verificado por hash cuando aplica) y `GET /workbench/project/evidence/source/{document_id}/file` para incrustar PDF/texto; **G1.5/U0:** `GET /workbench/project/corpus` (subida de corpus, proyección gobernada), `POST /workbench/project/corpus/upload`, detalle y acciones bajo `/workbench/project/corpus/...`. Variable `STRUCTURAL_TREE_WORKSPACE` define la raíz del workspace JSON (mismo contrato que `ProjectService`); el launcher la fija por defecto a `workspace/` bajo el repo; puedes sobreescribirla antes de ejecutar. `WORKBENCH_SESSION_SECRET` opcional para cookies de sesión. Ver `docs/09_block_4a_implementation_plan.md`.

**Block 3 M3 — flujo a vano simple (miembro de acero primario):** `SimpleSpanSteelWorkflowService.setup_initial_workflow` en `structural_tree_app.services.simple_span_steel_workflow` crea el nodo raíz, la primera decisión y alternativas persistidas (véase `docs/implementation/BLOCK_3_STATUS.md`).

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

- **Block 3** (vertical simple-span acero) está **cerrado** en este repositorio como línea base — `docs/implementation/BLOCK_3_STATUS.md`, `docs/08_block_3_validation_report.md`.
- **Block 4A** (planificación): **workbench frontend mínimo** para validar el flujo Block 3 por UI local — **no** es la UI final del producto. Plan: `docs/09_block_4a_implementation_plan.md`, criterios: `docs/10_block_4a_acceptance_snapshot.md`, estado: `docs/implementation/BLOCK_4A_STATUS.md`.
- Mejoras de producto pospuestas explícitamente: ver `docs/05_block_2_validation_report.md` §2(c) y `docs/CHANGELOG.md`.

# Modelo de datos maestro v1

## Entidades principales

- Project
- Document
- DocumentFragment
- ActiveCodeContext
- Node
- Branch
- Decision
- Alternative
- Assumption
- Variable
- UnitValue
- Calculation
- Check
- Reference
- Report
- VersionRecord

## Project

Campos mínimos:
- id
- name
- description
- status
- language
- unit_system
- active_code_context
- authorized_document_ids
- root_node_id
- branch_ids
- version_ids
- created_at
- updated_at

## ActiveCodeContext

Campos mínimos:
- primary_standard_family
- active_standard_ids
- complementary_standard_ids
- allowed_document_ids
- conflict_policy

## Document

Campos mínimos:
- id
- title
- author
- edition
- version_label
- publication_year
- document_type
- authority_level
- topics
- language
- file_path
- content_hash
- created_at

## DocumentFragment

Campos mínimos:
- id
- document_id
- chapter
- section
- page_start
- page_end
- fragment_type
- topic_tags
- authority_level
- text
- sibling_fragment_ids
- linked_fragment_ids

## Node

Campos mínimos:
- id
- project_id
- branch_id
- node_type
- title
- description
- parent_node_id
- child_node_ids
- state
- order_index
- depth
- linked_reference_ids
- linked_calculation_ids
- linked_assumption_ids
- created_at
- updated_at

## Branch

Campos mínimos:
- id
- project_id
- origin_decision_node_id
- title
- description
- state
- root_node_id
- parent_branch_id
- cloned_from_branch_id
- reactivated_from_branch_id
- comparison_tags
- created_at
- updated_at

## Decision

Campos mínimos:
- id
- project_id
- decision_node_id
- prompt
- criterion_ids
- alternative_ids
- selected_alternative_id
- status
- rationale
- created_at
- updated_at

## Alternative

Campos mínimos:
- id
- decision_id
- title
- description
- pros
- cons
- constraints
- next_expected_decisions
- status
- reactivatable

## Assumption

Campos mínimos:
- id
- project_id
- node_id
- label
- value
- unit
- source_type
- confidence
- rationale
- created_at

## Variable y UnitValue

Campos mínimos:
- name
- canonical_name
- value
- unit
- source
- converted_from
- conversion_factor
- confidence

## Calculation

Campos mínimos:
- id
- project_id
- node_id
- objective
n- method_label
- formula_id
- formula_text
- inputs
- substitutions
- result
- dimensional_validation
- reference_ids
- status
- created_at
- updated_at

## Check

Campos mínimos:
- id
- project_id
- node_id
- calculation_id
- check_type
- demand
- capacity
- utilization_ratio
- status
- message
- reference_ids

## Reference

Campos mínimos:
- id
- project_id
- document_id
- fragment_id
- usage_type
- citation_short
- citation_long
- quoted_context

## Report

Campos mínimos:
- id
- project_id
- title
- report_type
- included_branch_ids
- included_node_ids
- included_calculation_ids
- included_reference_ids
- export_path
- version_id
- created_at

## VersionRecord

Campos mínimos:
- id
- entity_type
- entity_id
- project_id
- change_type
- snapshot_path
- rationale
- created_at

## Relaciones críticas

1. Project contiene Branch y define ActiveCodeContext
2. Branch contiene Node
3. Decision vive sobre un Node de tipo decision
4. Alternative pertenece a Decision
5. Calculation y Check se vinculan a Node
6. Reference vincula Node y Calculation con DocumentFragment
7. Report referencia conjuntos de ramas, nodos, cálculos y referencias

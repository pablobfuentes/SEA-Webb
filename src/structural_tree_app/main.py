from __future__ import annotations

import json

from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.tree_workspace import TreeWorkspace


def bootstrap_example(workspace: str = "./workspace") -> dict:
    project_service = ProjectService(workspace)

    project = project_service.create_project(
        name="Proyecto ejemplo - claro simple 15 m",
        description="Exploración inicial de alternativas para elemento principal entre columnas.",
        language="es",
        unit_system="SI",
        primary_standard_family="AISC",
    )

    tw = TreeWorkspace(project_service, project)
    branch, root = tw.create_root_problem(
        title="Resolver elemento principal entre columnas con L = 15 m",
        description="Comparar y desarrollar tipologías viables dentro del marco documental activo.",
    )

    payload = {
        "project_id": project.id,
        "root_branch_id": branch.id,
        "root_node_id": root.id,
        "message": "Bootstrap completado",
    }
    return payload


if __name__ == "__main__":
    result = bootstrap_example()
    print(json.dumps(result, indent=2, ensure_ascii=False))

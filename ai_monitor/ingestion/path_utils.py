from pathlib import PurePath


def derive_project_name(project_path: str | None) -> str:
    if not project_path:
        return "unknown"

    name = PurePath(project_path).name
    return name or "unknown"

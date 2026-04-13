from pathlib import PurePath


def derive_project_name(project_path: str | None) -> str:
    if not project_path:
        return "unknown"

    path = PurePath(project_path)
    segments = [segment for segment in path.parts if segment not in {path.anchor, ""}]

    if not segments:
        return "unknown"

    dev_worktree_name = _match_dev_worktrees_project(segments)
    if dev_worktree_name is not None:
        return dev_worktree_name

    nested_worktree_name = _match_nested_worktree_project(segments)
    if nested_worktree_name is not None:
        return nested_worktree_name

    name = path.name
    return name or "unknown"


def _match_dev_worktrees_project(segments: list[str]) -> str | None:
    for index in range(len(segments) - 3):
        if segments[index] == "dev" and segments[index + 1] == "worktrees":
            return segments[index + 2]
    return None


def _match_nested_worktree_project(segments: list[str]) -> str | None:
    try:
        claude_index = segments.index(".claude")
    except ValueError:
        claude_index = -1

    if claude_index >= 1 and claude_index + 2 < len(segments):
        if segments[claude_index + 1] == "worktrees":
            return segments[claude_index - 1]

    try:
        dot_worktrees_index = segments.index(".worktrees")
    except ValueError:
        dot_worktrees_index = -1

    if dot_worktrees_index >= 1 and dot_worktrees_index + 1 < len(segments):
        return segments[dot_worktrees_index - 1]
    return None

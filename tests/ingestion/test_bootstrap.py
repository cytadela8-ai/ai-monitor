from pathlib import Path


def test_project_bootstrap_files_exist() -> None:
    required = [
        "pyproject.toml",
        ".gitignore",
        "README.md",
        "DEV.md",
        "ai_monitor/__init__.py",
    ]

    missing = [path for path in required if not Path(path).exists()]
    assert missing == []

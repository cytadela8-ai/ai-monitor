from ai_monitor.ingestion.path_utils import derive_project_name


def test_project_name_uses_path_basename() -> None:
    assert derive_project_name("/home/ubuntu/zk-chains-registry") == "zk-chains-registry"


def test_project_name_handles_empty_path() -> None:
    assert derive_project_name(None) == "unknown"


def test_project_name_handles_root_like_values() -> None:
    assert derive_project_name("/") == "unknown"

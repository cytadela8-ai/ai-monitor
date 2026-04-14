from fastapi.testclient import TestClient


def test_dashboard_renders_summary_labels(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    body = response.text
    assert "Conversations" in body
    assert "Text Prompts" in body
    assert "Slash Cmds" in body
    assert "Day" in body
    assert "Week" in body
    assert "Month" in body


def test_dashboard_handles_fresh_database(fresh_client: TestClient) -> None:
    response = fresh_client.get("/")

    assert response.status_code == 200


def test_dashboard_does_not_bootstrap_data_on_first_render(fresh_client: TestClient) -> None:
    response = fresh_client.get("/")

    assert response.status_code == 200

    metrics_response = fresh_client.get("/api/metrics", params={"period": "day"})
    payload = metrics_response.json()

    assert payload["refresh"] is None
    assert payload["rows"] == []


def test_dashboard_exposes_accessible_controls_and_table_context(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    body = response.text
    assert 'aria-pressed="true"' in body
    assert 'aria-pressed="false"' in body
    assert "<caption>" in body
    assert 'id="heatmap-summary"' in body
    assert 'class="toolbar panel"' in body
    assert 'class="summary-chip summary-chip--conversations"' in body
    assert 'aria-live="polite"' in body
    assert 'role="status"' in body
    assert 'class="metrics-table"' in body
    assert 'data-last-refresh="' in body
    assert 'id="heatmap-grid"' in body
    assert 'id="heatmap-hover-detail"' in body
    assert "Ledger Grouping" in body
    assert "This changes the ledger rows below, not the totals." in body
    assert 'static/vendor/chart.' not in body
    assert 'class="diagnostics-shell"' in body
    assert 'id="project-quick-picks"' in body
    assert 'id="machine-filter"' in body


def test_fresh_dashboard_marks_cache_as_missing(fresh_client: TestClient) -> None:
    response = fresh_client.get("/")

    assert response.status_code == 200
    assert 'data-last-refresh=""' in response.text


def test_favicon_ico_is_served(client: TestClient) -> None:
    response = client.get("/favicon.ico")

    assert response.status_code == 200


def test_favicon_ico_supports_head_requests(client: TestClient) -> None:
    response = client.head("/favicon.ico")

    assert response.status_code == 200

from fastapi.testclient import TestClient

from ai_monitor.config import AppConfig


def test_dashboard_renders_login_form_when_signed_out(
    unauthenticated_client: TestClient,
) -> None:
    response = unauthenticated_client.get("/")

    assert response.status_code == 200
    assert "Sign In" in response.text
    assert 'id="login-form"' in response.text
    assert "AI Monitor" in response.text


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
    assert 'id="sign-out-button"' in body
    assert 'id="machine-admin-list"' in body
    assert 'id="machine-create-form"' in body
    assert 'id="machine-setup-panel"' in body
    assert 'data-client-image="ghcr.io/cytadela8-ai/ai-monitor-client:latest"' in body
    assert "Machine Access" in body


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


def test_login_persists_session_for_follow_up_requests(
    unauthenticated_client: TestClient,
    app_config: AppConfig,
) -> None:
    login_response = unauthenticated_client.post(
        "/api/session/login",
        json={"admin_key": app_config.admin_key},
    )

    assert login_response.status_code == 200

    dashboard_response = unauthenticated_client.get("/")
    metrics_response = unauthenticated_client.get("/api/metrics", params={"period": "day"})

    assert dashboard_response.status_code == 200
    assert "Project Usage Ledger" in dashboard_response.text
    assert metrics_response.status_code == 200


def test_login_rejects_wrong_admin_key(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.post(
        "/api/session/login",
        json={"admin_key": "wrong-key"},
    )

    assert response.status_code == 401

    metrics_response = unauthenticated_client.get("/api/metrics", params={"period": "day"})
    assert metrics_response.status_code == 401

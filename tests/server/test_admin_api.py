from fastapi.testclient import TestClient


def test_admin_machine_endpoints_require_session(
    unauthenticated_client: TestClient,
) -> None:
    list_response = unauthenticated_client.get("/api/admin/machines")
    create_response = unauthenticated_client.post(
        "/api/admin/machines",
        json={"label": "work-laptop"},
    )

    assert list_response.status_code == 401
    assert create_response.status_code == 401


def test_admin_can_create_and_revoke_machine_keys(client: TestClient) -> None:
    create_response = client.post(
        "/api/admin/machines",
        json={"label": "work-laptop"},
    )

    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["machine"]["label"] == "work-laptop"
    assert payload["machine"]["is_local"] is False
    assert payload["api_key"]
    assert payload["setup"]["client_image"] == "ghcr.io/cytadela8-ai/ai-monitor-client:latest"
    assert "docker run --pull always --rm" in payload["setup"]["docker_command"]
    assert 'AI_MONITOR_API_KEY="aim_' in payload["setup"]["launch_script"]
    assert 'AI_MONITOR_SERVER_URL="http://testserver"' in payload["setup"]["launch_script"]

    list_response = client.get("/api/admin/machines")

    assert list_response.status_code == 200
    machines = list_response.json()["machines"]
    labels = [payload["machine"]["label"] for payload in machines]
    assert labels == ["main-server", "work-laptop"]
    remote_machine = next(
        payload for payload in machines if payload["machine"]["label"] == "work-laptop"
    )
    assert "<hidden: revoke and recreate to replace>" in remote_machine["setup"]["launch_script"]

    revoke_response = client.post(
        f"/api/admin/machines/{payload['machine']['id']}/revoke",
    )

    assert revoke_response.status_code == 200
    assert revoke_response.json()["machine"]["is_active"] is False


def test_logout_blocks_follow_up_admin_requests(client: TestClient) -> None:
    logout_response = client.post("/api/session/logout")

    assert logout_response.status_code == 200

    machines_response = client.get("/api/admin/machines")
    metrics_response = client.get("/api/metrics", params={"period": "day"})

    assert machines_response.status_code == 401
    assert metrics_response.status_code == 401

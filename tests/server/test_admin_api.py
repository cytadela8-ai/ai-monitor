from fastapi.testclient import TestClient


def test_admin_machine_endpoints_require_bootstrap_auth(client: TestClient) -> None:
    list_response = client.get("/api/admin/machines")
    create_response = client.post("/api/admin/machines", json={"label": "work-laptop"})

    assert list_response.status_code == 401
    assert create_response.status_code == 401


def test_admin_can_create_and_revoke_machine_keys(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/admin/machines",
        headers=admin_headers,
        json={"label": "work-laptop"},
    )

    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["machine"]["label"] == "work-laptop"
    assert payload["machine"]["is_local"] is False
    assert payload["api_key"]

    list_response = client.get("/api/admin/machines", headers=admin_headers)

    assert list_response.status_code == 200
    labels = [machine["label"] for machine in list_response.json()["machines"]]
    assert labels == ["main-server", "work-laptop"]

    revoke_response = client.post(
        f"/api/admin/machines/{payload['machine']['id']}/revoke",
        headers=admin_headers,
    )

    assert revoke_response.status_code == 200
    assert revoke_response.json()["machine"]["is_active"] is False

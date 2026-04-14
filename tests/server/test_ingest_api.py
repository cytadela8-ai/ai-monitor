from fastapi.testclient import TestClient


def test_snapshot_ingest_requires_machine_auth(client: TestClient) -> None:
    response = client.post("/api/ingest/snapshot", json={})

    assert response.status_code == 401


def test_snapshot_ingest_replaces_only_authenticated_machine_slice(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/admin/machines",
        headers=admin_headers,
        json={"label": "work-laptop"},
    )
    api_key = create_response.json()["api_key"]
    machine_headers = {"Authorization": f"Bearer {api_key}"}

    first_response = client.post(
        "/api/ingest/snapshot",
        headers=machine_headers,
        json={
            "generated_at": "2026-04-02T10:00:00+00:00",
            "providers": ["claude"],
            "conversations": [
                {
                    "provider": "claude",
                    "external_id": "remote-session-1",
                    "started_at": "2026-04-02T09:00:00+00:00",
                    "project_path": "/work/remote-alpha",
                    "project_name": "remote-alpha",
                }
            ],
            "prompt_events": [
                {
                    "provider": "claude",
                    "external_conversation_id": "remote-session-1",
                    "occurred_at": "2026-04-02T09:05:00+00:00",
                    "project_path": "/work/remote-alpha",
                    "project_name": "remote-alpha",
                    "event_type": "text_prompt",
                    "raw_text": "remote prompt",
                }
            ],
        },
    )

    assert first_response.status_code == 200

    remote_metrics = client.get(
        "/api/metrics",
        params={"period": "day", "machine": "work-laptop"},
    ).json()
    local_metrics = client.get(
        "/api/metrics",
        params={"period": "day", "machine": "main-server"},
    ).json()

    assert {row["project_name"] for row in remote_metrics["rows"]} == {"remote-alpha"}
    assert any(row["project_name"] == "zk-chains-registry" for row in local_metrics["rows"])

    second_response = client.post(
        "/api/ingest/snapshot",
        headers=machine_headers,
        json={
            "generated_at": "2026-04-03T10:00:00+00:00",
            "providers": ["claude"],
            "conversations": [
                {
                    "provider": "claude",
                    "external_id": "remote-session-2",
                    "started_at": "2026-04-03T09:00:00+00:00",
                    "project_path": "/work/remote-beta",
                    "project_name": "remote-beta",
                }
            ],
            "prompt_events": [
                {
                    "provider": "claude",
                    "external_conversation_id": "remote-session-2",
                    "occurred_at": "2026-04-03T09:05:00+00:00",
                    "project_path": "/work/remote-beta",
                    "project_name": "remote-beta",
                    "event_type": "slash_command",
                    "raw_text": "/sync",
                }
            ],
        },
    )

    assert second_response.status_code == 200

    replaced_metrics = client.get(
        "/api/metrics",
        params={"period": "day", "machine": "work-laptop"},
    ).json()

    assert {row["project_name"] for row in replaced_metrics["rows"]} == {"remote-beta"}

from fastapi.testclient import TestClient


def test_metrics_endpoint_returns_selected_period_data(client: TestClient) -> None:
    response = client.get("/api/metrics", params={"period": "week"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["period"] == "week"
    assert "rows" in payload


def test_refresh_endpoint_returns_refresh_report(client: TestClient) -> None:
    response = client.post("/api/refresh")

    assert response.status_code == 200
    assert "last_refreshed_at" in response.json()


def test_refresh_then_query_returns_fixture_metrics(client: TestClient) -> None:
    refresh_response = client.post("/api/refresh")
    assert refresh_response.status_code == 200

    metrics_response = client.get("/api/metrics", params={"period": "day"})
    payload = metrics_response.json()

    assert payload["refresh"]["provider_count"] == 2
    assert any(row["project_name"] == "zk-chains-registry" for row in payload["rows"])


def test_metrics_endpoint_bootstraps_data_on_first_request(fresh_client: TestClient) -> None:
    response = fresh_client.get("/api/metrics", params={"period": "day"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["refresh"]["provider_count"] == 2
    assert payload["rows"]

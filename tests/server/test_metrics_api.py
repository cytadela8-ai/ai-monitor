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

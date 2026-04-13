from fastapi.testclient import TestClient


def test_metrics_endpoint_returns_selected_period_data(client: TestClient) -> None:
    response = client.get("/api/metrics", params={"period": "week"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["period"] == "week"
    assert "rows" in payload
    assert "projects" in payload
    assert "summary" in payload
    assert "heatmap_days" in payload


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


def test_metrics_rows_are_sorted_newest_first(client: TestClient) -> None:
    response = client.get("/api/metrics", params={"period": "day"})

    assert response.status_code == 200
    rows = response.json()["rows"]
    assert rows == sorted(rows, key=lambda row: row["period_start"], reverse=True)


def test_metrics_endpoint_returns_ranked_project_options(client: TestClient) -> None:
    response = client.get("/api/metrics", params={"period": "day"})

    assert response.status_code == 200
    projects = response.json()["projects"]
    assert projects[0]["project_name"] == "zk-chains-registry"
    assert [project["project_name"] for project in projects] == [
        "zk-chains-registry",
        "zksync-prividium",
    ]
    assert all("total_events" in project for project in projects)


def test_metrics_endpoint_returns_empty_payload_before_first_refresh(
    fresh_client: TestClient,
) -> None:
    response = fresh_client.get("/api/metrics", params={"period": "day"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["refresh"] is None
    assert payload["rows"] == []
    assert payload["summary"] == {
        "conversation_count": 0,
        "text_prompt_count": 0,
        "slash_command_count": 0,
    }
    assert payload["heatmap_days"] == []


def test_metrics_summary_stays_fixed_when_only_grouping_changes(
    client: TestClient,
) -> None:
    day_payload = client.get("/api/metrics", params={"period": "day"}).json()
    week_payload = client.get("/api/metrics", params={"period": "week"}).json()
    month_payload = client.get("/api/metrics", params={"period": "month"}).json()

    expected_summary = {
        "conversation_count": 3,
        "text_prompt_count": 3,
        "slash_command_count": 2,
    }

    assert day_payload["summary"] == expected_summary
    assert week_payload["summary"] == expected_summary
    assert month_payload["summary"] == expected_summary


def test_metrics_endpoint_returns_daily_heatmap_series(client: TestClient) -> None:
    payload = client.get("/api/metrics", params={"period": "day"}).json()

    assert payload["heatmap_days"]
    assert {
        "day": "2026-03-27",
        "conversation_count": 3,
        "text_prompt_count": 3,
        "slash_command_count": 2,
        "total_events": 5,
    } in payload["heatmap_days"]

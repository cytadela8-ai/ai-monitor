from fastapi.testclient import TestClient


def test_dashboard_renders_summary_labels(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    body = response.text
    assert "Conversations" in body
    assert "Text Prompts" in body
    assert "Slash Commands" in body
    assert "Day" in body
    assert "Week" in body
    assert "Month" in body

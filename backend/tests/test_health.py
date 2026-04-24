def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["app"] == "Forgent"
    assert payload["version"] == "1.0.0"

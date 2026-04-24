def test_root_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "Welcome to Forgent API"
    assert payload["docs"] == "/docs"

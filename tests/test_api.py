from fastapi.testclient import TestClient

from api import create_app


def test_health() -> None:
    app = create_app(runner=lambda prompt: "ok", agent_mode="single", model="test-model")
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert data["mode"] == "single"
    assert data["model"] == "test-model"


def test_chat() -> None:
    def fake_runner(prompt: str) -> str:
        return f"echo:{prompt}"

    app = create_app(runner=fake_runner, agent_mode="multi", model="test-model")
    client = TestClient(app)

    response = client.post("/chat", json={"prompt": "hi"})
    assert response.status_code == 200
    data = response.json()

    assert data["response"] == "echo:hi"
    assert data["mode"] == "multi"

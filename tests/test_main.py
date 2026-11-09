
from fastapi.testclient import TestClient

import app.main as main_module

from app.main import app
from app.models import TestCaseResponse


client = TestClient(app)


def test_home():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "Application is running"


def test_generate_test_cases(monkeypatch):

    def fake_generate(requirement):
        return TestCaseResponse(
            requirement=requirement,
            test_cases=[],
            assumptions=[]
        )

    monkeypatch.setattr(
        main_module,
        "create_test_cases",
        fake_generate
    )

    response = client.post(
        "/generate-test-cases",
        json={
            "requirement": "Users should be able to login"
        }
    )

    assert response.status_code == 200
    assert response.json()["requirement"] == "Users should be able to login"


def test_invalid_requirement():

    response = client.post(
        "/generate-test-cases",
        json={
            "requirement": "Login"
        }
    )

    assert response.status_code == 422

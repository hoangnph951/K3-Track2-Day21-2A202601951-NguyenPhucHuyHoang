from fastapi.testclient import TestClient

from src.serve import app


class FakeModel:
    def predict(self, features):
        assert features.shape == (1, 12)
        return [2]


def test_health_and_predict_endpoints():
    previous_model = app.state.model
    app.state.model = FakeModel()
    try:
        with TestClient(app) as client:
            health_response = client.get("/health")
            assert health_response.status_code == 200
            assert health_response.json() == {"status": "ok"}

            predict_response = client.post(
                "/predict",
                json={"features": [1.0] * 12},
            )
            assert predict_response.status_code == 200
            assert predict_response.json() == {"prediction": 2, "label": "cao"}
    finally:
        app.state.model = previous_model


def test_predict_rejects_invalid_feature_count():
    previous_model = app.state.model
    app.state.model = FakeModel()
    try:
        with TestClient(app) as client:
            response = client.post("/predict", json={"features": [1.0, 2.0]})
            assert response.status_code == 400
            assert response.json()["detail"] == "Expected 12 features (wine quality)"
    finally:
        app.state.model = previous_model

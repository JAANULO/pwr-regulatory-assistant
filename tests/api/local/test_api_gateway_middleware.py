import pytest
from flask import Flask, jsonify, g
from api_gateway.middleware import init_api_key_middleware


class MockApiService:
    def validate_key(self, api_key, scope):
        if api_key == "good_key":
            return True, "OK", {"key_id": "123"}
        elif api_key == "rate_limited":
            return False, "Rate limit exceeded", {"status_code": 429}
        else:
            return False, "Invalid key", {"status_code": 401}


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True

    service = MockApiService()
    init_api_key_middleware(app, service, protected_routes=["/zapytaj"])

    @app.route("/zapytaj")
    def zapytaj():
        meta = getattr(g, "api_key_meta", {})
        return jsonify({"success": True, "key_id": meta.get("key_id")})

    @app.route("/otwarte")
    def otwarte():
        return jsonify({"success": True})

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_unprotected_route(client):
    response = client.get("/otwarte")
    assert response.status_code == 200


def test_protected_route_missing_key(client):
    response = client.get("/zapytaj")
    assert response.status_code == 401
    assert b"Missing API Key" in response.data


def test_protected_route_good_key(client):
    response = client.get("/zapytaj", headers={"X-Api-Key": "good_key"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["key_id"] == "123"


def test_protected_route_bad_key(client):
    response = client.get("/zapytaj", headers={"X-Api-Key": "bad_key"})
    assert response.status_code == 401
    assert b"Invalid key" in response.data


def test_protected_route_rate_limited(client):
    response = client.get("/zapytaj", headers={"X-Api-Key": "rate_limited"})
    assert response.status_code == 429
    assert b"Rate limit exceeded" in response.data

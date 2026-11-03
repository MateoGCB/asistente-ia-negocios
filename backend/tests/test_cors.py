"""CORS: only explicitly listed frontend origins may call the API from a browser. Never "*"."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from main import configure_cors, parse_cors_origins

DEFAULT_ORIGIN = "http://localhost:5173"
OTHER_ORIGIN = "http://sitio-ajeno.example.com"


def preflight(client, origin: str, method: str = "PATCH"):
    # What a browser sends before a cross-origin request with a JSON body and a token
    return client.options(
        "/businesses/",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        },
    )


def app_with_cors_env(monkeypatch, value: str | None) -> TestClient:
    # A tiny app configured exactly like main.py, but with another CORS_ORIGINS value
    if value is None:
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
    else:
        monkeypatch.setenv("CORS_ORIGINS", value)
    app = FastAPI()
    configure_cors(app)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    return TestClient(app)


def allowed_origin(response) -> str | None:
    return response.headers.get("access-control-allow-origin")


# ---------------------------------------------------------------- the real app (default origin)

def test_preflight_from_the_default_origin_is_allowed(client):
    response = preflight(client, DEFAULT_ORIGIN)

    assert response.status_code == 200
    assert allowed_origin(response) == DEFAULT_ORIGIN
    methods = {m.strip() for m in response.headers["access-control-allow-methods"].split(",")}
    assert methods == {"GET", "POST", "PATCH", "DELETE", "OPTIONS"}
    headers = {h.strip().lower() for h in response.headers["access-control-allow-headers"].split(",")}
    assert {"authorization", "content-type"} <= headers
    # No cookies: the token travels in the Authorization header
    assert "access-control-allow-credentials" not in response.headers


def test_simple_request_from_the_default_origin_gets_the_header(client):
    response = client.get("/public/no-existe/menu", headers={"Origin": DEFAULT_ORIGIN})

    assert allowed_origin(response) == DEFAULT_ORIGIN


def test_origin_not_listed_does_not_get_the_header(client):
    assert allowed_origin(preflight(client, OTHER_ORIGIN)) is None
    assert allowed_origin(client.get("/public/no-existe/menu", headers={"Origin": OTHER_ORIGIN})) is None


@pytest.mark.parametrize("method", ["PUT", "TRACE"])
def test_methods_not_listed_are_rejected_in_preflight(client, method):
    response = preflight(client, DEFAULT_ORIGIN, method=method)

    assert response.status_code == 400


# ---------------------------------------------------------------- CORS_ORIGINS variable

def test_two_configured_origins_are_both_allowed(monkeypatch):
    client = app_with_cors_env(monkeypatch, " https://panel.example.com , http://localhost:3000 ")

    for origin in ("https://panel.example.com", "http://localhost:3000"):
        assert allowed_origin(client.get("/ping", headers={"Origin": origin})) == origin
    # The default is replaced, not added
    assert allowed_origin(client.get("/ping", headers={"Origin": DEFAULT_ORIGIN})) is None


@pytest.mark.parametrize("value", [None, "", "   ", " , ,, ", "*", " * , "], ids=["missing", "empty", "spaces", "commas", "star", "star_and_commas"])
def test_empty_or_useless_variable_falls_back_to_the_default(monkeypatch, value):
    client = app_with_cors_env(monkeypatch, value)

    assert allowed_origin(client.get("/ping", headers={"Origin": DEFAULT_ORIGIN})) == DEFAULT_ORIGIN
    assert allowed_origin(client.get("/ping", headers={"Origin": OTHER_ORIGIN})) is None


def test_a_star_mixed_with_real_origins_is_ignored(monkeypatch):
    client = app_with_cors_env(monkeypatch, "*, https://panel.example.com")

    assert allowed_origin(client.get("/ping", headers={"Origin": "https://panel.example.com"})) == "https://panel.example.com"
    assert allowed_origin(client.get("/ping", headers={"Origin": OTHER_ORIGIN})) is None


@pytest.mark.parametrize("value", ["*", "*, https://panel.example.com", "", "https://panel.example.com"])
def test_star_never_appears_in_any_response(monkeypatch, value):
    client = app_with_cors_env(monkeypatch, value)

    for origin in (DEFAULT_ORIGIN, OTHER_ORIGIN, "https://panel.example.com", "null"):
        assert allowed_origin(client.get("/ping", headers={"Origin": origin})) != "*"


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("https://a.example.com,https://b.example.com", ["https://a.example.com", "https://b.example.com"]),
        ("  https://a.example.com  ", ["https://a.example.com"]),
        (",,https://a.example.com,,", ["https://a.example.com"]),
        ("", ["http://localhost:5173"]),
        (None, ["http://localhost:5173"]),
        ("*", ["http://localhost:5173"]),
    ],
)
def test_parse_cors_origins(raw, expected):
    assert parse_cors_origins(raw) == expected

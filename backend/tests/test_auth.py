from datetime import timedelta

import pytest
from jose import jwt

import security
from tests.conftest import TEST_PASSWORD
from utils.datetime_utils import utc_now

# A sample of protected endpoints from different routers: auth is checked the same way in all of them
PROTECTED_ENDPOINTS = [
    ("get", "/businesses/"),
    ("post", "/menus/"),
    ("get", "/businesses/1/orders"),
]


def sign(payload: dict, key: str = security.SECRET_KEY) -> str:
    # Builds a token by hand, signed like the real ones, to test one broken property at a time
    return jwt.encode(payload, key, algorithm=security.ALGORITHM)


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------- register

def test_register_returns_201_with_public_fields_only(client):
    body = {"name": "Usuario Nuevo", "email": "nuevo@example.com", "password": TEST_PASSWORD}
    response = client.post("/auth/register", json=body)

    assert response.status_code == 201
    data = response.json()
    # Exactly the User schema: never the password nor its hash
    assert set(data) == {"id", "name", "email"}
    assert data["email"] == "nuevo@example.com"
    assert data["name"] == "Usuario Nuevo"


def test_register_stores_a_hash_not_the_plain_password(client, db_session):
    from models.user_models import User_db

    client.post("/auth/register", json={"name": "Usuario", "email": "hash@example.com", "password": TEST_PASSWORD})

    stored = db_session.query(User_db).filter(User_db.email == "hash@example.com").one()
    assert stored.hashed_password != TEST_PASSWORD
    assert security.pwd_context.verify(TEST_PASSWORD, stored.hashed_password)


def test_register_with_existing_email_returns_409(client, user_a):
    body = {"name": "Otra persona", "email": user_a.email, "password": "otra-clave-456"}
    response = client.post("/auth/register", json=body)

    assert response.status_code == 409


# ---------------------------------------------------------------- login

def test_login_returns_a_bearer_token_for_that_user(client, user_a):
    response = client.post("/auth/login", json={"email": user_a.email, "password": user_a.password})

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    payload = jwt.decode(data["access_token"], security.SECRET_KEY, algorithms=[security.ALGORITHM])
    assert payload["sub"] == user_a.email
    # And the token actually opens a protected endpoint
    assert client.get("/businesses/", headers=bearer(data["access_token"])).status_code == 200


def test_wrong_password_and_unknown_email_give_the_same_401(client, user_a):
    # Same status AND same body: the API must not reveal which emails are registered
    wrong_password = client.post("/auth/login", json={"email": user_a.email, "password": "clave-incorrecta"})
    unknown_email = client.post("/auth/login", json={"email": "nadie@example.com", "password": user_a.password})

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


# ---------------------------------------------------------------- protected endpoints

@pytest.mark.parametrize("method, url", PROTECTED_ENDPOINTS)
def test_protected_endpoint_without_token_returns_401(client, method, url):
    response = client.request(method, url, json={"name": "x"})

    assert response.status_code == 401


def _bad_tokens(user_email: str) -> dict[str, str]:
    now = utc_now()
    return {
        "garbage": "esto-no-es-un-jwt",
        "expired": sign({"sub": user_email, "exp": now - timedelta(minutes=1)}),
        "without_sub": sign({"exp": now + timedelta(minutes=30)}),
        "wrong_signature": sign({"sub": user_email, "exp": now + timedelta(minutes=30)}, key="otra-clave-cualquiera"),
        # Valid signature, but the user does not exist (e.g. a deleted account)
        "unknown_user": sign({"sub": "fantasma@example.com", "exp": now + timedelta(minutes=30)}),
    }


@pytest.mark.parametrize("method, url", PROTECTED_ENDPOINTS)
@pytest.mark.parametrize("case", ["garbage", "expired", "without_sub", "wrong_signature", "unknown_user"])
def test_protected_endpoint_with_bad_token_returns_generic_401(client, user_a, method, url, case):
    token = _bad_tokens(user_a.email)[case]
    response = client.request(method, url, json={"name": "x"}, headers=bearer(token))

    assert response.status_code == 401
    # Generic message: it does not say WHY the token was rejected
    assert response.json() == {"detail": "Could not validate credentials"}

"""Register/login: emails validated and normalized to lowercase, password rules ONLY on register."""
import pytest

import security
from models.user_models import User_db

VALID_PASSWORD = "clave-segura-123"


def register(client, email: str, password: str = VALID_PASSWORD, name: str = "Persona Prueba"):
    return client.post("/auth/register", json={"name": name, "email": email, "password": password})


def login(client, email: str, password: str = VALID_PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def bearer(response) -> dict:
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# ---------------------------------------------------------------- emails

def test_register_stores_the_email_in_lowercase(client, db_session):
    response = register(client, "Mateo@Example.com")

    assert response.status_code == 201
    assert response.json()["email"] == "mateo@example.com"
    assert db_session.query(User_db).one().email == "mateo@example.com"


def test_spaces_around_the_email_are_removed(client):
    assert register(client, "  Persona@Example.com  ").json()["email"] == "persona@example.com"


@pytest.mark.parametrize("second", ["mateo@example.com", "MATEO@EXAMPLE.COM", " mateo@Example.COM "])
def test_same_email_with_other_capitals_is_409(client, db_session, second):
    register(client, "Mateo@Example.com")

    assert register(client, second).status_code == 409
    assert db_session.query(User_db).count() == 1


@pytest.mark.parametrize("typed", ["mateo@example.com", "MATEO@EXAMPLE.COM", "Mateo@Example.Com", "  mAtEo@eXaMpLe.cOm "])
def test_login_works_with_any_capitalization(client, typed):
    register(client, "Mateo@Example.com")

    response = login(client, typed)

    assert response.status_code == 200
    assert client.get("/businesses/", headers=bearer(response)).status_code == 200


@pytest.mark.parametrize("email", ["no-es-un-email", "persona@", "@example.com", "per sona@example.com", "", "persona@@example.com"])
def test_invalid_email_returns_422_on_register_and_login(client, db_session, email):
    assert register(client, email).status_code == 422
    assert login(client, email).status_code == 422
    assert db_session.query(User_db).count() == 0


def test_legacy_user_with_capitals_in_the_db_can_still_log_in(client, db_session):
    # A row saved before emails were normalized (inserted by hand, skipping the API)
    db_session.add(User_db(name="Usuario Viejo", email="Legacy.User@Example.com", hashed_password=security.pwd_context.hash(VALID_PASSWORD)))
    db_session.commit()

    response = login(client, "legacy.user@example.com")

    assert response.status_code == 200
    # The token's "sub" is the email as stored (with capitals): it must still identify the user
    assert client.get("/businesses/", headers=bearer(response)).status_code == 200
    # And nobody can register the same address in lowercase
    assert register(client, "legacy.user@example.com").status_code == 409


# ---------------------------------------------------------------- password rules (register only)

@pytest.mark.parametrize(
    "password",
    [
        "abcdef1",              # 7 characters
        "abcdefgh",             # 8, without a number
        "12345678",             # 8, without a letter
        "a1" + "x" * 71,        # 73 bytes
        "1" + "ñ" * 39,         # only 40 characters, but 79 bytes: bytes are counted, not characters
    ],
    ids=["7_chars", "no_number", "no_letter", "73_bytes", "40_chars_79_bytes"],
)
def test_invalid_password_on_register_returns_422_and_saves_nothing(client, db_session, password):
    response = register(client, "persona@example.com", password=password)

    assert response.status_code == 422
    assert db_session.query(User_db).count() == 0


@pytest.mark.parametrize(
    "password",
    [
        "abcdefg1",             # exactly 8
        "a1" + "x" * 70,        # exactly 72 bytes
        "ñ" * 35 + "a1",        # 37 characters, exactly 72 bytes
    ],
    ids=["8_chars", "72_bytes_ascii", "72_bytes_with_accents"],
)
def test_valid_password_on_register_returns_201_and_can_log_in(client, password):
    assert len(password.encode("utf-8")) <= 72

    assert register(client, "persona@example.com", password=password).status_code == 201
    assert login(client, "persona@example.com", password=password).status_code == 200


def test_byte_lengths_used_in_these_tests():
    # Written by hand so the cases above really test what their names say
    assert len(("a1" + "x" * 70).encode("utf-8")) == 72
    assert len(("a1" + "x" * 71).encode("utf-8")) == 73
    assert len("1" + "ñ" * 39) == 40 and len(("1" + "ñ" * 39).encode("utf-8")) == 79
    assert len(("ñ" * 35 + "a1").encode("utf-8")) == 72


@pytest.mark.parametrize("password", ["123", "abcdefgh", "", "a1" + "x" * 80])
def test_login_never_applies_password_rules(client, password):
    # A password that would be invalid on register is just a wrong password on login: 401, not 422
    register(client, "persona@example.com")

    response = login(client, "persona@example.com", password=password)

    assert response.status_code == 401
    assert response.json() == login(client, "nadie@example.com").json()  # same generic body


# ---------------------------------------------------------------- name (register)

@pytest.mark.parametrize(
    "sent, saved",
    [("Ana", "Ana"), ("  Ana María  ", "Ana María"), ("x", "x"), ("x" * 100, "x" * 100)],
    ids=["valid", "spaces_around", "1_char", "100_chars"],
)
def test_valid_name_is_saved_without_surrounding_spaces(client, db_session, sent, saved):
    response = register(client, "persona@example.com", name=sent)

    assert response.status_code == 201
    assert response.json()["name"] == saved
    assert db_session.query(User_db).one().name == saved


@pytest.mark.parametrize("name", ["", "    ", "x" * 101], ids=["empty", "only_spaces", "101_chars"])
def test_invalid_name_returns_422_and_saves_nothing(client, db_session, name):
    assert register(client, "persona@example.com", name=name).status_code == 422
    assert db_session.query(User_db).count() == 0


def test_password_spaces_are_kept(client):
    # Only the name is stripped: spaces in a password are part of it
    register(client, "persona@example.com", password="  clave 123  ")

    assert login(client, "persona@example.com", password="  clave 123  ").status_code == 200
    assert login(client, "persona@example.com", password="clave 123").status_code == 401

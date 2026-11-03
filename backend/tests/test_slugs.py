import pytest

from models.business_models import Business_db
from services import business_services


@pytest.mark.parametrize(
    "name, expected_slug",
    [
        ("Pizzería Popular Centro", "pizzeria-popular-centro"),  # accents removed
        ("LA ESQUINA", "la-esquina"),                            # lowercase
        ("Café  del   Sol", "cafe-del-sol"),                     # several spaces -> one hyphen
        ("  Bordes con espacios  ", "bordes-con-espacios"),      # no hyphens at the ends
        ("Bar & Grill #1!", "bar-grill-1"),                      # symbols -> one hyphen
        ("Ñandú Año 2024", "nandu-ano-2024"),                    # ñ -> n
        ("Sushi 🍣 Express", "sushi-express"),                   # emojis dropped
        ("¡¡¡!!!", "sucursal"),                                  # only symbols -> fallback
        ("🍕🍕🍕", "sucursal"),                                  # only emojis -> fallback
    ],
)
def test_slug_is_generated_from_the_name(user_a, create_business, name, expected_slug):
    assert create_business(user_a, name=name)["slug"] == expected_slug


def test_slug_is_unique_across_users(user_a, user_b, create_business):
    # Slugs are public URLs: unique in the whole platform, not per owner
    first = create_business(user_a, name="La Esquina")
    second = create_business(user_b, name="La Esquina")
    third = create_business(user_a, name="la esquina!")

    assert [first["slug"], second["slug"], third["slug"]] == ["la-esquina", "la-esquina-2", "la-esquina-3"]


def test_slug_does_not_change_when_the_business_is_renamed(client, user_a, create_business):
    created = create_business(user_a, name="Nombre Original")

    renamed = client.patch(f"/businesses/{created['id']}", json={"name": "Otro Nombre"}, headers=user_a.headers).json()

    assert renamed["name"] == "Otro Nombre"
    assert renamed["slug"] == "nombre-original"


def test_renamed_business_keeps_its_old_slug_taken(user_a, client, create_business):
    # After the rename, the old name's slug still belongs to the first business
    created = create_business(user_a, name="Nombre Original")
    client.patch(f"/businesses/{created['id']}", json={"name": "Otro Nombre"}, headers=user_a.headers)

    assert create_business(user_a, name="Nombre Original")["slug"] == "nombre-original-2"


# ---------------------------------------------------------------- retry on collision
# Simulates a race: another request saved the same slug AFTER we computed it but BEFORE our INSERT.
# We fake it by making generate_unique_slug return a slug that is already taken.

def test_slug_collision_once_is_retried_and_gets_a_suffix(client, user_a, create_business, monkeypatch):
    create_business(user_a, name="La Esquina")  # "la-esquina" is taken
    real_generator = business_services.generate_unique_slug
    calls = []

    def stale_then_real(name, db):
        calls.append(name)
        return "la-esquina" if len(calls) == 1 else real_generator(name, db)

    monkeypatch.setattr(business_services, "generate_unique_slug", stale_then_real)

    response = client.post("/businesses/", json={"name": "La Esquina", "industry": "gastronomia"}, headers=user_a.headers)

    assert response.status_code == 201
    assert response.json()["slug"] == "la-esquina-2"
    assert len(calls) == 2


def test_slug_collision_twice_returns_409_and_saves_nothing(client, user_a, create_business, db_session, monkeypatch):
    create_business(user_a, name="La Esquina")
    monkeypatch.setattr(business_services, "generate_unique_slug", lambda name, db: "la-esquina")

    response = client.post("/businesses/", json={"name": "La Esquina", "industry": "gastronomia"}, headers=user_a.headers)

    assert response.status_code == 409
    assert db_session.query(Business_db).count() == 1

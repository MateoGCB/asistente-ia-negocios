"""DELETE /businesses/{id} archives (soft delete): the row stays with deleted_at set,
and the API treats the business as if it did not exist."""
from datetime import timedelta, timezone

import pytest

from models.business_models import Business_db
from models.order_models import Order_db
from utils.datetime_utils import utc_now


def archive(client, user, business_id):
    return client.delete(f"/businesses/{business_id}", headers=user.headers)


def test_archive_returns_200_with_message(client, user_a, create_business):
    created = create_business(user_a)

    response = archive(client, user_a, created["id"])

    assert response.status_code == 200
    assert response.json() == {"message": "Business archived successfully"}


def test_archived_business_disappears_from_the_list(client, user_a, create_business):
    kept = create_business(user_a, name="Se Queda")
    archived = create_business(user_a, name="Se Archiva")

    archive(client, user_a, archived["id"])

    assert [b["id"] for b in client.get("/businesses/", headers=user_a.headers).json()] == [kept["id"]]


@pytest.mark.parametrize(
    "method, body",
    [("get", None), ("patch", {"name": "Nuevo"}), ("delete", None)],  # delete = archiving twice
)
def test_archived_business_answers_404(client, user_a, create_business, method, body):
    created = create_business(user_a)
    archive(client, user_a, created["id"])

    response = client.request(method, f"/businesses/{created['id']}", json=body, headers=user_a.headers)

    assert response.status_code == 404


def test_b_cannot_archive_a_business_of_a(client, user_a, user_b, create_business, db_session):
    created = create_business(user_a)

    assert archive(client, user_b, created["id"]).status_code == 404
    assert db_session.get(Business_db, created["id"]).deleted_at is None
    assert client.get(f"/businesses/{created['id']}", headers=user_a.headers).status_code == 200


def test_archived_row_stays_with_deleted_at_in_utc(client, user_a, create_business, db_session):
    created = create_business(user_a)
    before = utc_now()

    archive(client, user_a, created["id"])

    stored = db_session.get(Business_db, created["id"])
    assert stored is not None  # not physically deleted
    # UTCDateTime returns an AWARE datetime in UTC (SQLite alone would return it naive)
    assert stored.deleted_at.tzinfo == timezone.utc
    assert before - timedelta(seconds=1) <= stored.deleted_at <= utc_now() + timedelta(seconds=1)


def test_orders_of_an_archived_business_are_kept(client, shop, place_order, db_session):
    item_id = shop.items[0]["id"]
    assert place_order(shop.business["slug"], [(item_id, 1)]).status_code == 201
    assert place_order(shop.business["slug"], [(item_id, 2)]).status_code == 201

    archive(client, shop.owner, shop.business["id"])

    assert db_session.query(Order_db).filter(Order_db.business_id == shop.business["id"]).count() == 2


def test_archived_slug_is_never_reused(client, user_a, user_b, create_business):
    created = create_business(user_a, name="La Esquina")
    archive(client, user_a, created["id"])

    # Neither the same owner nor another one gets the old public URL
    assert create_business(user_a, name="La Esquina")["slug"] == "la-esquina-2"
    assert create_business(user_b, name="La Esquina")["slug"] == "la-esquina-3"


def test_archiving_a_branch_does_not_affect_another_with_the_same_menu(client, shop, create_business, assign_menu, place_order):
    other = create_business(shop.owner, name="Otra Sucursal")
    assign_menu(shop.owner, other["id"], shop.menu["id"])

    archive(client, shop.owner, shop.business["id"])

    # The archived branch is gone from the public side...
    assert client.get(f"/public/{shop.business['slug']}/menu").status_code == 404
    # ...but the other branch still shows the shared menu and accepts orders
    public_menu = client.get(f"/public/{other['slug']}/menu")
    assert public_menu.status_code == 200
    assert len(public_menu.json()["items"]) == len(shop.items)
    assert place_order(other["slug"], [(shop.items[0]["id"], 1)]).status_code == 201
    assert client.get(f"/businesses/{other['id']}", headers=shop.owner.headers).json()["menu_id"] == shop.menu["id"]


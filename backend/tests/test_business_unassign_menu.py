"""DELETE /businesses/{business_id}/menu: detaches the menu from ONE branch (the menu itself is kept)."""
from models.business_models import Business_db
from models.menu_models import Menu_db


def unassign(client, user, business_id):
    return client.delete(f"/businesses/{business_id}/menu", headers=user.headers)


def test_unassign_leaves_menu_id_null_and_keeps_the_menu(client, shop, db_session):
    response = unassign(client, shop.owner, shop.business["id"])

    assert response.status_code == 200
    assert response.json() == {"message": "Menu removed from business"}
    assert client.get(f"/businesses/{shop.business['id']}", headers=shop.owner.headers).json()["menu_id"] is None
    assert db_session.get(Menu_db, shop.menu["id"]) is not None
    assert len(client.get(f"/menus/{shop.menu['id']}/items", headers=shop.owner.headers).json()) == 2


def test_unassign_twice_is_still_200(client, shop):
    assert unassign(client, shop.owner, shop.business["id"]).status_code == 200
    assert unassign(client, shop.owner, shop.business["id"]).status_code == 200


def test_business_without_menu_from_the_start_returns_200(client, user_a, create_business):
    business = create_business(user_a)

    assert unassign(client, user_a, business["id"]).status_code == 200


def test_foreign_business_returns_404_and_is_not_changed(client, shop, user_b, db_session):
    foreign = unassign(client, user_b, shop.business["id"])
    unknown = unassign(client, user_b, 9999)

    assert foreign.status_code == unknown.status_code == 404
    assert foreign.json() == unknown.json()
    db_session.expire_all()
    assert db_session.get(Business_db, shop.business["id"]).menu_id == shop.menu["id"]


def test_archived_business_returns_404(client, shop, db_session):
    client.delete(f"/businesses/{shop.business['id']}", headers=shop.owner.headers)

    assert unassign(client, shop.owner, shop.business["id"]).status_code == 404
    db_session.expire_all()
    assert db_session.get(Business_db, shop.business["id"]).menu_id == shop.menu["id"]  # untouched


def test_other_branch_sharing_the_menu_is_not_affected(client, shop, create_business, assign_menu):
    other = create_business(shop.owner, name="Otra Sucursal")
    assign_menu(shop.owner, other["id"], shop.menu["id"])

    unassign(client, shop.owner, shop.business["id"])

    assert client.get(f"/businesses/{other['id']}", headers=shop.owner.headers).json()["menu_id"] == shop.menu["id"]
    assert client.get(f"/public/{other['slug']}/menu").status_code == 200


def test_public_menu_of_that_branch_becomes_the_usual_404(client, shop):
    assert client.get(f"/public/{shop.business['slug']}/menu").status_code == 200
    reference = client.get("/public/este-slug-no-existe/menu")

    unassign(client, shop.owner, shop.business["id"])

    response = client.get(f"/public/{shop.business['slug']}/menu")
    assert response.status_code == 404
    assert response.json() == reference.json()


def test_patch_with_menu_id_null_is_still_ignored(client, shop):
    # The only way to remove the menu is the new DELETE: PATCH keeps ignoring nulls
    response = client.patch(f"/businesses/{shop.business['id']}", json={"menu_id": None}, headers=shop.owner.headers)

    assert response.status_code == 200
    assert response.json()["menu_id"] == shop.menu["id"]


def test_unassign_without_token_returns_401(client, shop):
    assert client.delete(f"/businesses/{shop.business['id']}/menu").status_code == 401

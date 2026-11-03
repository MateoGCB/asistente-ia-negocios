"""GET /menus/ (only my menus, with items_count) and DELETE /menus/{menu_id}."""
import pytest

from models.business_models import Business_db
from models.menu_models import Menu_db, MenuItem_db
from models.order_models import Order_db, OrderItem_db


def menus_of(client, user):
    response = client.get("/menus/", headers=user.headers)
    assert response.status_code == 200, response.text
    return response.json()


def delete_menu(client, user, menu_id):
    return client.delete(f"/menus/{menu_id}", headers=user.headers)


# ---------------------------------------------------------------- GET /menus/

def test_list_shows_only_my_menus_with_items_count(client, user_a, user_b, create_menu, create_item):
    empty = create_menu(user_a, name="Vacío")
    one = create_menu(user_a, name="Uno")
    several = create_menu(user_a, name="Varios")
    create_item(user_a, one["id"])
    for n in range(3):
        create_item(user_a, several["id"], name=f"Plato {n}")
    create_item(user_b, create_menu(user_b, name="Menú de B")["id"])

    assert menus_of(client, user_a) == [
        {"id": empty["id"], "name": "Vacío", "items_count": 0},
        {"id": one["id"], "name": "Uno", "items_count": 1},
        {"id": several["id"], "name": "Varios", "items_count": 3},
    ]


def test_two_users_do_not_see_each_others_menus(client, user_a, user_b, create_menu):
    menu_a = create_menu(user_a, name="De A")
    menu_b = create_menu(user_b, name="De B")

    assert [m["id"] for m in menus_of(client, user_a)] == [menu_a["id"]]
    assert [m["id"] for m in menus_of(client, user_b)] == [menu_b["id"]]


def test_list_has_exactly_the_public_keys(client, user_a, create_menu):
    create_menu(user_a)

    assert all(set(menu) == {"id", "name", "items_count"} for menu in menus_of(client, user_a))  # no owner_id


def test_unavailable_items_are_counted_too(client, user_a, create_menu, create_item):
    # items_count counts every item of the menu, also the ones marked as sold out
    menu = create_menu(user_a)
    item = create_item(user_a, menu["id"])
    client.patch(f"/menus/{menu['id']}/items/{item['id']}", json={"available": False}, headers=user_a.headers)

    assert menus_of(client, user_a)[0]["items_count"] == 1


def test_list_without_token_returns_401(client):
    assert client.get("/menus/").status_code == 401


def test_list_of_a_user_without_menus_is_empty(client, user_a):
    assert menus_of(client, user_a) == []


# ---------------------------------------------------------------- DELETE /menus/{id}

@pytest.fixture
def menu_with_items(user_a, create_menu, create_item):
    menu = create_menu(user_a, name="Para Borrar")
    items = [create_item(user_a, menu["id"], name=f"Plato {n}") for n in range(2)]
    return menu, items


def test_delete_menu_without_businesses(client, user_a, menu_with_items, db_session):
    menu, items = menu_with_items

    response = delete_menu(client, user_a, menu["id"])

    assert response.status_code == 200
    assert response.json() == {"message": "Menu deleted successfully"}
    assert db_session.get(Menu_db, menu["id"]) is None
    assert db_session.query(MenuItem_db).filter(MenuItem_db.id.in_([i["id"] for i in items])).count() == 0
    assert menus_of(client, user_a) == []
    assert client.get(f"/menus/{menu['id']}/items", headers=user_a.headers).status_code == 404


def test_foreign_menu_returns_404_and_is_kept(client, user_b, menu_with_items, db_session):
    menu, items = menu_with_items

    foreign = delete_menu(client, user_b, menu["id"])
    unknown = delete_menu(client, user_b, 9999)

    assert foreign.status_code == unknown.status_code == 404
    assert foreign.json() == unknown.json()  # B cannot tell "not yours" from "does not exist"
    assert db_session.get(Menu_db, menu["id"]) is not None
    assert db_session.query(MenuItem_db).filter(MenuItem_db.menu_id == menu["id"]).count() == 2


def test_menu_used_by_an_active_business_returns_409_and_nothing_is_deleted(client, user_a, menu_with_items, create_business, assign_menu, db_session):
    menu, items = menu_with_items
    business = create_business(user_a)
    assign_menu(user_a, business["id"], menu["id"])

    response = delete_menu(client, user_a, menu["id"])

    assert response.status_code == 409
    assert "active businesses" in response.json()["detail"]
    db_session.expire_all()
    assert db_session.get(Menu_db, menu["id"]) is not None
    assert db_session.query(MenuItem_db).filter(MenuItem_db.menu_id == menu["id"]).count() == 2
    assert db_session.get(Business_db, business["id"]).menu_id == menu["id"]


def test_menu_shared_by_two_active_businesses_returns_409(client, user_a, menu_with_items, create_business, assign_menu):
    menu, _ = menu_with_items
    for name in ("Sucursal 1", "Sucursal 2"):
        assign_menu(user_a, create_business(user_a, name=name)["id"], menu["id"])

    assert delete_menu(client, user_a, menu["id"]).status_code == 409


def test_menu_used_only_by_an_archived_business_is_deleted_and_detached(client, user_a, menu_with_items, create_business, assign_menu, db_session):
    menu, _ = menu_with_items
    business = create_business(user_a)
    assign_menu(user_a, business["id"], menu["id"])
    client.delete(f"/businesses/{business['id']}", headers=user_a.headers)  # archive

    response = delete_menu(client, user_a, menu["id"])

    assert response.status_code == 200
    db_session.expire_all()
    assert db_session.get(Business_db, business["id"]).menu_id is None
    assert db_session.get(Menu_db, menu["id"]) is None
    assert db_session.query(MenuItem_db).filter(MenuItem_db.menu_id == menu["id"]).count() == 0


def test_409_with_an_active_and_an_archived_business_changes_nothing(client, user_a, menu_with_items, create_business, assign_menu, db_session):
    # All or nothing: the archived business must NOT be detached when the delete is refused
    menu, _ = menu_with_items
    active = create_business(user_a, name="Activa")
    archived = create_business(user_a, name="Archivada")
    assign_menu(user_a, active["id"], menu["id"])
    assign_menu(user_a, archived["id"], menu["id"])
    client.delete(f"/businesses/{archived['id']}", headers=user_a.headers)

    assert delete_menu(client, user_a, menu["id"]).status_code == 409

    db_session.expire_all()
    assert db_session.get(Business_db, archived["id"]).menu_id == menu["id"]
    assert db_session.query(MenuItem_db).filter(MenuItem_db.menu_id == menu["id"]).count() == 2


def test_old_orders_are_kept_after_deleting_the_menu(client, shop, place_order, db_session):
    assert place_order(shop.business["slug"], [(shop.items[0]["id"], 2)]).status_code == 201
    client.delete(f"/businesses/{shop.business['id']}", headers=shop.owner.headers)  # archive first

    assert delete_menu(client, shop.owner, shop.menu["id"]).status_code == 200

    db_session.expire_all()
    order = db_session.query(Order_db).one()
    assert order.business_id == shop.business["id"]
    line = db_session.query(OrderItem_db).one()
    # The snapshot keeps the name and price even though the menu item no longer exists
    assert (line.item_name, str(line.unit_price), line.quantity) == ("Pizza Muzzarella", "8500.00", 2)


def test_delete_menu_without_token_returns_401(client, menu_with_items):
    assert client.delete(f"/menus/{menu_with_items[0]['id']}").status_code == 401

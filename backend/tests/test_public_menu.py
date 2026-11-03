"""GET /public/{slug}/menu: no token, and only what an anonymous customer may see."""
import pytest

# The public schemas are a WHITE LIST: if a field is added by mistake, these tests fail
PUBLIC_MENU_KEYS = {"business_name", "menu_name", "items"}
PUBLIC_ITEM_KEYS = {"id", "name", "description", "price", "category"}


def public_menu(client, slug, headers=None):
    return client.get(f"/public/{slug}/menu", headers=headers)


def test_public_menu_works_without_token(client, shop):
    response = public_menu(client, shop.business["slug"])

    assert response.status_code == 200
    data = response.json()
    assert data["business_name"] == "Pizzería de Prueba"
    assert data["menu_name"] == "Carta de Prueba"
    assert [i["name"] for i in data["items"]] == ["Pizza Muzzarella", "Café con leche"]
    assert data["items"][1]["price"] == "3500.50"


def test_public_menu_has_exactly_the_public_keys(client, shop):
    data = public_menu(client, shop.business["slug"]).json()

    assert set(data) == PUBLIC_MENU_KEYS
    for item in data["items"]:
        # No owner_id, menu_id, slug, available, or anything internal
        assert set(item) == PUBLIC_ITEM_KEYS


def test_unavailable_items_are_hidden(client, shop):
    hidden = shop.items[0]
    client.patch(f"/menus/{shop.menu['id']}/items/{hidden['id']}", json={"available": False}, headers=shop.owner.headers)

    items = public_menu(client, shop.business["slug"]).json()["items"]

    assert [i["id"] for i in items] == [shop.items[1]["id"]]


def test_menu_without_available_items_returns_200_with_empty_list(client, shop):
    for item in shop.items:
        client.patch(f"/menus/{shop.menu['id']}/items/{item['id']}", json={"available": False}, headers=shop.owner.headers)

    response = public_menu(client, shop.business["slug"])

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_item_turned_back_on_reappears(client, shop):
    url = f"/menus/{shop.menu['id']}/items/{shop.items[0]['id']}"
    client.patch(url, json={"available": False}, headers=shop.owner.headers)
    client.patch(url, json={"available": True}, headers=shop.owner.headers)

    assert len(public_menu(client, shop.business["slug"]).json()["items"]) == 2


def test_invalid_token_in_the_header_is_ignored(client, shop):
    # A public endpoint does not even look at Authorization: a garbage token must not cause a 401
    response = public_menu(client, shop.business["slug"], headers={"Authorization": "Bearer basura"})

    assert response.status_code == 200


def test_two_branches_with_the_same_menu_show_the_same_items(client, shop, create_business, assign_menu):
    other = create_business(shop.owner, name="Otra Sucursal")
    assign_menu(shop.owner, other["id"], shop.menu["id"])

    first = public_menu(client, shop.business["slug"]).json()
    second = public_menu(client, other["slug"]).json()

    assert first["items"] == second["items"]
    assert second["business_name"] == "Otra Sucursal"


# ---------------------------------------------------------------- every "not available" case looks the same

@pytest.fixture
def not_found_reference(client):
    # What a slug that never existed answers: every other case below must be IDENTICAL
    response = public_menu(client, "este-slug-no-existe")
    assert response.status_code == 404
    return response.json()


def test_branch_without_menu_gives_the_same_404_as_unknown_slug(client, user_a, create_business, not_found_reference):
    without_menu = create_business(user_a, name="Sin Menu")

    response = public_menu(client, without_menu["slug"])

    assert response.status_code == 404
    assert response.json() == not_found_reference


def test_uppercase_slug_gives_404(client, shop, not_found_reference):
    # Slugs are always lowercase; the lookup is exact
    response = public_menu(client, shop.business["slug"].upper())

    assert response.status_code == 404
    assert response.json() == not_found_reference


def test_archived_business_gives_the_same_404_as_unknown_slug(client, shop, not_found_reference):
    client.delete(f"/businesses/{shop.business['id']}", headers=shop.owner.headers)

    response = public_menu(client, shop.business["slug"])

    assert response.status_code == 404
    assert response.json() == not_found_reference

"""
API-тесты для блюд: **отображение списка** (поиск/фильтры) (EP).
"""

from __future__ import annotations

import pytest
import httpx

from tests.conftest import dish_json, product_json, unique_token


class TestDishListSearchAndFilters:
    """EP: фильтры по категории и флагам; подстрочный поиск."""

    @pytest.fixture
    def dishes_for_filters(self, client: httpx.Client):
        token = unique_token()
        product_id_base = int(
            client.post("/api/products", json=product_json(name=f"Prod {token}", is_vegan=True)).json()["id"]
        )
        dish_id_salad = int(
            client.post(
                "/api/dishes",
                json=dish_json(product_id_base, name=f"GreenSalad {token}", category="Салат", is_vegan=True),
            ).json()["id"]
        )
        dish_id_soup = int(
            client.post(
                "/api/dishes",
                json=dish_json(product_id_base, name=f"SoupBowl {token}", category="Суп", is_vegan=True),
            ).json()["id"]
        )
        return client, (dish_id_salad, dish_id_soup)

    def test_search_substring_ascii_case_insensitive(self, client: httpx.Client):
        """Латиница: поиск в изолированном срезе (уникальный токен в названии)."""
        token = unique_token()
        p = int(client.post("/api/products", json=product_json(name=f"Prod {token}", is_vegan=True)).json()["id"])
        d = int(client.post("/api/dishes", json=dish_json(p, name=f"Green-{token}", category="Салат", is_vegan=True)).json()["id"])
        response = client.get("/api/dishes", params={"q": token})
        ids = {item["id"] for item in response.json()}
        assert (response.status_code, d in ids) == (200, True)

    def test_filter_category_includes_created_dish(self, dishes_for_filters):
        client, (_, dish_id_soup) = dishes_for_filters
        response = client.get("/api/dishes", params={"category": "Суп"})
        ids = {item["id"] for item in response.json()}
        assert (response.status_code, dish_id_soup in ids) == (200, True)


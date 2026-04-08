"""
API-тесты для продуктов: **отображение списка** (поиск/фильтры/сортировка) (EP/BVA).
"""

from __future__ import annotations

import pytest
import httpx

from tests.conftest import product_json, unique_token

class TestProductListFiltersSearchSort:
    """
    EP: комбинации фильтров; подстрочный поиск.
    BVA: параметр sort_by на границе допустимого набора vs недопустимое значение.
    """

    @pytest.fixture
    def three_products(self, client: httpx.Client):
        """Три продукта с разными категориями и флагами для EP классов фильтрации."""
        token_borscht = unique_token()
        token_chicken = unique_token()
        token_herb = unique_token()
        product_id_borscht = int(
            client.post(
                "/api/products",
                json=product_json(name=f"Борщ овощной {token_borscht}", category="Овощи", is_vegan=True, calories=30.0),
            ).json()["id"]
        )
        product_id_chicken = int(
            client.post(
                "/api/products",
                json=product_json(name=f"Курица {token_chicken}", category="Мясной", is_vegan=False, calories=200.0),
            ).json()["id"]
        )
        product_id_herb = int(
            client.post(
                "/api/products",
                json=product_json(name=f"борщник трава {token_herb}", category="Зелень", is_vegan=True, calories=5.0),
            ).json()["id"]
        )
        return client, (product_id_borscht, product_id_chicken, product_id_herb)

    def test_search_substring_ascii_case_insensitive(self, client: httpx.Client):
        """
        EP: подстрочный поиск; BVA: разный регистр в запросе и в БД.

        Для кириллицы ``lower()`` в SQLite без ICU не нормализует буквы, поэтому здесь
        используются латинские имена — проверяется задуманная логика API (casefold запроса + lower колонки).
        """
        token = unique_token()
        client.post("/api/products", json=product_json(name=f"TomatoBase {token}", category="Овощи", calories=10.0))
        client.post("/api/products", json=product_json(name=f"tomato leaf {token}", category="Зелень", calories=2.0))
        response = client.get("/api/products", params={"q": token})
        names = {item["name"] for item in response.json()}
        assert (response.status_code, {n.rsplit(" ", 1)[0] for n in names}) == (200, {"TomatoBase", "tomato leaf"})

    def test_search_by_unique_suffix_token_isolated_from_user_data(self, three_products):
        """
        EP: поиск по подстроке.

        Мы работаем с продовой БД (там могут быть пользовательские продукты), поэтому изолируем поиск
        уникальным ASCII-токеном, который гарантированно относится только к созданной тестом записи.
        """
        client, (_, _, product_id_herb) = three_products
        name = client.get(f"/api/products/{product_id_herb}").json()["name"]
        token = name.rsplit(" ", 1)[1]
        response = client.get("/api/products", params={"q": token})
        ids = {item["id"] for item in response.json()}
        assert (response.status_code, product_id_herb in ids) == (200, True)

    def test_filter_category_and_vegan_includes_created_product(self, three_products):
        client, (product_id_borscht, _, _) = three_products
        response = client.get("/api/products", params={"category": "Овощи", "is_vegan": True})
        ids = {item["id"] for item in response.json()}
        assert (response.status_code, product_id_borscht in ids) == (200, True)

    def test_sort_by_name_asc_with_unique_query_scope(self, client: httpx.Client):
        """BVA/EP: сортировка по имени проверяется в изолированном срезе списка (через уникальный q)."""
        token = unique_token()
        product_id_alpha = int(
            client.post("/api/products", json=product_json(name=f"Sort-{token}-Alpha", calories=100.0)).json()["id"]
        )
        product_id_omega = int(
            client.post("/api/products", json=product_json(name=f"Sort-{token}-Omega", calories=10.0)).json()["id"]
        )
        response = client.get("/api/products", params={"q": token, "sort_by": "name"})
        ids_in_order = [item["id"] for item in response.json()]
        assert (response.status_code, ids_in_order[:2]) == (200, [product_id_alpha, product_id_omega])

    def test_sort_by_calories_asc_with_unique_query_scope(self, client: httpx.Client):
        """EP: сортировка по калориям проверяется в изолированном срезе списка (через уникальный q)."""
        token = unique_token()
        product_id_high_calories = int(
            client.post("/api/products", json=product_json(name=f"Sort-{token}-Hi", calories=100.0)).json()["id"]
        )
        product_id_low_calories = int(
            client.post("/api/products", json=product_json(name=f"Sort-{token}-Lo", calories=10.0)).json()["id"]
        )
        response = client.get("/api/products", params={"q": token, "sort_by": "calories"})
        ids_in_order = [item["id"] for item in response.json()]
        assert (response.status_code, ids_in_order[:2]) == (200, [product_id_low_calories, product_id_high_calories])

    def test_sort_by_invalid_pattern_422(self, client: httpx.Client):
        """BVA: значение вне шаблона Query pattern — ожидаем 422 от FastAPI."""
        response = client.get("/api/products", params={"sort_by": "invalid"})
        assert response.status_code == 422


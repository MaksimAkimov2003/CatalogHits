"""
API-тесты для блюд: макросы категории, флаги по составу, endpoint чернового расчёта (EP/BVA).
"""

from __future__ import annotations

import httpx

from tests.conftest import dish_json, product_json, unique_token


class TestDishMacrosAndExplicitCategory:
    """
    EP: макрос в названии задаёт категорию; явная категория в форме перекрывает макрос.
    BVA: несколько макросов — срабатывает первый по позиции в строке (требование ТЗ).
    """

    def test_macro_in_name_sets_category_and_strips_macro(self, client: httpx.Client):
        token = unique_token()
        pid = int(
            client.post(
                "/api/products",
                json=product_json(
                    name=f"Огурец {token}",
                    calories=15.0,
                    proteins=1.0,
                    fats=0.0,
                    carbs=3.0,
                    is_vegan=True,
                    is_gluten_free=True,
                    is_sugar_free=True,
                ),
            ).json()["id"]
        )
        response = client.post(
            "/api/dishes",
            json={
                "name": "!салат Огуречный",
                "photos": [],
                "ingredients": [{"product_id": pid, "amount_grams": 100.0}],
                "portion_size": 100.0,
                "category": None,
                "calories": None,
                "proteins": None,
                "fats": None,
                "carbs": None,
                "is_vegan": True,
                "is_gluten_free": True,
                "is_sugar_free": True,
            },
        )
        body = response.json()
        assert (response.status_code, body.get("category")) == (200, "Салат")

    def test_explicit_category_overrides_macro(self, client: httpx.Client):
        token = unique_token()
        pid = int(client.post("/api/products", json=product_json(name=f"Prod {token}")).json()["id"])
        response = client.post(
            "/api/dishes",
            json=dish_json(
                pid,
                name="!суп Как суп",
                category="Десерт",
            ),
        )
        assert (response.status_code, response.json().get("category")) == (200, "Десерт")

    def test_first_macro_wins_second_removed_from_name(self, client: httpx.Client):
        """BVA/EP: первый макрос по позиции в строке определяет категорию; все макросы вырезаются из имени."""
        token = unique_token()
        pid = int(client.post("/api/products", json=product_json(name=f"Prod {token}")).json()["id"])
        response = client.post(
            "/api/dishes",
            json=dish_json(
                pid,
                name="!первое !десерт Каша",
                category=None,
                calories=None,
                proteins=None,
                fats=None,
                carbs=None,
            ),
        )
        body = response.json()
        assert (response.status_code, body.get("category")) == (200, "Первое")


class TestDishFlagsAgainstIngredients:
    """EP: флаг «веган» при несовместимом составе — ошибка валидации."""

    def test_vegan_flag_rejected_when_not_all_products_vegan(self, client: httpx.Client):
        token = unique_token()
        vegan = int(client.post("/api/products", json=product_json(name=f"Лук {token}", is_vegan=True)).json()["id"])
        cheese = int(client.post("/api/products", json=product_json(name=f"Сыр {token}", is_vegan=False)).json()["id"])
        response = client.post(
            "/api/dishes",
            json=dish_json(
                vegan,
                name="Салат",
                category="Салат",
                ingredients=[
                    {"product_id": vegan, "amount_grams": 50.0},
                    {"product_id": cheese, "amount_grams": 50.0},
                ],
                portion_size=100.0,
                is_vegan=True,
            ),
        )
        assert response.status_code == 422


class TestCalculateDraftEndpoint:
    """Черновой расчёт КБЖУ и нормализация имени для превью формы."""

    def test_calculate_draft_returns_macros_and_available_flags(self, client: httpx.Client):
        token = unique_token()
        pid = int(
            client.post(
                "/api/products",
                json=product_json(
                    name=f"Киноа {token}",
                    calories=300.0,
                    proteins=12.0,
                    fats=5.0,
                    carbs=55.0,
                    is_vegan=True,
                    is_gluten_free=True,
                    is_sugar_free=True,
                ),
            ).json()["id"]
        )
        response = client.post(
            "/api/dishes/calculate-draft",
            json={
                "name": "!второе Боул",
                "photos": [],
                "ingredients": [{"product_id": pid, "amount_grams": 100.0}],
                "portion_size": 100.0,
                "category": None,
                "calories": None,
                "proteins": None,
                "fats": None,
                "carbs": None,
                "is_vegan": True,
                "is_gluten_free": True,
                "is_sugar_free": True,
            },
        )
        data = response.json()
        assert (
            response.status_code,
            data.get("category"),
            data.get("calories"),
            bool((data.get("available_flags") or {}).get("is_vegan")),
        ) == (200, "Второе", 300.0, True)


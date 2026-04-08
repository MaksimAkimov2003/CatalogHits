"""
API-тесты для блюд: **создание** и базовая валидация (EP/BVA).
"""

from __future__ import annotations

import pytest
import httpx

from tests.conftest import dish_json, product_json, unique_token


class TestDishCreateValidationEquivalenceAndBoundaries:
    """
    EP: нет категории и нет макроса в названии; неверная категория.
    BVA: portion_size > 0, amount_grams > 0 (границы строгих неравенств в схеме).
    """

    def test_no_category_and_no_macro_in_name_rejected(self, client: httpx.Client):
        """EP: класс запросов без способа определить категорию блюда."""
        token = unique_token()
        pid = int(client.post("/api/products", json=product_json(name=f"Prod {token}")).json()["id"])
        response = client.post(
            "/api/dishes",
            json=dish_json(pid, name="Без категории", category=None),
        )
        assert response.status_code == 422

    @pytest.mark.parametrize(
        "portion_size,expect_status",
        [
            pytest.param(0.0, 422, id="bva_portion_size_zero_invalid"),
            pytest.param(-1.0, 422, id="bva_portion_size_negative_invalid"),
            pytest.param(0.01, 200, id="bva_portion_size_small_positive_ok"),
        ],
    )
    def test_portion_size_boundary(self, client: httpx.Client, portion_size: float, expect_status: int):
        """BVA: ``portion_size`` должно быть строго больше нуля."""
        token = unique_token()
        pid = int(client.post("/api/products", json=product_json(name=f"Prod {token}")).json()["id"])
        response = client.post(
            "/api/dishes",
            json=dish_json(pid, portion_size=portion_size),
        )
        assert response.status_code == expect_status

    @pytest.mark.parametrize(
        "amount_grams,expect_status",
        [
            pytest.param(0.0, 422, id="bva_amount_zero_invalid"),
            pytest.param(-5.0, 422, id="bva_amount_negative_invalid"),
            pytest.param(0.01, 200, id="bva_amount_small_positive_ok"),
        ],
    )
    def test_ingredient_amount_boundary(self, client: httpx.Client, amount_grams: float, expect_status: int):
        """BVA: количество ингредиента в граммах — строго > 0."""
        token = unique_token()
        pid = int(client.post("/api/products", json=product_json(name=f"Prod {token}")).json()["id"])
        response = client.post(
            "/api/dishes",
            json=dish_json(
                pid,
                ingredients=[{"product_id": pid, "amount_grams": amount_grams}],
            ),
        )
        assert response.status_code == expect_status

    def test_invalid_dish_category_rejected(self, client: httpx.Client):
        """EP: категория не из DISH_CATEGORIES."""
        token = unique_token()
        pid = int(client.post("/api/products", json=product_json(name=f"Prod {token}")).json()["id"])
        response = client.post(
            "/api/dishes",
            json=dish_json(pid, category="Завтрак"),
        )
        assert response.status_code == 422


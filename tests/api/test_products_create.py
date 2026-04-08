"""
API-тесты для продуктов: **создание** и валидации (EP/BVA).
"""

from __future__ import annotations

import pytest
import httpx

from tests.conftest import product_json


class TestProductCreateEquivalenceAndBoundaries:
    """
    EP: корректное тело запроса vs отсутствующие/некорректные поля.
    BVA: минимальная длина имени (2 символа), сумма БЖУ на 100 г (граница 100), число URL фото (0..5).
    """

    @pytest.mark.parametrize(
        "name,expect_status",
        [
            pytest.param("a", 422, id="bva_name_too_short_one_char"),
            pytest.param("ab", 200, id="bva_name_min_length_two_ok"),
        ],
    )
    def test_name_length_boundary(self, client: httpx.Client, name: str, expect_status: int):
        """BVA: граница min_length=2 для названия."""
        response = client.post("/api/products", json=product_json(name=name))
        assert response.status_code == expect_status

    @pytest.mark.parametrize(
        "proteins,fats,carbs,expect_status",
        [
            pytest.param(40.0, 30.0, 30.0, 200, id="bva_bju_sum_exactly_100_ok"),
            # Явно выше 100 г без артефактов float (40+30+31).
            pytest.param(40.0, 30.0, 31.0, 422, id="bva_bju_sum_over_100_rejected"),
        ],
    )
    def test_bju_sum_boundary_on_100g(self, client: httpx.Client, proteins, fats, carbs, expect_status: int):
        """
        BVA: сумма белков+жиров+углеводов на 100 г не может превышать 100 г (с допуском в валидаторе).
        Проверяем «ровно 100» и значение выше порога.
        """
        response = client.post(
            "/api/products",
            json=product_json(proteins=proteins, fats=fats, carbs=carbs),
        )
        assert response.status_code == expect_status

    @pytest.mark.parametrize(
        "photo_count,expect_status",
        [
            pytest.param(0, 200, id="ep_photos_empty_list"),
            pytest.param(1, 200, id="ep_photos_empty_list"),
            pytest.param(4, 200, id="ep_photos_empty_list"),
            pytest.param(5, 200, id="bva_photos_max_five_ok"),
            pytest.param(6, 422, id="bva_photos_six_rejected"),
        ],
    )
    def test_photos_count_boundaries(self, client: httpx.Client, photo_count: int, expect_status: int):
        """BVA: max_length=5 для списка URL фото; EP: пустой список — допустимый класс."""
        photos = [f"https://example.com/p{i}.jpg" for i in range(photo_count)]
        response = client.post("/api/products", json=product_json(photos=photos))
        assert response.status_code == expect_status

    def test_invalid_category_rejected(self, client: httpx.Client):
        """EP: категория вне перечисления — отдельный класс невалидных входов."""
        response = client.post("/api/products", json=product_json(category="Неизвестная категория"))
        assert response.status_code == 422

    def test_missing_required_numeric_fields_rejected(self, client: httpx.Client):
        """EP: только имя без числовых полей — невалидный запрос (обязательные КБЖУ)."""
        response = client.post("/api/products", json={"name": "Только имя"})
        assert response.status_code == 422


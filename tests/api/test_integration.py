"""
Сквозные API-сценарии (интеграция нескольких эндпоинтов), отражающие требования ТЗ.

Эквивалентное разбиение: «продукт свободен» vs «продукт в составе блюда» для операции DELETE.
"""

from __future__ import annotations

import httpx

from tests.conftest import product_json, unique_token


class TestProductDeletionBlockedByDish:
    """
    ТЗ 1.5: удаление продукта, используемого в блюде, недоступно; ответ содержит список блюд.
    После удаления блюда продукт можно удалить (переход между классами эквивалентности).
    """

    def test_delete_product_conflict_lists_dish_names_then_succeeds_after_dish_removed(
        self, client: httpx.Client
    ):
        token = unique_token()
        product_id_tomato = int(
            client.post(
                "/api/products",
                json=product_json(name=f"Томат {token}", is_vegan=True, is_gluten_free=True, is_sugar_free=True),
            ).json()["id"]
        )
        product_id_cheese = int(
            client.post(
                "/api/products",
                json=product_json(name=f"Сыр {token}", is_vegan=False, is_gluten_free=True, is_sugar_free=True),
            ).json()["id"]
        )

        dish = client.post(
            "/api/dishes",
            json={
                "name": "Салат с сыром",
                "photos": [],
                "ingredients": [
                    {"product_id": product_id_tomato, "amount_grams": 120.0},
                    {"product_id": product_id_cheese, "amount_grams": 80.0},
                ],
                "portion_size": 200.0,
                "category": "Салат",
                "calories": None,
                "proteins": None,
                "fats": None,
                "carbs": None,
                "is_vegan": False,
                "is_gluten_free": True,
                "is_sugar_free": True,
            },
        )
        dish_id = dish.json()["id"]

        blocked = client.delete(f"/api/products/{product_id_tomato}")
        detail = blocked.json().get("detail") or {}
        has_dish_name = "Салат с сыром" in (detail.get("dishes") or [])

        del_dish = client.delete(f"/api/dishes/{dish_id}")
        del_product_after = client.delete(f"/api/products/{product_id_tomato}")
        assert (dish.status_code, blocked.status_code, has_dish_name, del_dish.status_code, del_product_after.status_code) == (
            200,
            409,
            True,
            200,
            200,
        )


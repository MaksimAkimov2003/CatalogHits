"""
Unit tests for dish macro (KБЖУ) draft calculation.

Требование ТЗ:
- покрыть unit-тестами автоматический расчёт калорийности блюда.
- обязательно использовать техники тест-дизайна:
  - Эквивалентное разбиение (Equivalence Partitioning)
  - Анализ граничных значений (Boundary Value Analysis)

Мы тестируем функцию `app.services.calculate_draft_macros` напрямую (без API),
то есть это именно unit-тесты бизнес-логики расчёта.

Эквивалентные классы (для калорийности):
- EP1: 1 ингредиент, валидные значения (amount_grams > 0, calories >= 0)
- EP2: несколько ингредиентов (суммирование)
- EP3: продукт не найден (ошибка 404)

Граничные значения:
- BV1: amount_grams = 0.01 (минимально-положительное, близко к 0)
- BV2: amount_grams = 0 (граница; в проде отсечено схемой, но проверяем формулу)
- BV3: calories = 0 (граница калорийности)
"""

from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
from fastapi import HTTPException

from app import models
from app.services import calculate_draft_macros


@dataclass(frozen=True)
class IngredientPayload:
    """Минимальный payload-объект с атрибутами, ожидаемыми calculate_draft_macros."""

    product_id: int
    amount_grams: float


@pytest.fixture()
def db_mock():
    """
    `calculate_draft_macros` использует только `db.get(models.Product, product_id)`,
    поэтому для unit-теста достаточно замокать `get` и задать возвращаемые продукты.
    """
    db = Mock()
    return db


def _product_stub(
    *,
    calories: float,
    proteins: float = 0.0,
    fats: float = 0.0,
    carbs: float = 0.0,
    is_vegan: bool = True,
    is_gluten_free: bool = True,
    is_sugar_free: bool = True,
):
    # Минимальный объект, который нужен calculate_draft_macros:
    # calories/proteins/fats/carbs + флаги.
    return SimpleNamespace(
        calories=calories,
        proteins=proteins,
        fats=fats,
        carbs=carbs,
        is_vegan=is_vegan,
        is_gluten_free=is_gluten_free,
        is_sugar_free=is_sugar_free,
    )


@pytest.mark.parametrize(
    "calories_per_100,amount_grams,expected",
    [
        # EP1: 1 ингредиент (валидные значения)
        (100.0, 150.0, 150.0),
        (250.0, 40.0, 100.0),
        # BV1: очень маленькое положительное количество
        (123.0, 0.01, 0.0123),
        # BV2: граница amount=0 (в проде схемой запрещено, но формула должна быть стабильна)
        (123.0, 0.0, 0.0),
        # BV3: граница calories=0
        (0.0, 999.0, 0.0),
    ],
)
def test_calculate_draft_calories_single_ingredient_equivalence_and_boundaries(
    db_mock, calories_per_100, amount_grams, expected
):
    """
    Эквивалентное разбиение (EP1) + граничные значения (BV1/BV2/BV3)
    для формулы:
      calories_portion = calories_100g * amount_grams / 100
    """

    # Given
    product_id = 1
    db_mock.get.return_value = _product_stub(calories=calories_per_100)

    # When
    calories, proteins, fats, carbs, flags = calculate_draft_macros(
        db_mock, [IngredientPayload(product_id=product_id, amount_grams=amount_grams)]
    )

    # Then
    db_mock.get.assert_called_once_with(models.Product, product_id)
    assert calories == pytest.approx(expected, rel=1e-12, abs=1e-12)
    # Доп. утверждения (не основная цель, но помогает ловить регрессии)
    assert proteins == pytest.approx(0.0)
    assert fats == pytest.approx(0.0)
    assert carbs == pytest.approx(0.0)
    assert flags == {"is_vegan": True, "is_gluten_free": True, "is_sugar_free": True}


def test_calculate_draft_calories_multiple_ingredients_sums(db_mock):
    """
    EP2: несколько ингредиентов — проверяем суммирование вкладов.
    """

    # Given
    p1_id = 10
    p2_id = 20

    def get_side_effect(model, product_id):
        assert model is models.Product
        if product_id == p1_id:
            return _product_stub(calories=100.0)
        if product_id == p2_id:
            return _product_stub(calories=250.0)
        return None

    db_mock.get.side_effect = get_side_effect

    # When
    calories, *_ = calculate_draft_macros(
        db_mock,
        [
            IngredientPayload(product_id=p1_id, amount_grams=120.0),  # 120
            IngredientPayload(product_id=p2_id, amount_grams=80.0),  # 200
        ],
    )

    # Then
    assert db_mock.get.call_args_list == [call(models.Product, p1_id), call(models.Product, p2_id)]
    assert calories == pytest.approx(320.0)


def test_calculate_draft_raises_404_when_product_missing(db_mock):
    """
    EP3: продукт не найден -> HTTPException(404).
    """

    # Given
    db_mock.get.return_value = None

    # When / Then
    with pytest.raises(HTTPException) as err:
        calculate_draft_macros(db_mock, [IngredientPayload(product_id=9999, amount_grams=100.0)])
    db_mock.get.assert_called_once_with(models.Product, 9999)
    assert err.value.status_code == 404


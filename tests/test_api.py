from pathlib import Path
import sys

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import Base, get_db
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_recipe_book.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def make_product(name: str, vegan: bool, gluten: bool, sugar: bool):
    response = client.post(
        "/api/products",
        json={
            "name": name,
            "photos": [],
            "calories": 100,
            "proteins": 10,
            "fats": 5,
            "carbs": 20,
            "composition": None,
            "category": "Овощи",
            "cooking_requirement": "Готовый к употреблению",
            "is_vegan": vegan,
            "is_gluten_free": gluten,
            "is_sugar_free": sugar,
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_product_and_dish_flow():
    p1 = make_product("Томат", True, True, True)
    p2 = make_product("Сыр", False, True, True)

    draft = client.post(
        "/api/dishes/calculate-draft",
        json={
            "name": "!салат Салат томатный",
            "photos": [],
            "ingredients": [{"product_id": p1, "amount_grams": 200}],
            "portion_size": 200,
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
    assert draft.status_code == 200
    assert draft.json()["category"] == "Салат"

    bad_dish = client.post(
        "/api/dishes",
        json={
            "name": "Салат с сыром",
            "photos": [],
            "ingredients": [
                {"product_id": p1, "amount_grams": 120},
                {"product_id": p2, "amount_grams": 80},
            ],
            "portion_size": 200,
            "category": "Салат",
            "is_vegan": True,
            "is_gluten_free": True,
            "is_sugar_free": True,
        },
    )
    assert bad_dish.status_code == 422

    good_dish = client.post(
        "/api/dishes",
        json={
            "name": "Салат с сыром",
            "photos": [],
            "ingredients": [
                {"product_id": p1, "amount_grams": 120},
                {"product_id": p2, "amount_grams": 80},
            ],
            "portion_size": 200,
            "category": "Салат",
            "is_vegan": False,
            "is_gluten_free": True,
            "is_sugar_free": True,
        },
    )
    assert good_dish.status_code == 200
    dish_id = good_dish.json()["id"]

    cannot_delete = client.delete(f"/api/products/{p1}")
    assert cannot_delete.status_code == 409
    assert "dishes" in cannot_delete.json()["detail"]

    delete_dish = client.delete(f"/api/dishes/{dish_id}")
    assert delete_dish.status_code == 200
    delete_product = client.delete(f"/api/products/{p1}")
    assert delete_product.status_code == 200


def test_product_bju_sum_cannot_exceed_100():
    response = client.post(
        "/api/products",
        json={
            "name": "Плохой продукт",
            "photos": [],
            "calories": 100,
            "proteins": 60,
            "fats": 30,
            "carbs": 20,  # 110 > 100
            "composition": None,
            "category": "Овощи",
            "cooking_requirement": "Готовый к употреблению",
            "is_vegan": True,
            "is_gluten_free": True,
            "is_sugar_free": True,
        },
    )
    assert response.status_code == 422


def test_product_create_requires_required_fields():
    response = client.post(
        "/api/products",
        json={
            "name": "Только имя",
        },
    )
    assert response.status_code == 422

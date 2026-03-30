import json
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional, Tuple, Dict

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app import models

TZ_UTC7 = timezone(timedelta(hours=7))

MACRO_CATEGORY_MAP = {
    "!десерт": "Десерт",
    "!первое": "Первое",
    "!второе": "Второе",
    "!напиток": "Напиток",
    "!салат": "Салат",
    "!суп": "Суп",
    "!перекус": "Перекус",
}


def serialize_photos(photos: list[str]) -> str:
    return json.dumps(photos, ensure_ascii=False)


def deserialize_photos(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    photos = json.loads(raw)
    if not isinstance(photos, list):
        return []

    normalized: list[str] = []
    i = 0
    while i < len(photos):
        cur = photos[i]
        nxt = photos[i + 1] if i + 1 < len(photos) else None

        # Backward-compat: some clients split `data:` URLs by comma which breaks the required
        # `data:<mime>[;base64],<payload>` format into two list entries.
        if (
            isinstance(cur, str)
            and isinstance(nxt, str)
            and cur.startswith("data:")
            and "," not in cur
            and nxt
            and not nxt.startswith(("http://", "https://", "data:"))
        ):
            normalized.append(f"{cur},{nxt}")
            i += 2
            continue

        normalized.append(cur if isinstance(cur, str) else str(cur))
        i += 1

    return normalized


def normalize_name_and_category(name: str, explicit_category: Optional[str]) -> Tuple[str, str]:
    clean_name = name
    # Requirement: if multiple macros are present, apply ONLY the first one by position in the name.
    detected_macro = None
    detected_category = None
    detected_pos = None
    for macro, category in MACRO_CATEGORY_MAP.items():
        pos = clean_name.find(macro)
        if pos == -1:
            continue
        if detected_pos is None or pos < detected_pos:
            detected_pos = pos
            detected_macro = macro
            detected_category = category

    # Remove all macros from the final name, but category is determined only by the first macro.
    for macro in MACRO_CATEGORY_MAP.keys():
        if macro in clean_name:
            clean_name = clean_name.replace(macro, "")
    clean_name = " ".join(clean_name.split())
    category = explicit_category or detected_category
    if not category:
        raise HTTPException(status_code=422, detail="Категория блюда не определена")
    return clean_name, category


def calculate_draft_macros(db: Session, ingredients_payload: Iterable) -> Tuple[float, float, float, float, Dict[str, bool]]:
    calories = proteins = fats = carbs = 0.0
    all_vegan = True
    all_gluten_free = True
    all_sugar_free = True

    for item in ingredients_payload:
        product = db.get(models.Product, item.product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Продукт {item.product_id} не найден")
        ratio = item.amount_grams / 100.0
        calories += product.calories * ratio
        proteins += product.proteins * ratio
        fats += product.fats * ratio
        carbs += product.carbs * ratio
        all_vegan = all_vegan and product.is_vegan
        all_gluten_free = all_gluten_free and product.is_gluten_free
        all_sugar_free = all_sugar_free and product.is_sugar_free

    available_flags = {
        "is_vegan": all_vegan,
        "is_gluten_free": all_gluten_free,
        "is_sugar_free": all_sugar_free,
    }
    return calories, proteins, fats, carbs, available_flags


def validate_dish_flags(payload, available_flags: dict[str, bool]):
    for key, can_be_set in available_flags.items():
        if getattr(payload, key) and not can_be_set:
            raise HTTPException(
                status_code=422,
                detail=f"Флаг {key} недоступен из-за состава блюда",
            )


def dish_to_dict(dish: models.Dish) -> dict:
    ingredients = [
        {
            "id": i.id,
            "product_id": i.product_id,
            "product_name": i.product.name,
            "amount_grams": i.amount_grams,
        }
        for i in dish.ingredients
    ]
    available = {
        "is_vegan": all(i.product.is_vegan for i in dish.ingredients),
        "is_gluten_free": all(i.product.is_gluten_free for i in dish.ingredients),
        "is_sugar_free": all(i.product.is_sugar_free for i in dish.ingredients),
    }
    return {
        "id": dish.id,
        "name": dish.name,
        "photos": deserialize_photos(dish.photos),
        "calories": dish.calories,
        "proteins": dish.proteins,
        "fats": dish.fats,
        "carbs": dish.carbs,
        "portion_size": dish.portion_size,
        "category": dish.category,
        "is_vegan": dish.is_vegan if available["is_vegan"] else False,
        "is_gluten_free": dish.is_gluten_free if available["is_gluten_free"] else False,
        "is_sugar_free": dish.is_sugar_free if available["is_sugar_free"] else False,
        "ingredients": ingredients,
        "available_flags": available,
        "created_at": to_utc7(dish.created_at),
        "updated_at": to_utc7(dish.updated_at),
    }


def fetch_dish_or_404(db: Session, dish_id: int) -> models.Dish:
    dish = (
        db.query(models.Dish)
        .options(joinedload(models.Dish.ingredients).joinedload(models.DishIngredient.product))
        .filter(models.Dish.id == dish_id)
        .first()
    )
    if not dish:
        raise HTTPException(status_code=404, detail="Блюдо не найдено")
    return dish


def now_utc():
    return datetime.utcnow()


def to_utc7(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TZ_UTC7)

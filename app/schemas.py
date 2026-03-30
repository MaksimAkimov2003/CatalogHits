from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

PRODUCT_CATEGORIES = [
    "Замороженный",
    "Мясной",
    "Овощи",
    "Зелень",
    "Специи",
    "Крупы",
    "Консервы",
    "Жидкость",
    "Сладости",
]
COOKING_REQUIREMENTS = ["Готовый к употреблению", "Полуфабрикат", "Требует приготовления"]
DISH_CATEGORIES = ["Десерт", "Первое", "Второе", "Напиток", "Салат", "Суп", "Перекус"]


class ProductFields(BaseModel):
    name: str = Field(..., min_length=2)
    photos: list[str] = Field(default_factory=list, max_length=5)
    calories: float = Field(..., ge=0)
    proteins: float = Field(..., ge=0)
    fats: float = Field(..., ge=0)
    carbs: float = Field(..., ge=0)
    composition: Optional[str] = None
    category: str
    cooking_requirement: str
    is_vegan: bool = False
    is_gluten_free: bool = False
    is_sugar_free: bool = False

    @field_validator("category")
    @classmethod
    def validate_product_category(cls, value: str) -> str:
        if value not in PRODUCT_CATEGORIES:
            raise ValueError("Недопустимая категория продукта")
        return value

    @field_validator("cooking_requirement")
    @classmethod
    def validate_cooking_requirement(cls, value: str) -> str:
        if value not in COOKING_REQUIREMENTS:
            raise ValueError("Недопустимое значение необходимости готовки")
        return value


class ProductIn(ProductFields):
    @model_validator(mode="after")
    def validate_bju_sum(self):
        # На 100г продукта сумма БЖУ не может превышать 100г.
        # Делаем небольшой допуск на погрешность округления.
        total = float(self.proteins) + float(self.fats) + float(self.carbs)
        if total > 100.0 + 1e-6:
            raise ValueError("Сумма БЖУ на 100 г не может превышать 100 г")
        return self


class ProductCreate(ProductIn):
    pass


class ProductUpdate(ProductIn):
    pass


class ProductOut(ProductFields):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DishIngredientInput(BaseModel):
    product_id: int
    amount_grams: float = Field(..., gt=0)


class DishIngredientOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    amount_grams: float


class DishBase(BaseModel):
    name: str = Field(..., min_length=2)
    photos: list[str] = Field(default_factory=list, max_length=5)
    calories: Optional[float] = Field(default=None, ge=0)
    proteins: Optional[float] = Field(default=None, ge=0)
    fats: Optional[float] = Field(default=None, ge=0)
    carbs: Optional[float] = Field(default=None, ge=0)
    ingredients: list[DishIngredientInput] = Field(..., min_length=1)
    portion_size: float = Field(..., gt=0)
    category: Optional[str] = None
    is_vegan: bool = False
    is_gluten_free: bool = False
    is_sugar_free: bool = False

    @field_validator("category")
    @classmethod
    def validate_dish_category(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if value not in DISH_CATEGORIES:
            raise ValueError("Недопустимая категория блюда")
        return value

    @model_validator(mode="after")
    def check_category_present(self):
        if self.category is None and not any(m in self.name for m in ("!десерт", "!первое", "!второе", "!напиток", "!салат", "!суп", "!перекус")):
            raise ValueError("Укажите категорию блюда или макрос в названии")
        return self


class DishCreate(DishBase):
    pass


class DishUpdate(DishBase):
    pass


class DishOut(BaseModel):
    id: int
    name: str
    photos: list[str]
    calories: float
    proteins: float
    fats: float
    carbs: float
    portion_size: float
    category: str
    is_vegan: bool
    is_gluten_free: bool
    is_sugar_free: bool
    ingredients: list[DishIngredientOut]
    available_flags: dict[str, bool]
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

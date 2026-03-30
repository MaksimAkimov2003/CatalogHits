from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from starlette.requests import Request
from typing import Optional

from app import models, schemas, services
from app.database import Base, engine, get_db

app = FastAPI(title="Книга рецептов")
Base.metadata.create_all(bind=engine)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/products/new", response_class=HTMLResponse)
def product_new(request: Request):
    return templates.TemplateResponse(
        "product_new.html",
        {
            "request": request,
            "product_categories": schemas.PRODUCT_CATEGORIES,
            "cooking_requirements": schemas.COOKING_REQUIREMENTS,
        },
    )


@app.get("/dishes/new", response_class=HTMLResponse)
def dish_new(request: Request):
    return templates.TemplateResponse(
        "dish_new.html",
        {
            "request": request,
            "dish_categories": schemas.DISH_CATEGORIES,
        },
    )


@app.get("/products/{product_id}", response_class=HTMLResponse)
def product_detail(request: Request, product_id: int, db: Session = Depends(get_db)):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Продукт не найден")
    product_dict = {
        **product.__dict__,
        "photos": services.deserialize_photos(product.photos),
        "created_at": services.to_utc7(product.created_at),
        "updated_at": services.to_utc7(product.updated_at),
    }
    return templates.TemplateResponse(
        "product_detail.html",
        {
            "request": request,
            "product": product_dict,
            "product_categories": schemas.PRODUCT_CATEGORIES,
            "cooking_requirements": schemas.COOKING_REQUIREMENTS,
        },
    )


@app.get("/dishes/{dish_id}", response_class=HTMLResponse)
def dish_detail(request: Request, dish_id: int, db: Session = Depends(get_db)):
    dish = services.fetch_dish_or_404(db, dish_id)
    dish_dict = services.dish_to_dict(dish)
    return templates.TemplateResponse(
        "dish_detail.html",
        {
            "request": request,
            "dish": dish_dict,
            "dish_categories": schemas.DISH_CATEGORIES,
        },
    )


@app.post("/api/products", response_model=schemas.ProductOut)
def create_product(payload: schemas.ProductCreate, db: Session = Depends(get_db)):
    product = models.Product(
        name=payload.name,
        photos=services.serialize_photos(payload.photos),
        calories=payload.calories,
        proteins=payload.proteins,
        fats=payload.fats,
        carbs=payload.carbs,
        composition=payload.composition,
        category=payload.category,
        cooking_requirement=payload.cooking_requirement,
        is_vegan=payload.is_vegan,
        is_gluten_free=payload.is_gluten_free,
        is_sugar_free=payload.is_sugar_free,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return {
        **product.__dict__,
        "photos": services.deserialize_photos(product.photos),
        "created_at": services.to_utc7(product.created_at),
        "updated_at": services.to_utc7(product.updated_at),
    }


@app.get("/api/products", response_model=list[schemas.ProductOut])
def list_products(
    db: Session = Depends(get_db),
    q: Optional[str] = None,
    category: Optional[str] = None,
    cooking_requirement: Optional[str] = None,
    is_vegan: Optional[bool] = None,
    is_gluten_free: Optional[bool] = None,
    is_sugar_free: Optional[bool] = None,
    sort_by: str = Query(default="name", pattern="^(name|calories|proteins|fats|carbs)$"),
):
    query = db.query(models.Product)
    if q:
        q_norm = q.casefold()
        query = query.filter(func.lower(models.Product.name).like(f"%{q_norm}%"))
    if category:
        query = query.filter(models.Product.category == category)
    if cooking_requirement:
        query = query.filter(models.Product.cooking_requirement == cooking_requirement)
    if is_vegan is not None:
        query = query.filter(models.Product.is_vegan == is_vegan)
    if is_gluten_free is not None:
        query = query.filter(models.Product.is_gluten_free == is_gluten_free)
    if is_sugar_free is not None:
        query = query.filter(models.Product.is_sugar_free == is_sugar_free)

    query = query.order_by(getattr(models.Product, sort_by).asc())
    items = query.all()
    return [
        {
            **p.__dict__,
            "photos": services.deserialize_photos(p.photos),
            "created_at": services.to_utc7(p.created_at),
            "updated_at": services.to_utc7(p.updated_at),
        }
        for p in items
    ]


@app.get("/api/products/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Продукт не найден")
    return {
        **product.__dict__,
        "photos": services.deserialize_photos(product.photos),
        "created_at": services.to_utc7(product.created_at),
        "updated_at": services.to_utc7(product.updated_at),
    }


@app.put("/api/products/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: int, payload: schemas.ProductUpdate, db: Session = Depends(get_db)):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Продукт не найден")
    for field in (
        "name",
        "calories",
        "proteins",
        "fats",
        "carbs",
        "composition",
        "category",
        "cooking_requirement",
        "is_vegan",
        "is_gluten_free",
        "is_sugar_free",
    ):
        setattr(product, field, getattr(payload, field))
    product.photos = services.serialize_photos(payload.photos)
    product.updated_at = services.now_utc()
    db.commit()
    db.refresh(product)
    return {
        **product.__dict__,
        "photos": services.deserialize_photos(product.photos),
        "created_at": services.to_utc7(product.created_at),
        "updated_at": services.to_utc7(product.updated_at),
    }


@app.delete("/api/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Продукт не найден")
    links = (
        db.query(models.DishIngredient)
        .options(joinedload(models.DishIngredient.dish))
        .filter(models.DishIngredient.product_id == product_id)
        .all()
    )
    if links:
        dish_names = sorted({i.dish.name for i in links})
        raise HTTPException(
            status_code=409,
            detail={"message": "Продукт используется в блюдах", "dishes": dish_names},
        )
    db.delete(product)
    db.commit()
    return {"ok": True}


@app.post("/api/dishes/calculate-draft")
def calculate_draft(payload: schemas.DishCreate, db: Session = Depends(get_db)):
    _, category = services.normalize_name_and_category(payload.name, payload.category)
    calories, proteins, fats, carbs, available = services.calculate_draft_macros(db, payload.ingredients)
    return {
        "name": services.normalize_name_and_category(payload.name, payload.category)[0],
        "category": category,
        "calories": calories,
        "proteins": proteins,
        "fats": fats,
        "carbs": carbs,
        "available_flags": available,
    }


@app.post("/api/dishes", response_model=schemas.DishOut)
def create_dish(payload: schemas.DishCreate, db: Session = Depends(get_db)):
    clean_name, final_category = services.normalize_name_and_category(payload.name, payload.category)
    calories, proteins, fats, carbs, available = services.calculate_draft_macros(db, payload.ingredients)
    services.validate_dish_flags(payload, available)
    dish = models.Dish(
        name=clean_name,
        photos=services.serialize_photos(payload.photos),
        calories=payload.calories if payload.calories is not None else calories,
        proteins=payload.proteins if payload.proteins is not None else proteins,
        fats=payload.fats if payload.fats is not None else fats,
        carbs=payload.carbs if payload.carbs is not None else carbs,
        portion_size=payload.portion_size,
        category=final_category,
        is_vegan=payload.is_vegan and available["is_vegan"],
        is_gluten_free=payload.is_gluten_free and available["is_gluten_free"],
        is_sugar_free=payload.is_sugar_free and available["is_sugar_free"],
    )
    db.add(dish)
    db.flush()
    for item in payload.ingredients:
        db.add(models.DishIngredient(dish_id=dish.id, product_id=item.product_id, amount_grams=item.amount_grams))
    db.commit()
    return services.dish_to_dict(services.fetch_dish_or_404(db, dish.id))


@app.get("/api/dishes", response_model=list[schemas.DishOut])
def list_dishes(
    db: Session = Depends(get_db),
    q: Optional[str] = None,
    category: Optional[str] = None,
    is_vegan: Optional[bool] = None,
    is_gluten_free: Optional[bool] = None,
    is_sugar_free: Optional[bool] = None,
):
    query = db.query(models.Dish).options(
        joinedload(models.Dish.ingredients).joinedload(models.DishIngredient.product)
    )
    if q:
        q_norm = q.casefold()
        query = query.filter(func.lower(models.Dish.name).like(f"%{q_norm}%"))
    if category:
        query = query.filter(models.Dish.category == category)
    if is_vegan is not None:
        query = query.filter(models.Dish.is_vegan == is_vegan)
    if is_gluten_free is not None:
        query = query.filter(models.Dish.is_gluten_free == is_gluten_free)
    if is_sugar_free is not None:
        query = query.filter(models.Dish.is_sugar_free == is_sugar_free)
    return [services.dish_to_dict(d) for d in query.order_by(models.Dish.name.asc()).all()]


@app.get("/api/dishes/{dish_id}", response_model=schemas.DishOut)
def get_dish(dish_id: int, db: Session = Depends(get_db)):
    return services.dish_to_dict(services.fetch_dish_or_404(db, dish_id))


@app.put("/api/dishes/{dish_id}", response_model=schemas.DishOut)
def update_dish(dish_id: int, payload: schemas.DishUpdate, db: Session = Depends(get_db)):
    dish = services.fetch_dish_or_404(db, dish_id)
    clean_name, final_category = services.normalize_name_and_category(payload.name, payload.category)
    calories, proteins, fats, carbs, available = services.calculate_draft_macros(db, payload.ingredients)
    services.validate_dish_flags(payload, available)

    dish.name = clean_name
    dish.photos = services.serialize_photos(payload.photos)
    dish.calories = payload.calories if payload.calories is not None else calories
    dish.proteins = payload.proteins if payload.proteins is not None else proteins
    dish.fats = payload.fats if payload.fats is not None else fats
    dish.carbs = payload.carbs if payload.carbs is not None else carbs
    dish.portion_size = payload.portion_size
    dish.category = final_category
    dish.is_vegan = payload.is_vegan and available["is_vegan"]
    dish.is_gluten_free = payload.is_gluten_free and available["is_gluten_free"]
    dish.is_sugar_free = payload.is_sugar_free and available["is_sugar_free"]
    dish.updated_at = services.now_utc()

    dish.ingredients.clear()
    db.flush()
    for item in payload.ingredients:
        dish.ingredients.append(models.DishIngredient(product_id=item.product_id, amount_grams=item.amount_grams))
    db.commit()
    return services.dish_to_dict(services.fetch_dish_or_404(db, dish.id))


@app.delete("/api/dishes/{dish_id}")
def delete_dish(dish_id: int, db: Session = Depends(get_db)):
    dish = db.get(models.Dish, dish_id)
    if not dish:
        raise HTTPException(status_code=404, detail="Блюдо не найдено")
    db.delete(dish)
    db.commit()
    return {"ok": True}

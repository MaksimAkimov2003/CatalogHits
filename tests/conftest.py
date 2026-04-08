"""
Общие фикстуры и вспомогательные функции для API-тестов бэкенда «Книга рецептов».

Тест-дизайн (на уровне всего набора):
- **Эквивалентное разбиение (EP)**: валидные и невалидные классы входов (имя, БЖУ, категории,
  состав блюда, флаги и т.д.).
- **Анализ граничных значений (BVA)**: проверки у границ допустимых интервалов и рядом
  с ними (например, min_length имени, сумма БЖУ = 100 г, ``portion_size > 0``, число фото ≤ 5).

Инструменты: ``pytest``, ``starlette.testclient.TestClient`` (HTTP поверх ASGI), SQLAlchemy.

**Важно (интеграционные API-тесты):** тесты используют **ту же самую** БД, что и приложение
по умолчанию — файл ``recipe_book.db``. База **не очищается** перед тестами.

Безопасность: тесты обязаны работать так, чтобы не затрагивать данные пользователей.
Для этого все создаваемые тестом сущности получают уникальный суффикс в названии, чтобы:
- не пересекаться с пользовательскими данными по имени;
- можно было изолировать выборки (через `q`) при проверках списка/сортировки.

Важно: по требованию задания в этом варианте тесты **не удаляют** данные из `recipe_book.db`
в teardown.
"""

from __future__ import annotations

import contextlib
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402
import httpx  # noqa: E402


def _pick_free_port() -> int:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="session")
def server_base_url():
    """
    Поднимаем реальный Uvicorn (отдельный процесс) и тестируем по настоящему HTTP,
    максимально приближенно к продовому запуску.
    """
    port = _pick_free_port()
    base_url = f"http://127.0.0.1:{port}"

    # Стартуем uvicorn через текущий python из venv.
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    # Ждём готовности сервера (poll endpoint).
    deadline = time.time() + 10.0
    last_exc: Exception | None = None
    while time.time() < deadline:
        if proc.poll() is not None:
            out = (proc.stdout.read() if proc.stdout else "")
            raise RuntimeError(f"uvicorn exited early (code={proc.returncode}). Output:\n{out}")
        try:
            r = httpx.get(f"{base_url}/api/products", timeout=1.0)
            if r.status_code in (200, 422):  # 422 возможно, если что-то не так с параметрами, но маршрут живой
                last_exc = None
                break
        except Exception as e:  # noqa: BLE001 - в ожидании старта
            last_exc = e
        time.sleep(0.2)
    else:
        out = (proc.stdout.read() if proc.stdout else "")
        raise RuntimeError(f"uvicorn did not become ready. Last error: {last_exc}. Output:\n{out}")

    try:
        yield base_url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:  # noqa: BLE001
            proc.kill()


@pytest.fixture
def client(server_base_url: str):
    """Реальный HTTP-клиент как в проде (httpx)."""
    with httpx.Client(base_url=server_base_url, timeout=5.0) as c:
        yield c


def product_json(**overrides: Any) -> dict[str, Any]:
    """Базовый валидный JSON продукта; переопределения задают конкретные поля для EP/BVA."""
    base: dict[str, Any] = {
        "name": "Тестовый продукт",
        "photos": [],
        "calories": 100.0,
        "proteins": 10.0,
        "fats": 5.0,
        "carbs": 20.0,
        "composition": None,
        "category": "Овощи",
        "cooking_requirement": "Готовый к употреблению",
        "is_vegan": False,
        "is_gluten_free": False,
        "is_sugar_free": False,
    }
    base.update(overrides)
    return base


def dish_json(product_id: int, **overrides: Any) -> dict[str, Any]:
    """Базовый валидный JSON блюда с одним ингредиентом."""
    base: dict[str, Any] = {
        "name": "Тестовое блюдо",
        "photos": [],
        "ingredients": [{"product_id": product_id, "amount_grams": 100.0}],
        "portion_size": 100.0,
        "category": "Второе",
        "calories": None,
        "proteins": None,
        "fats": None,
        "carbs": None,
        "is_vegan": False,
        "is_gluten_free": False,
        "is_sugar_free": False,
    }
    base.update(overrides)
    return base


def unique_token() -> str:
    """Короткий уникальный токен для имён/поиска в тестах (без каких-либо автопереименований)."""
    return uuid4().hex[:10]

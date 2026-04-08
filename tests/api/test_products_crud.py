"""
API-тесты для продуктов: **просмотр/редактирование/удаление** (CRUD) (EP).
"""

from __future__ import annotations

import httpx

from tests.conftest import product_json, unique_token


class TestProductReadUpdateDelete:
    """EP: существующий vs несуществующий ресурс; корректное обновление полей."""

    def test_get_product_404(self, client: httpx.Client):
        response = client.get("/api/products/99999")
        assert response.status_code == 404

    def test_update_product_404(self, client: httpx.Client):
        response = client.put("/api/products/99999", json=product_json(name="Новое имя"))
        assert response.status_code == 404

    def test_delete_product_404(self, client: httpx.Client):
        response = client.delete("/api/products/99999")
        assert response.status_code == 404

    def test_create_and_update(self, client: httpx.Client):
        token = unique_token()
        create_r = client.post("/api/products", json=product_json(name=f"Горох {token}", calories=50.0))
        pid = int(create_r.json()["id"])

        get_r = client.get(f"/api/products/{pid}")

        assert (get_r.status_code, get_r.json().get("name")) == (200, f"Горох {token}")

        put_r = client.put(
            f"/api/products/{pid}",
            json=product_json(name=f"Горох обновлённый {token}", calories=55.0),
        )

        assert (put_r.status_code, put_r.json().get("name"), put_r.json().get("calories")) == (
            200,
            f"Горох обновлённый {token}",
            55.0,
        )


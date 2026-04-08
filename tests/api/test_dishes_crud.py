"""
API-тесты для блюд: **просмотр/редактирование/удаление** (CRUD) (EP).
"""

from __future__ import annotations

import httpx

from tests.conftest import dish_json, product_json, unique_token


class TestDishReadUpdateDelete:
    """CRUD-хвост: получение 404, обновление, удаление."""

    def test_get_dish_404(self, client: httpx.Client):
        response = client.get("/api/dishes/99999")
        assert response.status_code == 404

    def test_update_dish(self, client: httpx.Client):
        token = unique_token()
        pid = int(client.post("/api/products", json=product_json(name=f"Prod {token}")).json()["id"])
        dish_id = int(client.post("/api/dishes", json=dish_json(pid, name=f"Жаркое {token}")).json()["id"])

        upd = client.put(
            f"/api/dishes/{dish_id}",
            json=dish_json(pid, name="Жаркое новое", portion_size=200.0),
        )
        assert (upd.status_code, upd.json().get("portion_size")) == (200, 200.0)

    def test_delete_dish(self, client: httpx.Client):
        token = unique_token()
        pid = int(client.post("/api/products", json=product_json(name=f"Prod {token}")).json()["id"])
        dish_id = int(client.post("/api/dishes", json=dish_json(pid, name=f"Жаркое {token}")).json()["id"])

        del_r = client.delete(f"/api/dishes/{dish_id}")
        get_after_del = client.get(f"/api/dishes/{dish_id}")
        assert (del_r.status_code, get_after_del.status_code) == (200, 404)


const PRODUCT_CATEGORIES = ["Замороженный", "Мясной", "Овощи", "Зелень", "Специи", "Крупы", "Консервы", "Жидкость", "Сладости"];
const COOKING_REQUIREMENTS = ["Готовый к употреблению", "Полуфабрикат", "Требует приготовления"];
const DISH_CATEGORIES = ["Десерт", "Первое", "Второе", "Напиток", "Салат", "Суп", "Перекус"];

function byId(id) {
  return document.getElementById(id);
}

function fillSelect(id, values, withEmpty = false) {
  const select = byId(id);
  if (!select) return;
  if (withEmpty) {
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "Не выбрано";
    select.appendChild(empty);
  }
  values.forEach(v => {
    const option = document.createElement("option");
    option.value = v;
    option.textContent = v;
    select.appendChild(option);
  });
}

// Filters: explicit "all" options look better than blank rows.
fillSelect("p-filter-category", ["Все категории", ...PRODUCT_CATEGORIES]);
const pCat = byId("p-filter-category");
if (pCat) pCat.querySelector("option").value = "";
fillSelect("p-filter-cooking", ["Любая готовка", ...COOKING_REQUIREMENTS]);
const pCook = byId("p-filter-cooking");
if (pCook) pCook.querySelector("option").value = "";
fillSelect("d-filter-category", ["Все категории", ...DISH_CATEGORIES]);
const dCat = byId("d-filter-category");
if (dCat) dCat.querySelector("option").value = "";

const productsSection = byId("products-section");
const dishesSection = byId("dishes-section");
const tabProducts = byId("tab-products");
const tabDishes = byId("tab-dishes");
if (tabProducts && tabDishes && productsSection && dishesSection) {
  tabProducts.onclick = () => {
    productsSection.classList.remove("hidden");
    dishesSection.classList.add("hidden");
  };
  tabDishes.onclick = () => {
    dishesSection.classList.remove("hidden");
    productsSection.classList.add("hidden");
  };
}

function parseCsvUrls(value) {
  const s = String(value || "").trim();
  if (!s) return [];

  const out = [];
  let cur = "";
  let inDataUrl = false;
  let dataCommaConsumed = false;

  for (let i = 0; i < s.length; i++) {
    const ch = s[i];

    if (ch === "," || ch === "\n" || ch === ";") {
      // Keep the mandatory comma inside a data: URL (`data:...,...`) as part of the token.
      if (ch === "," && inDataUrl && !dataCommaConsumed) {
        cur += ch;
        dataCommaConsumed = true;
        continue;
      }

      const trimmed = cur.trim();
      if (trimmed) out.push(trimmed);
      cur = "";
      inDataUrl = false;
      dataCommaConsumed = false;
      continue;
    }

    cur += ch;

    if (!inDataUrl && cur.trimStart().startsWith("data:")) {
      inDataUrl = true;
      dataCommaConsumed = false;
    }
  }

  const last = cur.trim();
  if (last) out.push(last);
  return out;
}

function numOrNull(v) {
  const trimmed = String(v).trim();
  if (!trimmed) return null;
  return Number(trimmed);
}

function dishIngredientRowTemplate(products, selectedId, amount) {
  const options = products.map(p => `<option value="${p.id}" ${String(p.id) === String(selectedId) ? "selected" : ""}>${p.name}</option>`).join("");
  return `
    <div class="ingredient-row">
      <div class="field">
        <label>Продукт</label>
        <select class="d-ingredient-product">${options}</select>
      </div>
      <div class="field">
        <label>Граммы</label>
        <input class="d-ingredient-amount" type="number" step="0.01" min="0.01" value="${amount ?? ""}" />
      </div>
      <button type="button" class="d-remove-ingredient">Удалить</button>
    </div>
  `;
}

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail ? JSON.stringify(data.detail) : `HTTP ${response.status}`);
  }
  return response.json();
}

function renderBadges(entity) {
  const badges = [];
  if (entity.is_vegan) badges.push(`<span class="badge vegan">Веган</span>`);
  if (entity.is_gluten_free) badges.push(`<span class="badge gluten">Без глютена</span>`);
  if (entity.is_sugar_free) badges.push(`<span class="badge sugar">Без сахара</span>`);
  if (!badges.length) return "";
  return `<div class="badges">${badges.join("")}</div>`;
}

function renderThumb(photos) {
  const url = Array.isArray(photos) && photos.length ? photos[0] : null;
  if (!url) return "";
  const escaped = String(url).replaceAll('"', "&quot;");
  return `<img class="thumb" src="${escaped}" alt="Фото" loading="lazy" />`;
}

async function loadProducts() {
  const q = encodeURIComponent(byId("p-search")?.value || "");
  const sortBy = encodeURIComponent(byId("p-sort")?.value || "name");
  const category = encodeURIComponent(byId("p-filter-category")?.value || "");
  const cooking = encodeURIComponent(byId("p-filter-cooking")?.value || "");
  const vegan = !!byId("p-filter-vegan")?.checked;
  const gluten = !!byId("p-filter-gluten")?.checked;
  const sugar = !!byId("p-filter-sugar")?.checked;

  const params = new URLSearchParams();
  if (q) params.set("q", decodeURIComponent(q));
  params.set("sort_by", decodeURIComponent(sortBy));
  if (category) params.set("category", decodeURIComponent(category));
  if (cooking) params.set("cooking_requirement", decodeURIComponent(cooking));
  if (vegan) params.set("is_vegan", "true");
  if (gluten) params.set("is_gluten_free", "true");
  if (sugar) params.set("is_sugar_free", "true");

  const products = await api(`/api/products?${params.toString()}`);
  const list = byId("products-list");
  if (!list) return;
  list.innerHTML = "";
  products.forEach(p => {
    const div = document.createElement("div");
    div.className = "list-item";
    div.innerHTML = `
      <div class="row">
        ${renderThumb(p.photos)}
        <div class="meta">
          <div><a href="/products/${p.id}"><b>${p.name}</b></a> | ${p.category}</div>
          <div>КБЖУ: ${p.calories}/${p.proteins}/${p.fats}/${p.carbs}</div>
          ${renderBadges(p)}
          <div style="margin-top:6px">
            <a href="/products/${p.id}" style="display:inline-block; padding:6px 10px; border:1px solid #ddd; border-radius:10px; background:#fff; text-decoration:none; margin-right:8px">Открыть</a>
            <button data-id="${p.id}" class="delete-product">Удалить</button>
          </div>
        </div>
      </div>
    `;
    list.appendChild(div);
  });
  document.querySelectorAll(".delete-product").forEach(btn => {
    btn.onclick = async () => {
      try {
        await api(`/api/products/${btn.dataset.id}`, { method: "DELETE" });
        await loadProducts();
      } catch (e) {
        alert(e.message);
      }
    };
  });
}

async function loadDishes() {
  const q = encodeURIComponent(byId("d-search")?.value || "");
  const category = encodeURIComponent(byId("d-filter-category")?.value || "");
  const vegan = !!byId("d-filter-vegan")?.checked;
  const gluten = !!byId("d-filter-gluten")?.checked;
  const sugar = !!byId("d-filter-sugar")?.checked;

  const params = new URLSearchParams();
  if (q) params.set("q", decodeURIComponent(q));
  if (category) params.set("category", decodeURIComponent(category));
  if (vegan) params.set("is_vegan", "true");
  if (gluten) params.set("is_gluten_free", "true");
  if (sugar) params.set("is_sugar_free", "true");

  const dishes = await api(`/api/dishes?${params.toString()}`);
  const list = byId("dishes-list");
  if (!list) return;
  list.innerHTML = "";
  dishes.forEach(d => {
    const composition = d.ingredients.map(i => `${i.product_name} (${i.amount_grams}г)`).join(", ");
    const div = document.createElement("div");
    div.className = "list-item";
    div.innerHTML = `
      <div class="row">
        ${renderThumb(d.photos)}
        <div class="meta">
          <div><a href="/dishes/${d.id}"><b>${d.name}</b></a> | ${d.category}</div>
          <div>КБЖУ: ${d.calories}/${d.proteins}/${d.fats}/${d.carbs}</div>
          ${renderBadges(d)}
          <div style="margin-top:4px">${composition}</div>
          <div style="margin-top:6px">
            <a href="/dishes/${d.id}" style="display:inline-block; padding:6px 10px; border:1px solid #ddd; border-radius:10px; background:#fff; text-decoration:none; margin-right:8px">Открыть</a>
            <button data-id="${d.id}" class="delete-dish">Удалить</button>
          </div>
        </div>
      </div>
    `;
    list.appendChild(div);
  });
  document.querySelectorAll(".delete-dish").forEach(btn => {
    btn.onclick = async () => {
      try {
        await api(`/api/dishes/${btn.dataset.id}`, { method: "DELETE" });
        await loadDishes();
      } catch (e) {
        alert(e.message);
      }
    };
  });
}

loadProducts();
loadDishes();

const reloadProductsBtn = byId("reload-products");
if (reloadProductsBtn) reloadProductsBtn.onclick = loadProducts;
const reloadDishesBtn = byId("reload-dishes");
if (reloadDishesBtn) reloadDishesBtn.onclick = loadDishes;

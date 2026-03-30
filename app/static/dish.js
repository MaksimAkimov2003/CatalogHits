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

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data && data.detail ? data.detail : `HTTP ${response.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail, null, 2));
  }
  return data;
}

function setMessage(kind, text) {
  const el = document.getElementById("msg");
  el.className = `msg ${kind}`;
  el.textContent = text;
}

function renderPhotosPreview(urls) {
  const container = document.getElementById("photos-preview");
  container.innerHTML = "";
  urls.slice(0, 5).forEach(url => {
    const img = document.createElement("img");
    img.className = "thumb";
    img.loading = "lazy";
    img.alt = "Фото";
    img.src = url;
    container.appendChild(img);
  });
}

function setFlagAvailability(available) {
  const flags = [
    ["is_vegan", "is_vegan"],
    ["is_gluten_free", "is_gluten_free"],
    ["is_sugar_free", "is_sugar_free"],
  ];
  flags.forEach(([id, key]) => {
    const checkbox = document.getElementById(id);
    const can = !!available[key];
    checkbox.disabled = !can;
    if (!can) checkbox.checked = false;
  });

  const pills = document.getElementById("available-flags").querySelectorAll(".pill");
  const mapping = [
    ["is_vegan", "Веган"],
    ["is_gluten_free", "Без глютена"],
    ["is_sugar_free", "Без сахара"],
  ];
  pills.forEach((pill, idx) => {
    const key = mapping[idx][0];
    pill.classList.remove("ok", "no");
    pill.classList.add(available[key] ? "ok" : "no");
  });
}

function ingredientRowTemplate(products, selectedId, amount) {
  const options = products.map(p => `<option value="${p.id}" ${String(p.id) === String(selectedId) ? "selected" : ""}>${p.name}</option>`).join("");
  return `
    <div class="ingredient-row">
      <div class="field">
        <label>Продукт</label>
        <select class="ingredient-product">
          ${options}
        </select>
      </div>
      <div class="field">
        <label>Граммы</label>
        <input class="ingredient-amount" type="number" step="0.01" min="0.01" value="${amount ?? ""}" />
      </div>
      <button type="button" class="remove-ingredient">Удалить</button>
    </div>
  `;
}

function readIngredientsFromUI() {
  const rows = Array.from(document.querySelectorAll("#ingredients-container .ingredient-row"));
  return rows.map(r => ({
    product_id: Number(r.querySelector(".ingredient-product").value),
    amount_grams: Number(r.querySelector(".ingredient-amount").value),
  })).filter(x => x.product_id && x.amount_grams > 0);
}

function numOrNullFromInput(id) {
  const raw = String(document.getElementById(id).value ?? "").trim();
  if (!raw) return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

function collectDishPayload({ manualMacrosOverride } = { manualMacrosOverride: false }) {
  return {
    name: document.getElementById("name").value,
    photos: parseCsvUrls(document.getElementById("photos").value).slice(0, 5),
    ingredients: readIngredientsFromUI(),
    portion_size: Number(document.getElementById("portion_size").value),
    category: document.getElementById("category").value || null,
    // If user didn't override macros manually, send nulls so backend always recalculates on save.
    calories: manualMacrosOverride ? numOrNullFromInput("calories") : null,
    proteins: manualMacrosOverride ? numOrNullFromInput("proteins") : null,
    fats: manualMacrosOverride ? numOrNullFromInput("fats") : null,
    carbs: manualMacrosOverride ? numOrNullFromInput("carbs") : null,
    is_vegan: document.getElementById("is_vegan").checked,
    is_gluten_free: document.getElementById("is_gluten_free").checked,
    is_sugar_free: document.getElementById("is_sugar_free").checked,
  };
}

async function calculateDraftAndApply() {
  const payload = collectDishPayload({ manualMacrosOverride: false });
  const draft = await api("/api/dishes/calculate-draft", {
    method: "POST",
    body: JSON.stringify({
      ...payload,
      // allow user override: draft endpoint accepts optional macros in payload anyway
      calories: null,
      proteins: null,
      fats: null,
      carbs: null,
    }),
  });
  // Apply draft values only when macros are not manually overridden.
  if (!window.__dish_manual_macros_override) {
    document.getElementById("calories").value = String(draft.calories.toFixed(2));
    document.getElementById("proteins").value = String(draft.proteins.toFixed(2));
    document.getElementById("fats").value = String(draft.fats.toFixed(2));
    document.getElementById("carbs").value = String(draft.carbs.toFixed(2));
  }
  setFlagAvailability(draft.available_flags);
}

async function init() {
  const dishId = document.getElementById("dish-form").dataset.dishId;
  const initialDish = await api(`/api/dishes/${dishId}`);
  const products = await api("/api/products?sort_by=name");

  // Track whether user manually overrides macros fields.
  window.__dish_manual_macros_override = false;
  ["calories", "proteins", "fats", "carbs"].forEach((id) => {
    const el = document.getElementById(id);
    el.addEventListener("input", () => {
      window.__dish_manual_macros_override = true;
    });
  });

  const container = document.getElementById("ingredients-container");
  container.innerHTML = "";
  (initialDish.ingredients || []).forEach(i => {
    const wrapper = document.createElement("div");
    wrapper.innerHTML = ingredientRowTemplate(products, i.product_id, i.amount_grams);
    container.appendChild(wrapper.firstElementChild);
  });

  function wireRemoveButtons() {
    document.querySelectorAll(".remove-ingredient").forEach(btn => {
      btn.onclick = () => {
        btn.closest(".ingredient-row").remove();
        // Ingredient list changed: auto-recalc draft macros and flag availability.
        calculateDraftAndApply().catch(() => {});
      };
    });
  }

  wireRemoveButtons();

  document.getElementById("add-ingredient").onclick = () => {
    const wrapper = document.createElement("div");
    wrapper.innerHTML = ingredientRowTemplate(products, products[0]?.id, 100);
    container.appendChild(wrapper.firstElementChild);
    wireRemoveButtons();
    // Ingredient list changed: auto-recalc draft macros and flag availability.
    calculateDraftAndApply().catch(() => {});
  };

  document.getElementById("preview-photos").onclick = () => {
    renderPhotosPreview(parseCsvUrls(document.getElementById("photos").value));
  };

  document.getElementById("calc-draft").onclick = async () => {
    try {
      setMessage("", "");
      await calculateDraftAndApply();
      setMessage("ok", "Черновик КБЖУ пересчитан, доступность флагов обновлена");
    } catch (e) {
      setMessage("err", e.message);
    }
  };

  // Keep flags in sync when ingredients change.
  container.addEventListener("change", async (e) => {
    if (e.target.classList.contains("ingredient-product") || e.target.classList.contains("ingredient-amount")) {
      try {
        await calculateDraftAndApply();
      } catch {
        // ignore transient invalid state while user edits
      }
    }
  });

  setFlagAvailability(initialDish.available_flags || {});

  document.getElementById("dish-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    setMessage("", "");
    const dishId = e.target.dataset.dishId;

    try {
      const payload = collectDishPayload({ manualMacrosOverride: window.__dish_manual_macros_override });
      const updated = await api(`/api/dishes/${dishId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      document.title = `Блюдо — ${updated.name}`;
      document.querySelector(".title").textContent = `Блюдо: ${updated.name}`;
      document.getElementById("updated-at").textContent = updated.updated_at || "—";
      renderPhotosPreview(updated.photos || []);
      setFlagAvailability(updated.available_flags || {});
      // After save, consider current macros as auto unless user changes again.
      window.__dish_manual_macros_override = false;
      setMessage("ok", "Сохранено");
    } catch (err) {
      setMessage("err", err.message);
    }
  });
}

init().catch((e) => setMessage("err", e.message));


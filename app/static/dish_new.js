function parseCsvUrls(value) {
  const s = String(value || "").trim();
  if (!s) return [];
  return s.split(",").map(v => v.trim()).filter(Boolean);
}

function numOrNullFromInput(id) {
  const raw = String(document.getElementById(id).value ?? "").trim();
  if (!raw) return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
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
}

function ingredientRowTemplate(products, selectedId, amount) {
  const options = products.map(p => `<option value="${p.id}" ${String(p.id) === String(selectedId) ? "selected" : ""}>${p.name}</option>`).join("");
  return `
    <div class="ingredient-row">
      <div class="field">
        <label>Продукт</label>
        <select class="ingredient-product">${options}</select>
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

function collectDishPayload() {
  return {
    name: document.getElementById("name").value,
    photos: parseCsvUrls(document.getElementById("photos").value).slice(0, 5),
    ingredients: readIngredientsFromUI(),
    portion_size: Number(document.getElementById("portion_size").value),
    category: document.getElementById("category").value || null,
    calories: numOrNullFromInput("calories"),
    proteins: numOrNullFromInput("proteins"),
    fats: numOrNullFromInput("fats"),
    carbs: numOrNullFromInput("carbs"),
    is_vegan: document.getElementById("is_vegan").checked,
    is_gluten_free: document.getElementById("is_gluten_free").checked,
    is_sugar_free: document.getElementById("is_sugar_free").checked,
  };
}

async function calculateDraftAndApply() {
  const payload = collectDishPayload();
  const draft = await api("/api/dishes/calculate-draft", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  // Fill draft values only if user left them empty.
  if (!String(document.getElementById("calories").value || "").trim()) document.getElementById("calories").value = draft.calories.toFixed(2);
  if (!String(document.getElementById("proteins").value || "").trim()) document.getElementById("proteins").value = draft.proteins.toFixed(2);
  if (!String(document.getElementById("fats").value || "").trim()) document.getElementById("fats").value = draft.fats.toFixed(2);
  if (!String(document.getElementById("carbs").value || "").trim()) document.getElementById("carbs").value = draft.carbs.toFixed(2);

  setFlagAvailability(draft.available_flags);
  return draft;
}

async function init() {
  const products = await api("/api/products?sort_by=name");
  const container = document.getElementById("ingredients-container");
  container.innerHTML = "";

  function wireRemoveButtons() {
    document.querySelectorAll(".remove-ingredient").forEach(btn => {
      btn.onclick = () => {
        btn.closest(".ingredient-row").remove();
        calculateDraftAndApply().catch(() => {});
      };
    });
  }

  function addRow(selectedId, amount) {
    const wrapper = document.createElement("div");
    wrapper.innerHTML = ingredientRowTemplate(products, selectedId ?? products[0]?.id, amount ?? 100);
    container.appendChild(wrapper.firstElementChild);
    wireRemoveButtons();
    calculateDraftAndApply().catch(() => {});
  }

  // start with 1 row
  addRow(products[0]?.id, 100);

  document.getElementById("add-ingredient").onclick = () => addRow(products[0]?.id, 100);

  container.addEventListener("change", async (e) => {
    if (e.target.classList.contains("ingredient-product") || e.target.classList.contains("ingredient-amount")) {
      calculateDraftAndApply().catch(() => {});
    }
  });

  document.getElementById("preview-photos").onclick = () => {
    renderPhotosPreview(parseCsvUrls(document.getElementById("photos").value));
  };

  document.getElementById("calc-draft").onclick = async () => {
    try {
      setMessage("", "");
      await calculateDraftAndApply();
      setMessage("ok", "Черновик рассчитан, доступность флагов обновлена");
    } catch (e) {
      setMessage("err", e.message);
    }
  };

  document.getElementById("dish-new-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    setMessage("", "");
    try {
      // Ensure we have a draft at least once (best effort).
      await calculateDraftAndApply().catch(() => {});

      const payload = collectDishPayload();
      const created = await api("/api/dishes", { method: "POST", body: JSON.stringify(payload) });
      setMessage("ok", `Создано. Открываю блюдо #${created.id}…`);
      window.location.href = `/dishes/${created.id}`;
    } catch (err) {
      setMessage("err", err.message);
    }
  });
}

init().catch((e) => setMessage("err", e.message));


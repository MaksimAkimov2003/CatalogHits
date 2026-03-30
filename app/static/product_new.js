function parseCsvUrls(value) {
  const s = String(value || "").trim();
  if (!s) return [];
  return s.split(",").map(v => v.trim()).filter(Boolean);
}

function requireNumberFromInput(id, label) {
  const raw = String(document.getElementById(id).value ?? "").trim();
  if (!raw) throw new Error(`Заполните поле: ${label}`);
  const n = Number(raw);
  if (!Number.isFinite(n)) throw new Error(`Некорректное число в поле: ${label}`);
  return n;
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

document.getElementById("preview-photos").onclick = () => {
  renderPhotosPreview(parseCsvUrls(document.getElementById("photos").value));
};

document.getElementById("product-new-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  setMessage("", "");

  try {
    const payload = {
      name: document.getElementById("name").value,
      photos: parseCsvUrls(document.getElementById("photos").value).slice(0, 5),
      calories: requireNumberFromInput("calories", "Ккал/100г"),
      proteins: requireNumberFromInput("proteins", "Белки/100г"),
      fats: requireNumberFromInput("fats", "Жиры/100г"),
      carbs: requireNumberFromInput("carbs", "Углеводы/100г"),
      composition: document.getElementById("composition").value || null,
      category: document.getElementById("category").value,
      cooking_requirement: document.getElementById("cooking").value,
      is_vegan: document.getElementById("is_vegan").checked,
      is_gluten_free: document.getElementById("is_gluten_free").checked,
      is_sugar_free: document.getElementById("is_sugar_free").checked,
    };

    const created = await api("/api/products", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    setMessage("ok", `Создано. Открываю продукт #${created.id}…`);
    window.location.href = `/products/${created.id}`;
  } catch (err) {
    setMessage("err", err.message);
  }
});


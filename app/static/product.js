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

document.getElementById("preview-photos").onclick = () => {
  const urls = parseCsvUrls(document.getElementById("photos").value);
  renderPhotosPreview(urls);
};

document.getElementById("product-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  setMessage("", "");

  const productId = e.target.dataset.productId;
  const payload = {
    name: document.getElementById("name").value,
    photos: parseCsvUrls(document.getElementById("photos").value).slice(0, 5),
    calories: Number(document.getElementById("calories").value),
    proteins: Number(document.getElementById("proteins").value),
    fats: Number(document.getElementById("fats").value),
    carbs: Number(document.getElementById("carbs").value),
    composition: document.getElementById("composition").value || null,
    category: document.getElementById("category").value,
    cooking_requirement: document.getElementById("cooking").value,
    is_vegan: document.getElementById("is_vegan").checked,
    is_gluten_free: document.getElementById("is_gluten_free").checked,
    is_sugar_free: document.getElementById("is_sugar_free").checked,
  };

  try {
    const updated = await api(`/api/products/${productId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    document.title = `Продукт — ${updated.name}`;
    document.querySelector(".title").textContent = `Продукт: ${updated.name}`;
    document.getElementById("updated-at").textContent = updated.updated_at || "—";
    renderPhotosPreview(updated.photos || []);
    setMessage("ok", "Сохранено");
  } catch (err) {
    setMessage("err", err.message);
  }
});


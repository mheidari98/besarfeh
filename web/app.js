"use strict";

// --- provider metadata (label + brand color, used only to encode the source) ---
const PROV = {
  mci: { label: "همراه اول", varc: "--mci" },
  mtn: { label: "ایرانسل", varc: "--mtn", tagMod: "tag--mtn" },
  rightel: { label: "رایتل", varc: "--rightel" },
};
const ORDER = ["mci", "mtn", "rightel"];

// --- formatting (Persian digits + grouping) ---
const faNum = (n, frac = 0) =>
  new Intl.NumberFormat("fa-IR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: frac,
    useGrouping: true,
  }).format(n);

const toman = (n) => faNum(Math.round(n));
const volume = (mb) =>
  mb == null ? "—" : mb >= 1024 ? `${faNum(mb / 1024, 1)} گیگ` : `${faNum(mb)} مگ`;
const parseDigits = (s) =>
  Number(
    String(s)
      .replace(/[۰-۹]/g, (d) => "۰۱۲۳۴۵۶۷۸۹".indexOf(d))
      .replace(/[٠-٩]/g, (d) => "٠١٢٣٤٥٦٧٨٩".indexOf(d))
      .replace(/[^\d]/g, ""),
  ) || 0;

// price/MB -> color, green (cheap) to red (expensive) across the dataset
function heatScale(values) {
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  return (v) => {
    const t = hi === lo ? 0 : (v - lo) / (hi - lo);
    return `hsl(${Math.round(150 * (1 - t))} 62% 38%)`;
  };
}

// --- state ---
let ALL = [];
let HEAT = () => "var(--ink)";
const state = { providers: new Set(), q: "", sort: "ppm", budget: 100000 };

const $ = (s) => document.querySelector(s);

async function load() {
  try {
    const res = await fetch("./data/packages.json", { cache: "no-cache" });
    const json = await res.json();
    ALL = json.packages || [];
    const rates = ALL.filter((p) => p.price_per_mb != null).map((p) => p.price_per_mb);
    HEAT = heatScale(rates);
    const when = res.headers.get("last-modified");
    $("#meta").textContent =
      `${faNum(ALL.length)} بسته` +
      (when ? ` · به‌روزرسانی ${new Date(when).toLocaleDateString("fa-IR")}` : "");
  } catch {
    $("#board").innerHTML = "";
    $("#empty").hidden = false;
    $("#empty").textContent = "دریافت داده‌ها ناموفق بود. کمی بعد دوباره امتحان کن.";
    return;
  }
  buildChips();
  bindControls();
  renderAnswer();
  renderBoard();
}

function buildChips() {
  const box = $("#providers");
  const mk = (key, label, varc) => {
    const b = document.createElement("button");
    b.className = "chip";
    b.type = "button";
    b.dataset.key = key;
    b.setAttribute("aria-pressed", key === "all" ? "true" : "false");
    b.innerHTML =
      (varc ? `<span class="chip__dot" style="--c:var(${varc})"></span>` : "") + label;
    box.appendChild(b);
  };
  mk("all", "همه");
  ORDER.forEach((k) => mk(k, PROV[k].label, PROV[k].varc));

  box.addEventListener("click", (e) => {
    const btn = e.target.closest(".chip");
    if (!btn) return;
    const key = btn.dataset.key;
    if (key === "all") state.providers.clear();
    else {
      state.providers.has(key) ? state.providers.delete(key) : state.providers.add(key);
    }
    [...box.children].forEach((c) =>
      c.setAttribute(
        "aria-pressed",
        c.dataset.key === "all"
          ? String(state.providers.size === 0)
          : String(state.providers.has(c.dataset.key)),
      ),
    );
    renderBoard();
  });
}

function bindControls() {
  const budget = $("#budget");
  state.budget = parseDigits(budget.value);
  budget.addEventListener("input", () => {
    state.budget = parseDigits(budget.value);
    renderAnswer();
  });
  budget.addEventListener("change", () => {
    budget.value = state.budget ? faNum(state.budget) : "";
  });
  $("#search").addEventListener("input", (e) => {
    state.q = e.target.value.trim();
    renderBoard();
  });
  $("#sort").addEventListener("change", (e) => {
    state.sort = e.target.value;
    renderBoard();
  });
}

// greedy buy-plan within budget (same logic as the CLI's ranking.rank)
function plan(budget) {
  const ranked = ALL.filter((p) => p.price_per_mb != null && p.price > 0).sort(
    (a, b) => a.price_per_mb - b.price_per_mb,
  );
  let rem = budget;
  const out = [];
  for (const p of ranked) {
    if (rem <= 0) break;
    const count = Math.floor(rem / p.price);
    if (count) {
      out.push({ p, count });
      rem -= count * p.price;
    }
  }
  return out;
}

function renderAnswer() {
  const box = $("#answer");
  const b = state.budget;
  if (!b) {
    box.innerHTML = "";
    return;
  }
  const items = plan(b);
  if (!items.length) {
    box.innerHTML = `<div class="buy">با ${toman(b)} تومان حتی ارزان‌ترین بسته هم خریدنی نیست.</div>`;
    return;
  }
  const spent = items.reduce((s, it) => s + it.p.price * it.count, 0);
  const rows = items
    .slice(0, 5)
    .map((it, i) => {
      const p = it.p;
      return `<div class="buy ${i === 0 ? "buy--top" : ""}">
        <span class="buy__count">${faNum(it.count)}×</span>
        <span class="buy__name">${PROV[p.provider].label} — ${escape(p.name)}</span>
        <span class="buy__rate">${faNum(p.price_per_mb, 1)} <small>ت/مگ</small></span>
        <span class="buy__total">${toman(p.price * it.count)} تومان</span>
      </div>`;
    })
    .join("");
  box.innerHTML =
    `<div class="answer__head">با ${toman(b)} تومان، به‌صرفه‌ترین خرید:</div>${rows}` +
    `<div class="answer__head">جمعاً ${toman(spent)} از ${toman(b)} تومان.</div>`;
}

function renderBoard() {
  let list = ALL.slice();
  if (state.providers.size) list = list.filter((p) => state.providers.has(p.provider));
  if (state.q) list = list.filter((p) => p.name.includes(state.q));

  const big = 1e12;
  const cmp = {
    ppm: (a, b) => (a.price_per_mb ?? big) - (b.price_per_mb ?? big),
    price: (a, b) => a.price - b.price,
    volume: (a, b) => (b.volume_mb ?? 0) - (a.volume_mb ?? 0),
  }[state.sort];
  list.sort(cmp);

  const bestPpm = Math.min(
    ...ALL.filter((p) => p.price_per_mb != null).map((p) => p.price_per_mb),
  );
  const board = $("#board");
  board.innerHTML = "";
  $("#empty").hidden = list.length > 0;

  list.forEach((p, i) => {
    const pv = PROV[p.provider];
    const isTop = p.price_per_mb === bestPpm;
    const row = document.createElement("div");
    row.className = "row" + (isTop ? " row--top" : "");
    row.style.cssText = `--p:var(${pv.varc});--i:${i}`;

    const rate =
      p.price_per_mb == null
        ? `<div class="rate rate--none">—<small>بدون رتبه</small></div>`
        : `<div class="rate" style="--heat:${HEAT(p.price_per_mb)}">${faNum(p.price_per_mb, 1)}<small>تومان/مگ</small></div>`;

    const code = p.buy_code && p.buy_code !== "-";
    const buy = code
      ? `<button class="copy" type="button" data-code="${escape(p.buy_code)}"><span>کد خرید</span> ${escape(p.buy_code)}</button>`
      : `<button class="copy" type="button" disabled><span>بدون کد</span></button>`;

    row.innerHTML = `
      <div class="rank">${faNum(i + 1)}</div>
      <div class="cell__name">
        <div class="name"><span class="tag ${pv.tagMod || ""}">${pv.label}</span>${escape(p.name)}</div>
        ${p.duration ? `<div class="sub">${escape(p.duration)}</div>` : ""}
      </div>
      <div class="vol">${volume(p.volume_mb)}</div>
      <div class="price">${toman(p.price)} <small>ت</small></div>
      ${rate}
      <div class="cell__buy">${buy}</div>`;
    board.appendChild(row);
  });
}

document.addEventListener("click", (e) => {
  const btn = e.target.closest(".copy[data-code]");
  if (!btn) return;
  navigator.clipboard?.writeText(btn.dataset.code).then(() => {
    const html = btn.innerHTML;
    btn.classList.add("copy--done");
    btn.innerHTML = "کپی شد ✓";
    setTimeout(() => {
      btn.classList.remove("copy--done");
      btn.innerHTML = html;
    }, 1500);
  });
});

function escape(s) {
  return String(s).replace(
    /[&<>"]/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c],
  );
}

load();

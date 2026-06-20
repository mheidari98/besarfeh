"use strict";

// --- provider metadata: label, brand color, and where to actually buy a pack ---
//   mci     -> packs buy with a dialable USSD code (we show & copy it)
//   mtn/rightel -> their "offer codes" aren't dialable; send the user to the
//                  operator's own buy page instead (verified 2026-06).
const PROV = {
  mci: { label: "همراه اول", varc: "--mci", buy: "https://mci.ir/internet-plans" },
  mtn: {
    label: "ایرانسل",
    varc: "--mtn",
    tagMod: "tag--mtn",
    buy: "https://irancell.ir/o/1001/mobile-internet-packages",
  },
  rightel: { label: "رایتل", varc: "--rightel", buy: "https://package.rightel.ir/packagesList" },
};
const ORDER = ["mci", "mtn", "rightel"];
const PRESETS = [50000, 100000, 200000, 500000, 1000000];

// --- formatting ---
const faNum = (n, frac = 0) =>
  new Intl.NumberFormat("fa-IR", { maximumFractionDigits: frac, useGrouping: true }).format(n);
const toman = (n) => faNum(Math.round(n));
const volume = (mb) =>
  mb == null ? "—" : mb >= 1024 ? `${faNum(mb / 1024, 1)} گیگ` : `${faNum(mb)} مگ`;
// accept English OR Persian/Arabic digits, ignore everything else (commas, spaces…)
const parseDigits = (s) =>
  Number(
    String(s)
      .replace(/[۰-۹]/g, (d) => "۰۱۲۳۴۵۶۷۸۹".indexOf(d))
      .replace(/[٠-٩]/g, (d) => "٠١٢٣٤٥٦٧٨٩".indexOf(d))
      .replace(/[^\d]/g, ""),
  ) || 0;
// compact preset label: 50000 -> "۵۰ هزار", 1000000 -> "۱ میلیون"
const presetLabel = (n) =>
  n >= 1e6 ? `${faNum(n / 1e6)} میلیون` : `${faNum(n / 1e3)} هزار`;

// price/MB -> hue (green=cheap … red=expensive); lightness lives in CSS so it
// adapts to light/dark themes.
function heatHue(values) {
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  return (v) => Math.round(150 * (1 - (hi === lo ? 0 : (v - lo) / (hi - lo))));
}

// --- state (mirrored to the URL so a view is shareable) ---
let ALL = [];
let HUE = () => 150;
let bestPpm = Infinity;
const state = { providers: new Set(), q: "", sort: "ppm", budget: 100000 };
const $ = (s) => document.querySelector(s);

function readUrl() {
  const p = new URLSearchParams(location.search);
  if (p.has("b")) state.budget = parseDigits(p.get("b"));
  if (p.has("q")) state.q = p.get("q");
  if (["ppm", "price", "volume"].includes(p.get("s"))) state.sort = p.get("s");
  (p.get("p") || "").split(",").filter((k) => PROV[k]).forEach((k) => state.providers.add(k));
}

function writeUrl() {
  const p = new URLSearchParams();
  if (state.budget && state.budget !== 100000) p.set("b", state.budget);
  if (state.q) p.set("q", state.q);
  if (state.sort !== "ppm") p.set("s", state.sort);
  if (state.providers.size) p.set("p", [...state.providers].join(","));
  const qs = p.toString();
  history.replaceState(null, "", qs ? `?${qs}` : location.pathname);
}

async function load() {
  readUrl();
  try {
    const res = await fetch("./data/packages.json", { cache: "no-cache" });
    const json = await res.json();
    ALL = json.packages || [];
    const rates = ALL.filter((p) => p.price_per_mb != null).map((p) => p.price_per_mb);
    HUE = heatHue(rates);
    bestPpm = Math.min(...rates);
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
  initTheme();
  buildPresets();
  buildChips();
  bindControls();
  renderAnswer();
  renderBoard();
}

// --- theme ---
function initTheme() {
  const btn = $("#theme");
  const paint = () =>
    (btn.textContent = document.documentElement.dataset.theme === "dark" ? "☀︎" : "☾");
  paint();
  btn.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("theme", next);
    } catch {}
    paint();
  });
}

// --- budget: presets + a plain field (typed value is left exactly as entered) ---
function buildPresets() {
  const box = $("#presets");
  PRESETS.forEach((n) => {
    const b = document.createElement("button");
    b.className = "preset";
    b.type = "button";
    b.dataset.amount = n;
    b.textContent = presetLabel(n);
    box.appendChild(b);
  });
  box.addEventListener("click", (e) => {
    const btn = e.target.closest(".preset");
    if (!btn) return;
    state.budget = Number(btn.dataset.amount);
    $("#budget").value = state.budget;
    markPresets();
    renderAnswer();
    writeUrl();
  });
}

function markPresets() {
  [...$("#presets").children].forEach((b) =>
    b.setAttribute("aria-pressed", String(Number(b.dataset.amount) === state.budget)),
  );
}

function buildChips() {
  const box = $("#providers");
  const mk = (key, label, varc) => {
    const b = document.createElement("button");
    b.className = "chip";
    b.type = "button";
    b.dataset.key = key;
    b.innerHTML =
      (varc ? `<span class="chip__dot" style="--c:var(${varc})"></span>` : "") + label;
    box.appendChild(b);
  };
  mk("all", "همه");
  ORDER.forEach((k) => mk(k, PROV[k].label, PROV[k].varc));
  markChips();

  box.addEventListener("click", (e) => {
    const btn = e.target.closest(".chip");
    if (!btn) return;
    const key = btn.dataset.key;
    if (key === "all") state.providers.clear();
    else state.providers.has(key) ? state.providers.delete(key) : state.providers.add(key);
    markChips();
    renderBoard();
    writeUrl();
  });
}

function markChips() {
  [...$("#providers").children].forEach((c) =>
    c.setAttribute(
      "aria-pressed",
      c.dataset.key === "all"
        ? String(state.providers.size === 0)
        : String(state.providers.has(c.dataset.key)),
    ),
  );
}

function bindControls() {
  const budget = $("#budget");
  budget.value = state.budget || "";
  markPresets();
  budget.addEventListener("input", () => {
    state.budget = parseDigits(budget.value);
    markPresets();
    renderAnswer();
    writeUrl();
  });

  const search = $("#search");
  search.value = state.q;
  search.addEventListener("input", (e) => {
    state.q = e.target.value.trim();
    renderBoard();
    writeUrl();
  });

  const sort = $("#sort");
  sort.value = state.sort;
  sort.addEventListener("change", (e) => {
    state.sort = e.target.value;
    renderBoard();
    writeUrl();
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

  $("#empty").hidden = list.length > 0;
  $("#board").innerHTML = list
    .map((p, i) => {
      const pv = PROV[p.provider];
      const rate =
        p.price_per_mb == null
          ? `<div class="rate rate--none">—<small>بدون رتبه</small></div>`
          : `<div class="rate" style="--hue:${HUE(p.price_per_mb)}">${faNum(p.price_per_mb, 1)}<small>تومان/مگ</small></div>`;

      // mci: dialable USSD -> copy button. others: link to operator's buy page.
      const ussd = p.provider === "mci" && p.buy_code && /^\*/.test(p.buy_code);
      const buy = ussd
        ? `<button class="buy-act copy" type="button" data-code="${escape(p.buy_code)}"><span>کد دستوری</span>${escape(p.buy_code)}</button>`
        : `<a class="buy-act link" href="${pv.buy}" target="_blank" rel="noopener">خرید آنلاین<span class="buy-act__ext" aria-hidden="true">↗</span></a>`;

      return `<div class="row${p.price_per_mb === bestPpm ? " row--top" : ""}" style="--p:var(${pv.varc});--i:${Math.min(i, 30)}">
      <div class="rank">${faNum(i + 1)}</div>
      <div class="cell__name">
        <div class="name"><span class="tag ${pv.tagMod || ""}">${pv.label}</span>${escape(p.name)}</div>
        ${p.duration ? `<div class="sub">${escape(p.duration)}</div>` : ""}
      </div>
      <div class="vol">${volume(p.volume_mb)}</div>
      <div class="price">${toman(p.price)} <small>ت</small></div>
      ${rate}
      <div class="cell__buy">${buy}</div></div>`;
    })
    .join("");
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

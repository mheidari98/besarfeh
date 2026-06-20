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

// duration buckets (days from packages.json `duration_days`) — the axis Iranians
// shop by. Single-select chips; "همه" = no filter.
const DUR_BUCKETS = [
  { key: "daily", label: "روزانه", test: (d) => d <= 1 },
  { key: "weekly", label: "هفتگی", test: (d) => d >= 2 && d <= 10 },
  { key: "monthly", label: "ماهانه", test: (d) => d >= 11 && d <= 45 },
  { key: "long", label: "بلندمدت", test: (d) => d > 45 },
];
// min-volume floor (MB) for the board; 0 = show all.
const MINVOL = [
  { v: 0, label: "همهٔ حجم‌ها" },
  { v: 1024, label: "۱ گیگ به بالا" },
  { v: 5120, label: "۵ گیگ به بالا" },
  { v: 10240, label: "۱۰ گیگ به بالا" },
  { v: 51200, label: "۵۰ گیگ به بالا" },
];
// optional "hide" toggles for packs that aren't freely buyable / always-on and
// so distort the per-GB ranking. Backed by the same `flags` the badges use; the
// "morning" flag stays badge-only (too rare to warrant its own toggle).
const FLAG_FILTERS = [
  { key: "night", label: "بدون شبانه" },
  { key: "new_sub", label: "بدون ویژهٔ مشترکین جدید" },
];
// caveats parsed into `flags` by the export step -> small badge on the card.
const BADGES = {
  new_sub: { label: "ویژهٔ مشترکین جدید", cls: "badge--warn" },
  night: { label: "شبانه", cls: "badge--night" },
  morning: { label: "صبحانت", cls: "badge--morning" },
};

// --- formatting ---
const faNum = (n, frac = 0) =>
  new Intl.NumberFormat("fa-IR", { maximumFractionDigits: frac, useGrouping: true }).format(n);
const toman = (n) => faNum(Math.round(n));
const volume = (mb) =>
  mb == null ? "—" : mb >= 1024 ? `${faNum(mb / 1024, 1)} گیگ` : `${faNum(mb)} مگ`;
// Persian/Arabic numerals -> ASCII digits (shared by budget parsing + search).
const foldDigits = (s) =>
  String(s)
    .replace(/[۰-۹]/g, (d) => "۰۱۲۳۴۵۶۷۸۹".indexOf(d))
    .replace(/[٠-٩]/g, (d) => "٠١٢٣٤٥٦٧٨٩".indexOf(d));
// budget field: keep only digits (ignore commas, spaces, "تومان"…)
const parseDigits = (s) => Number(foldDigits(s).replace(/[^\d]/g, "")) || 0;
// forgiving search fold: digits + Arabic kaf/yeh -> Persian, drop ZWNJ + spaces.
// So "گيگ" (Arabic yeh), "۱۵", and "سی روزه" all match what the data stores.
const norm = (s) =>
  foldDigits(s)
    .replace(/ي/g, "ی")
    .replace(/ك/g, "ک")
    .replace(/[‌\s]/g, "")
    .toLowerCase();
// rate the way buyers reason about it: toman per GB (sort still uses per-MB).
const ratePerGb = (ppm) => faNum(Math.round(ppm * 1024));
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
const state = { providers: new Set(), q: "", sort: "ppm", budget: 100000, dur: "", minvol: 0, excl: new Set() };
const $ = (s) => document.querySelector(s);

function readUrl() {
  const p = new URLSearchParams(location.search);
  if (p.has("b")) state.budget = parseDigits(p.get("b"));
  if (p.has("q")) state.q = p.get("q");
  if (["ppm", "price", "volume"].includes(p.get("s"))) state.sort = p.get("s");
  if (DUR_BUCKETS.some((b) => b.key === p.get("d"))) state.dur = p.get("d");
  if (p.has("v")) state.minvol = parseDigits(p.get("v"));
  (p.get("p") || "").split(",").filter((k) => PROV[k]).forEach((k) => state.providers.add(k));
  (p.get("x") || "").split(",").filter((k) => FLAG_FILTERS.some((f) => f.key === k))
    .forEach((k) => state.excl.add(k));
}

function writeUrl() {
  const p = new URLSearchParams();
  if (state.budget && state.budget !== 100000) p.set("b", state.budget);
  if (state.q) p.set("q", state.q);
  if (state.sort !== "ppm") p.set("s", state.sort);
  if (state.dur) p.set("d", state.dur);
  if (state.minvol) p.set("v", state.minvol);
  if (state.providers.size) p.set("p", [...state.providers].join(","));
  if (state.excl.size) p.set("x", [...state.excl].join(","));
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
  buildDurChips();
  buildFlagChips();
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
    renderAnswer();
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

// duration chips: single-select (exclusive), "همه" = no filter
function buildDurChips() {
  const box = $("#durations");
  const mk = (key, label) => {
    const b = document.createElement("button");
    b.className = "chip";
    b.type = "button";
    b.dataset.dur = key;
    b.textContent = label;
    box.appendChild(b);
  };
  mk("", "همه");
  DUR_BUCKETS.forEach((d) => mk(d.key, d.label));
  markDurChips();
  box.addEventListener("click", (e) => {
    const btn = e.target.closest(".chip");
    if (!btn) return;
    state.dur = btn.dataset.dur;
    markDurChips();
    renderAnswer();
    renderBoard();
    writeUrl();
  });
}

function markDurChips() {
  [...$("#durations").children].forEach((c) =>
    c.setAttribute("aria-pressed", String(c.dataset.dur === state.dur)),
  );
}

// flag chips: multi-select "hide" toggles (pressed = exclude that flag)
function buildFlagChips() {
  const box = $("#flags");
  FLAG_FILTERS.forEach(({ key, label }) => {
    const b = document.createElement("button");
    b.className = "chip";
    b.type = "button";
    b.dataset.flag = key;
    b.textContent = label;
    box.appendChild(b);
  });
  markFlagChips();
  box.addEventListener("click", (e) => {
    const btn = e.target.closest(".chip");
    if (!btn) return;
    const key = btn.dataset.flag;
    state.excl.has(key) ? state.excl.delete(key) : state.excl.add(key);
    markFlagChips();
    renderAnswer();
    renderBoard();
    writeUrl();
  });
}

function markFlagChips() {
  [...$("#flags").children].forEach((c) =>
    c.setAttribute("aria-pressed", String(state.excl.has(c.dataset.flag))),
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

  const minvol = $("#minvol");
  MINVOL.forEach((o) => {
    const opt = document.createElement("option");
    opt.value = o.v;
    opt.textContent = o.label;
    minvol.appendChild(opt);
  });
  minvol.value = state.minvol;
  minvol.addEventListener("change", (e) => {
    state.minvol = Number(e.target.value);
    renderAnswer();
    renderBoard();
    writeUrl();
  });

  // mobile: fold the advanced filters behind a toggle (drawer)
  const ft = $("#filtersToggle");
  ft.addEventListener("click", () => {
    const open = $(".controls").classList.toggle("filters-open");
    ft.setAttribute("aria-expanded", String(open));
  });
}

// rows passing the active provider / duration / min-volume / flag filters.
// Shared by the board AND the budget answer so the suggestion always reflects
// the filters in view. Search (q) is board-only (withSearch).
function filtered(withSearch) {
  let list = ALL.slice();
  if (state.providers.size) list = list.filter((p) => state.providers.has(p.provider));
  if (state.dur) {
    const bucket = DUR_BUCKETS.find((b) => b.key === state.dur);
    list = list.filter((p) => p.duration_days != null && bucket.test(p.duration_days));
  }
  if (state.minvol) list = list.filter((p) => (p.volume_mb ?? 0) >= state.minvol);
  if (state.excl.size) list = list.filter((p) => !(p.flags || []).some((f) => state.excl.has(f)));
  if (withSearch && state.q) {
    const q = norm(state.q);
    list = list.filter((p) => norm(p.name).includes(q));
  }
  return list;
}

// greedy buy-plan within budget (same logic as the CLI's ranking.rank), scoped
// to the active filters so it matches the board (search excluded).
function plan(budget) {
  const ranked = filtered(false)
    .filter((p) => p.price_per_mb != null && p.price > 0)
    .sort((a, b) => a.price_per_mb - b.price_per_mb);
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
        <span class="buy__rate">${ratePerGb(p.price_per_mb)} <small>ت/گیگ</small></span>
        <span class="buy__total">${toman(p.price * it.count)} تومان</span>
      </div>`;
    })
    .join("");
  const left = b - spent;
  const tail =
    left > 0
      ? `جمعاً ${toman(spent)} از ${toman(b)} تومان؛ ${toman(left)} تومان باقی می‌ماند.`
      : `جمعاً ${toman(spent)} از ${toman(b)} تومان.`;
  box.innerHTML =
    `<div class="answer__head">با ${toman(b)} تومان، به‌صرفه‌ترین خرید:</div>${rows}` +
    `<div class="answer__head">${tail}</div>`;
}

function renderBoard() {
  const list = filtered(true);

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
          : `<div class="rate" style="--hue:${HUE(p.price_per_mb)}">${ratePerGb(p.price_per_mb)}<small>تومان/گیگ</small></div>`;
      const badges = (p.flags || [])
        .map((f) => (BADGES[f] ? `<span class="badge ${BADGES[f].cls}">${BADGES[f].label}</span>` : ""))
        .join("");

      // mci: dialable USSD -> copy button. others: link to operator's buy page.
      const ussd = p.provider === "mci" && p.buy_code && /^\*/.test(p.buy_code);
      const buy = ussd
        ? `<button class="buy-act copy" type="button" data-code="${escape(p.buy_code)}"><span>کد دستوری</span><bdi class="ussd" dir="ltr">${escape(p.buy_code)}</bdi></button>`
        : `<a class="buy-act link" href="${pv.buy}" target="_blank" rel="noopener">خرید آنلاین<span class="buy-act__ext" aria-hidden="true">↗</span></a>`;

      return `<div class="row${p.price_per_mb === bestPpm ? " row--top" : ""}" style="--p:var(${pv.varc});--i:${Math.min(i, 30)}">
      <div class="rank">${faNum(i + 1)}</div>
      <div class="cell__name">
        <div class="name"><span class="tag ${pv.tagMod || ""}">${pv.label}</span>${escape(p.name)}</div>
        <div class="sub">${p.duration ? escape(p.duration) : ""}${badges}</div>
      </div>
      <div class="vol">${volume(p.volume_mb)}</div>
      <div class="price">${toman(p.price)} <small>ت</small></div>
      ${rate}
      <div class="cell__buy">${buy}</div></div>`;
    })
    .join("");
}

// Copy with a fallback for browsers without the async Clipboard API (older
// Android WebViews, non-HTTPS previews) so the USSD code is never a dead tap.
function copyText(text) {
  if (navigator.clipboard?.writeText) return navigator.clipboard.writeText(text);
  return new Promise((resolve, reject) => {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.cssText = "position:fixed;top:0;opacity:0";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try {
      document.execCommand("copy") ? resolve() : reject();
    } catch (err) {
      reject(err);
    } finally {
      ta.remove();
    }
  });
}

document.addEventListener("click", (e) => {
  const btn = e.target.closest(".copy[data-code]");
  if (!btn) return;
  const flash = (msg) => {
    const html = btn.innerHTML;
    btn.classList.add("copy--done");
    btn.innerHTML = msg;
    setTimeout(() => {
      btn.classList.remove("copy--done");
      btn.innerHTML = html;
    }, 1500);
  };
  copyText(btn.dataset.code).then(
    () => flash("کپی شد ✓"),
    // copy failed: at least surface the code (LTR-isolated) for the user to type
    () => flash(`<bdi dir="ltr">${escape(btn.dataset.code)}</bdi>`),
  );
});

function escape(s) {
  return String(s).replace(
    /[&<>"]/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c],
  );
}

load();

# CLAUDE.md — Iranian mobile-internet package comparator

Scrapes MCI / Irancell / RighTel, normalizes every pack to a price-per-megabyte
ranking, and prints the best packs buyable within a budget. Python + uv, all three
scrapers pure `requests` (no Selenium / browser / JS engine).

## Commands

```bash
uv sync                                                  # set up env (Python 3.13 via uv)
uv run besarfeh -b 100000 -p mci mtn    # run: budget (toman) + providers
uv run besarfeh -h                      # all options
uv run ruff check . && uv run ruff format .              # lint + format (keep clean)
# smoke-test one scraper in isolation:
uv run python -c "from besarfeh.scrapers import irancell; d=irancell(); print(len(d))"
```

Providers: `mci`, `mtn` (= Irancell), `rightel`. Sanity counts for a healthy
scrape: **mci ~40 (34 rankable), mtn ~38, rightel ~85** (as of early 2026).

## Conventions

- **Style: simple, short, compact.** No over-engineering, no needless abstraction.
  Add a line/comment only when needed; keep comments short. Inline a helper used
  once. snake_case, meaningful names.
- **Lint/format with ruff** (`pyproject.toml`: rules `I, UP, B, SIM`).
- **Scrapers are plain functions, not classes** — stateless fetch → DataFrame. Put
  new cross-scraper helpers in `scrapers/_shared.py`, don't re-duplicate.
- **Normalized units (keep stable): price = toman, VAT included; volume = MB.** Raw
  inputs differ per source — ALWAYS confirm unit + VAT when adding a provider:
  Irancell API = toman pre-VAT (× `1+vat`); RighTel `packagePrice` = rial VAT-incl
  (`/10`); MCI `data-price` = toman pre-VAT (× `TAX_RATE`).

## Architecture

`src/` layout, installable package (hatchling), console script
`besarfeh` → `cli:main`.

```
src/besarfeh/
  cli.py          argparse only -> ranking.compare(providers, budget)
  ranking.py      iterate SCRAPERS, concat, rank by price/meg, greedily print buys
  scrapers/
    __init__.py   SCRAPERS = {"mci": mci, "mtn": irancell, "rightel": rightel}  (fixed order)
    mci.py        server-rendered HTML, data-* attrs
    irancell.py   JSON API
    rightel.py    JSON API (bearer token)
    _shared.py    USER_AGENT, HEADERS, write_csv (utf-8-sig, no index, mkdir DB/)
DB/*.csv          last scrape output, committed as sample data
```

Each scraper returns a DataFrame **and** writes a CSV side-effect to `DB/`.
`ranking.py` only consumes the return value; the CSV is a cache/debug artifact.

### Output contract (what `ranking.py` expects)

Every scraper returns **one** DataFrame (indexed `0..N-1`) carrying:
- numeric `volume` (**MB**) — `NaN` for packs that can't be ranked per-MB; those
  rows drop from the ranking (`volume.notna()`) but stay in the CSV.
- `price` (**toman, VAT included**).
- provider-specific display columns (printed via `info[provider].loc[id]`).

`ranking.py` adds `provider`/`id`, casts rankable `volume` to float once, then ranks
on `price/meg = price/volume`. `volume` may arrive str (irancell) / int (rightel) /
float-with-NaN (mci) — the single cast normalizes it. Keep `volume`/`price` stable.

## Per-provider notes

Full source field maps (data-* attrs, JSON paths, future-feature pointers) live in
`docs/scraper-internals.md` — read it when adding columns/features or debugging
parsing. The non-obvious gotchas:

### MCI (`scrapers/mci.py`) — server-rendered HTML
URL `https://mci.ir/internet-plans` (old `notrino-plans` is gone; "notrino" is just
the brand — legacy names like `notrino-plans.js` survive in the markup, ignore them).
- **All ~40 packages are in one GET.** `mci.ir` is a Liferay portal; rows are
  `<li class="package-list-item">`. **There is NO plans XHR** — data is in the
  document, not an API. List.js does only cosmetic client-side pagination, so the
  live browser DOM may show ~10 rows while the raw HTML has all of them. Parse the
  response, not the DOM.
- **GOTCHA — single-quoted attributes.** Raw HTML uses `class='package-list-item'`,
  so `grep 'class="..."'` returns 0. Use `soup.select("li.package-list-item")`
  (quote-agnostic), never a double-quote grep.
- Return: `volume` is `NaN` for `UNMEASURABLE_TYPES = {unlimited, sobhanet, new-sub}`
  (fair-usage cap / night-only / new-subscriber — not rankable per-MB). `price` is
  `data-price × TAX_RATE`, **unrounded on purpose** (rounding shifts the budget
  math). `TAX_RATE = 1.10` is hardcoded — MCI's HTML has no VAT field, but the page
  footnote states VAT is **10%**, added on top of the listed (pre-VAT, toman) price.

### Irancell (`scrapers/irancell.py`) — JSON API
- GET the page, regex `packages-id="([a-f0-9]{24})"`, then GET
  `https://irancell.ir/e/products/{id}` (no auth; send `accept-language: fa`).
- **Scraping the id live is deliberate** — it drifts over time; that resilience is
  the point. `DEFAULT_PACKAGES_ID` is only a fallback. Don't "optimize" it into a
  default-only request. Packs with empty `traffic` (voice/SMS) are skipped.

### RighTel (`scrapers/rightel.py`) — JSON API (bearer)
- Angular SPA backed by `portal-api.rightel.ir`: POST `{"username":"website"}` to
  `.../auth/authenticate` (password-less) → `data.token` JWT, then GET
  `.../extra-package-direct/web-site/purchasable-package` with `Authorization:
  Bearer <token>`.
- `internetAmount`/`durationAmount` are always null, so volume/duration are parsed
  from `purchasablePackageNameFa`. API returns ASCII digits now, so the Persian-digit
  normalization is defensive-only.

## Re-discovering an API when a site changes

These sites rewrite their frontends every couple of years; when a scraper returns 0
rows:

1. Open the page with the **chrome-devtools MCP** (`new_page`).
2. `list_network_requests` filtered to `["xhr","fetch"]` — find the JSON packages
   endpoint (Irancell: `/e/products/{id}`).
3. `get_network_request <reqid>`; map fields → output columns.
4. Check whether the dynamic id/params are in the page HTML so you can scrape them
   instead of hardcoding (Irancell: `packages-id="..."`).
5. Prefer the JSON API over HTML parsing — no Selenium, structured, stable.

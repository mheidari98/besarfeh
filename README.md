# besarfeh · به‌صرفه

> Find the most cost-effective mobile-internet package in Iran.
> Scrapes MCI (همراه اول), Irancell (ایرانسل) and RighTel (رایتل), ranks every
> pack by **price-per-megabyte**, and tells you the best buy within your budget.

All three operators are scraped over plain HTTP — no Chrome driver / Selenium.

---

## Website (no install)

A static comparator is published to GitHub Pages — pick a budget, see the
cheapest-per-MB packs and the USSD/offer code to buy them, all in the browser.
It reads the daily-refreshed CSVs in [`DB/`](DB), so the repo's git history
doubles as a **price-history dataset**.

---

## CLI

Requirements: [uv](https://docs.astral.sh/uv/) (manages Python + deps).

```bash
# best packs for a 100,000-toman budget across providers
uv run besarfeh -b 100000 -p mci mtn rightel
uv run besarfeh -h            # all options
```

Installable: `pip install .`, then `besarfeh -b 100000 -p mci`.

Extra entry points (used by CI):

```bash
uv run besarfeh-refresh       # re-scrape all providers -> DB/*.csv
uv run besarfeh-export        # DB/*.csv -> web/data/packages.json (for the site)
```

---

## Develop

```bash
uv sync
uv run pytest -q
uv run ruff check . && uv run ruff format .
```

---

## Providers

- [x] Hamrahe Aval (MCI)
- [x] Irancell (MTN)
- [x] RighTel

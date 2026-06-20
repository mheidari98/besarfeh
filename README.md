# besarfeh · به‌صرفه

> Find the most cost-effective mobile-internet package in Iran.
> Scrapes MCI (همراه اول), Irancell (ایرانسل) and RighTel (رایتل), ranks every
> pack by **price-per-megabyte**, and tells you the best buy within your budget.

All three operators are scraped over plain HTTP — no Chrome driver / Selenium.

---

## Website (no install)

A static comparator is published to GitHub Pages — pick a budget, see the
cheapest-per-MB packs and the USSD/offer code to buy them, all in the browser.
On every push to `main`, CI builds `web/data/packages.json` from the committed
CSVs in [`DB/`](DB) and redeploys, so the repo's git history doubles as a
**price-history dataset**.

---

## CLI

Requirements: [uv](https://docs.astral.sh/uv/) (manages Python + deps).

```bash
# best packs for a 100,000-toman budget across providers
uv run besarfeh -b 100000 -p mci mtn rightel
uv run besarfeh -h            # all options
```

Installable: `pip install .`, then `besarfeh -b 100000 -p mci`.

Extra entry points:

```bash
uv run besarfeh-refresh       # re-scrape all providers -> DB/*.csv
uv run besarfeh-export        # DB/*.csv -> web/data/packages.json (CI builds this)
```

---

## Refreshing data

The operator sites are only reachable from inside Iran, so the scrape runs
**locally**, not in GitHub CI. To update the published prices:

```bash
uv run besarfeh-refresh                       # scrape -> DB/*.csv
git commit -am "data: refresh $(date +%F)" && git push   # push to main
```

The push triggers the Pages workflow, which rebuilds `packages.json` from the
new CSVs and redeploys. `web/data/` is generated (gitignored) — never committed.
For daily automation, run that two-liner from a local cron on a machine in Iran.

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

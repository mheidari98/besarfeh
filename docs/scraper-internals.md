# Scraper internals — field maps & future-work reference

Detailed source maps for each provider. Read this when **adding a feature** or
**debugging a scraper's parsing** (offer codes, sim-type splits, new columns).
CLAUDE.md links here so it stays lean; nothing here is needed for day-to-day runs.

## MCI — `<li class="package-list-item">` `data-*` attributes

| attribute | meaning | Used? |
|---|---|---|
| `data-volume` | quota in **MB** ("60"=60MB, "61440"=60GB, "102400"=100GB). Always numeric. | ✅ `volume` |
| `data-price` | price in **toman, PRE-VAT** (matches the displayed price text exactly) | ✅ (× `TAX_RATE`) |
| `data-package-type` | `short-time` / `monthly` / `long-time` / `sobhanet` / `unlimited` / `new-sub` | ✅ filter via `UNMEASURABLE_TYPES` |
| `data-duration` | `one-day` / `three-days` / `seven-days` / `fifteen-days` / `thirty-days` / `three-months` / `four-months` / `unlimited-monthly` | ⬜ clean key for per-day cost ranking or duration filtering |
| `data-simcard` | `prepaid` / `postpaid-prepaid` | ⬜ could split pricing per sim type |
| `data-fair-volume` | fair-usage cap (MB) for `unlimited` packs; `"null"` otherwise | ⬜ only meaningful for unlimited |

### MCI inner DOM (text fields parsed by `_clean`)

| selector | meaning | Used? |
|---|---|---|
| `.package-volume-info .td-inner-wrapper` | Persian label "60 مگابایت یک‌روزه" | ✅ `package_volume_info` |
| `.item-package-price` | "2,450 تومان" | ✅ `package_price` |
| `.ussd-code-widget` | USSD code "*100*31#" (or "-" when none) | ✅ `ussd_code_block` |
| `.purchase-btn[data-package-code]` | online-purchase code, e.g. "502193" | ⬜ would enable a "how to buy online" output (parity with Irancell offer codes) |
| `.package-regulatory-confirm-code a[href]` | CRA approval link `etebar-basteh.cra.ir/?OperatorId=165&PackCode=<uuid>` + 12-digit code | ⬜ |
| `.item-package-simcard` | sim-type label, e.g. "ویژه سیم‌کارت اعتباری" | ⬜ redundant with `data-simcard` |

The `#packageType` / `#packageDuration` `<select>` dropdowns in the HTML enumerate
the full set of filter values above (List.js client-side filtering) — a handy
source of truth for valid enum values.

## Irancell — `/e/products/{id}` JSON element field map

| JSON path | Meaning | Used? |
|---|---|---|
| `name.fa` / `name.en` | Pack name e.g. "4 گیگابایت" | ✅ `pack-name` |
| `price` | Base price, toman, **pre-VAT** | ✅ (× `1+vat`) |
| `vat_percentage` | VAT fraction, e.g. `0.1` = 10% | ✅ |
| `specification_contents[key=traffic].desc.fa` | Volume in **MB** ("4096") | ✅ `volume` |
| `specification_contents[key=package_type].desc.fa` | Duration text ("30 روزه") | ✅ `data-duration` |
| `specification_contents[key=package_type].value` | Machine value ("30days","daily","specific-time-based"…) | ⬜ better than fa text for filtering |
| `sub_title.fa` | Time-restriction label (night-only etc.); empty today | ✅ `time-range` (filter key) |
| `id` | Mongo ObjectId of the pack | ⬜ |
| `desc.fa` | HTML blurb incl. CRA regulator approval code/link | ⬜ |
| `specification_contents[key=simcard_type].value` | `prepaid` / `postpaid` / `prepaid-postpaid` | ⬜ could split pricing per sim type |
| `prepaid_offer_code` / `postpaid_offer_code` | USSD/offer codes to actually buy the pack | ⬜ useful for a "how to buy" output |
| `ldms_offer_code` | Alt offer code (often empty) | ⬜ |
| `specification_contents[key=ussd].desc.fa` | USSD purchase code | ⬜ mostly empty |
| `specification_contents[key=dial_number].desc.fa` | Dial number | ⬜ usually empty |
| `specification_contents[key=speed].desc.fa` | Speed cap | ⬜ always empty in samples |
| `service_name` / `technology` | "NormalBolton" / "GSM" | ⬜ |
| `Promoted`, `OrderNumber`, `NetworkCoverage`, `categories`, `created_at`, `last_modified` | metadata | ⬜ |

### Future-work pointers

- **`package_type.value`** is the clean filter key — prefer it over Persian `desc`
  text if filtering by duration or detecting time-limited packs
  (`specific-time-based`, `hourly`). Packs with a non-empty `sub_title.fa`
  (night/region restricted) are always dropped — they can't be ranked per-MB
  fairly. All `sub_title.fa` are empty today, so this is dormant for now; if a
  toggle to include them is ever wanted, re-add an `--allow-limited` CLI flag.
- **Offer codes**: Irancell `prepaid_offer_code` is now scraped (offer-code
  column). MCI `.purchase-btn[data-package-code]` is still unscraped — adding it
  would give MCI an online-purchase code alongside its USSD code.

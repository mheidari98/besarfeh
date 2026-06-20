import re
import sys

import pandas as pd
import requests

from ._shared import HEADERS, http_session, warn_if_low, write_csv

PAGE_URL = "https://irancell.ir/o/1001/mobile-internet-packages"
PRODUCTS_API = "https://irancell.ir/e/products/{pid}"
OUTPUT_CSV = "DB/mtn.csv"
# Fallback packages-id (mobile internet) used if it cannot be scraped from the page.
DEFAULT_PACKAGES_ID = "5e16bf95d11fd7209ba56b20"


def _packages_id(session):
    """Scrape the dynamic products id from the page, fall back to default."""
    try:
        html = session.get(PAGE_URL, headers=HEADERS, timeout=20).text
        if m := re.search(r'packages-id="([a-f0-9]{24})"', html):
            return m.group(1)
    except requests.RequestException:
        pass
    print(
        "warning: irancell using fallback packages-id (may be stale)", file=sys.stderr
    )
    return DEFAULT_PACKAGES_ID


def _spec_fa(specs, key):
    """Persian text of a specification_contents entry, keyed by its `key`."""
    return specs.get(key, {}).get("desc", {}).get("fa", "").strip()


def _pack_row(pack):
    """One normalized row from a product, or None to skip (non-data / time-limited)."""
    specs = {s["key"]: s for s in pack.get("specification_contents", [])}
    traffic = _spec_fa(specs, "traffic")
    if not traffic:  # skip non-data packs (voice/SMS)
        return None
    time_range = pack.get("sub_title", {}).get("fa", "").strip()
    if time_range:  # skip time-limited (night/region) packs; can't rank fairly
        return None
    vat = pack.get("vat_percentage") or 0
    return {
        "pack-name": pack["name"]["fa"].replace("\xa0", " ").strip(),
        "data-duration": _spec_fa(specs, "package_type"),
        "time-range": time_range,
        "price": round(float(pack["price"]) * (1 + vat)),
        "volume": traffic,
        # USSD/offer code to actually buy the pack (prepaid first, postpaid fallback)
        "offer-code": pack.get("prepaid_offer_code")
        or pack.get("postpaid_offer_code")
        or "",
    }


def irancell():
    session = http_session()
    pid = _packages_id(session)

    resp = session.get(
        PRODUCTS_API.format(pid=pid),
        headers={**HEADERS, "accept": "*/*", "referer": PAGE_URL},
        timeout=20,
    )
    resp.raise_for_status()

    rows = [row for p in resp.json() if (row := _pack_row(p))]
    df = pd.DataFrame.from_dict(rows)
    write_csv(df, OUTPUT_CSV)
    return warn_if_low(df, "mtn", 38)

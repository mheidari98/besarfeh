import re

import pandas as pd
import requests

from ._shared import HEADERS, write_csv

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
    return DEFAULT_PACKAGES_ID


def _spec_fa(specs, key):
    """Persian text of a specification_contents entry, keyed by its `key`."""
    return specs.get(key, {}).get("desc", {}).get("fa", "").strip()


def irancell(allow_limited_packs=False):
    session = requests.Session()
    pid = _packages_id(session)

    resp = session.get(
        PRODUCTS_API.format(pid=pid),
        headers={**HEADERS, "accept": "*/*", "referer": PAGE_URL},
        timeout=20,
    )
    resp.raise_for_status()
    products = resp.json()

    pack_json = []
    for pack in products:
        specs = {s["key"]: s for s in pack.get("specification_contents", [])}
        traffic = _spec_fa(specs, "traffic")
        if not traffic:  # skip non-data packs
            continue
        time_range = pack.get("sub_title", {}).get("fa", "").strip()
        if not allow_limited_packs and time_range:
            continue
        vat = pack.get("vat_percentage") or 0
        pack_json.append(
            {
                "pack-name": pack["name"]["fa"].replace("\xa0", " ").strip(),
                "data-duration": _spec_fa(specs, "package_type"),
                "time-range": time_range,
                "price": round(float(pack["price"]) * (1 + vat)),
                "volume": traffic,
            }
        )

    df = pd.DataFrame.from_dict(pack_json)
    write_csv(df, OUTPUT_CSV)
    return df

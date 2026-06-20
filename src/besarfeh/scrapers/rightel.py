import re
import time

import pandas as pd

from ._shared import USER_AGENT, http_session, warn_if_low, write_csv

# RighTel rewrote its store into an Angular SPA. The old Selenium HTML scrape is
# dead; packages now come from a JSON API behind a (password-less) bearer token.
#
#   1. POST {"username": "website"} -> {"data": {"token": "<jwt>"}}
#   2. GET  purchasable-package  with  Authorization: Bearer <jwt>  -> packages
#
# No browser, no Selenium. See CLAUDE.md "Re-discovering an API" for how this was
# found (chrome-devtools MCP -> network panel -> portal-api.rightel.ir).

AUTH_URL = "https://portal-api.rightel.ir/user-management/api/v1/auth/authenticate"
PACKAGES_URL = (
    "https://portal-api.rightel.ir/extra-package/api/v1"
    "/extra-package-direct/web-site/purchasable-package"
)
AUTH_USERNAME = "website"
OUTPUT_CSV = "DB/rightel.csv"

HEADERS = {
    "User-Agent": USER_AGENT,
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "origin": "https://package.rightel.ir",
    "referer": "https://package.rightel.ir/",
}

# API returns ASCII digits today; normalize Persian numerals defensively. Callers
# translate the pack name once and pass the result to the parsers below.
_FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def _volume_mb(name):
    """Internet volume in MB parsed from the pack name, or None for voice/SMS packs."""
    if gb := re.search(r"([\d.]+)\s*گیگابایت", name):
        return float(gb.group(1)) * 1024
    if mb := re.search(r"([\d.]+)\s*مگابایت", name):
        return float(mb.group(1))
    return None  # دقیقه مکالمه / پیامک / رایتا bundles have no data volume


def _duration(name):
    """Human duration phrase parsed from the pack name (روزه / ماهه / ساله)."""
    m = re.search(r"([\d.]+)\s*(روزه|ماهه|ساله)", name)
    return m.group(0).strip() if m else ""


def _time_range(name):
    """Restriction label that mirrors irancell's `time-range` filter key."""
    if "شبانه" in name:  # night-only
        return "شبانه"
    if "عراق" in name:  # Iraq roaming
        return "ویژه عراق"
    if "بین الملل" in name:  # international
        return "بین الملل"
    return ""


def rightel():
    session = http_session()
    auth = session.post(
        AUTH_URL, headers=HEADERS, json={"username": AUTH_USERNAME}, timeout=20
    )
    auth.raise_for_status()
    token = auth.json()["data"]["token"]

    resp = session.get(
        PACKAGES_URL,
        params={"d": int(time.time() * 1000)},  # cache-buster the SPA sends
        headers={**HEADERS, "authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    packages = resp.json()["data"]

    rows = []
    for item in packages:
        p = item["purchasablePackage"]
        name = p["purchasablePackageNameFa"].strip()
        digits = name.translate(_FA_DIGITS)  # normalized once for the numeric parsers

        volume = _volume_mb(digits)
        if volume is None:  # skip voice/SMS/credit bundles (can't rank by price/MB)
            continue

        time_range = _time_range(name)
        if time_range:  # skip night/Iraq/international packs; can't rank fairly
            continue

        # packagePrice is RIAL, VAT included (matches the "۳۸,۲۰۰ ریال" the site
        # shows). Normalize to toman post-VAT like the other providers: / 10.
        price_rial = p["packagePrice"] - (p.get("packageDiscountAmount") or 0)

        rows.append(
            {
                "pack-name": name,
                "type": p["mainProductType"],  # PREPAID / POSTPAID / DATA
                "data-duration": _duration(digits),
                "time-range": time_range,
                "price": round(price_rial / 10),
                "volume": volume,  # float MB, like the other scrapers
                "offer-code": p.get("pricePlanOfferCode") or "",
            }
        )

    if not rows:  # all voice/SMS/restricted: let the caller report "no usable rows"
        return warn_if_low(pd.DataFrame(), "rightel", 49)
    df = pd.DataFrame.from_dict(rows).drop_duplicates(
        subset=["pack-name", "type", "price"], ignore_index=True
    )
    # Each pack is sold to credit (PREPAID) and permanent (POSTPAID) SIMs as two
    # identical rows differing only by offer-code; drop the postpaid twin and keep
    # the credit one (the mass-market SIM). Postpaid packs with no credit twin stay.
    keys = df.set_index(["pack-name", "price"]).index
    prepaid = keys[(df["type"] == "PREPAID").to_numpy()]
    twin = (df["type"] == "POSTPAID").to_numpy() & keys.isin(prepaid)
    df = df[~twin].reset_index(drop=True)
    write_csv(df, OUTPUT_CSV)
    return warn_if_low(df, "rightel", 49)  # ~85 raw, ~49 after prepaid/postpaid dedup

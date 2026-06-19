import pandas as pd
from bs4 import BeautifulSoup

from ._shared import HEADERS, http_session, warn_if_low, write_csv

URL = "https://mci.ir/internet-plans"

# Package types that can't be ranked on a price-per-megabyte basis:
#   unlimited -> volume is just a fair-usage cap, not real quota
#   sobhanet  -> night-only ("صبحانت")
#   new-sub   -> only buyable by new subscribers ("ویژه مشترکین جدید")
UNMEASURABLE_TYPES = {"unlimited", "sobhanet", "new-sub"}

TAX_RATE = 1.09  # MCI HTML exposes no VAT field; hardcode 9% (checked 2026-06)


def _clean(node):
    return " ".join(node.get_text().split()) if node else ""


def mci():
    """Scrape MCI packages from server-rendered HTML (data-* attrs, no JS/Selenium).

    Returns one df per package: display columns plus numeric volume (MB; NaN for
    unrankable unlimited/sobhanet/new-sub packs) and price (toman, +VAT).
    """
    resp = http_session().get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    rows = []
    for li in soup.select("li.package-list-item"):
        volume_mb = float(li.get("data-volume") or 0)
        rankable = (
            li.get("data-package-type", "") not in UNMEASURABLE_TYPES and volume_mb > 0
        )
        rows.append(
            {
                "package_volume_info": _clean(
                    li.select_one(".package-volume-info .td-inner-wrapper")
                ),
                "package_price": _clean(li.select_one(".item-package-price")),
                "ussd_code_block": _clean(li.select_one(".ussd-code-widget"))
                or _clean(li.select_one(".item-package-ussd")),
                "volume": volume_mb if rankable else float("nan"),
                "price": float(li.get("data-price") or 0) * TAX_RATE,
            }
        )

    df = pd.DataFrame(rows)
    write_csv(df, "DB/mci.csv")
    return warn_if_low(df, "mci", 40)

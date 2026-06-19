import sys

import pandas as pd
from tabulate import tabulate

from .scrapers import SCRAPERS


def rank(providers, budget):
    """Scrape the requested providers and return a greedy buy-plan (no printing).

    Each entry has normalized fields (provider, count, volume MB, price toman,
    price_per_mb) plus `pack`, the provider's raw display row (a pandas Series).
    Returned in cheapest-price-per-MB order.
    """
    frames, info = [], {}
    for name, scrape in SCRAPERS.items():  # fixed order: mci, mtn, rightel
        if name not in providers:
            continue
        try:
            df = scrape()
        except Exception as e:  # one dead provider must not sink the others
            print(f"warning: {name} scrape failed: {e}", file=sys.stderr)
            continue
        if df.empty or "volume" not in df:
            print(f"warning: {name} returned no usable rows", file=sys.stderr)
            continue
        df["provider"], df["id"] = name, df.index
        info[name] = df
        frames.append(df[df["volume"].notna()][["provider", "id", "volume", "price"]])

    if not frames:
        return []
    ranking = pd.concat(frames, ignore_index=True)
    ranking["volume"] = ranking["volume"].astype(float)
    # drop price 0: would ZeroDivisionError below and is meaningless per-MB
    ranking = ranking[ranking["price"] > 0]
    ranking["price/meg"] = ranking["price"] / ranking["volume"]
    ranking.sort_values("price/meg", inplace=True)

    plan = []
    for _, row in ranking.iterrows():
        if budget <= 0:
            break
        count = int(budget // row["price"])
        budget -= count * row["price"]
        if count:
            plan.append(
                {
                    "provider": row["provider"],
                    "count": count,
                    "volume": row["volume"],
                    "price": row["price"],
                    "price_per_mb": row["price/meg"],
                    "pack": info[row["provider"]].loc[row["id"]],
                }
            )
    return plan


def _human_mb(mb):
    """1024 -> '1 GB', 60 -> '60 MB'."""
    return f"{mb / 1024:g} GB" if mb >= 1024 else f"{mb:g} MB"


def _display_row(item):
    """One uniform, human-readable row across all providers (no internal cols)."""
    pack = item["pack"]
    name = pack.get("pack-name") or pack.get("package_volume_info") or ""
    buy_code = pack.get("ussd_code_block") or pack.get("offer-code") or ""
    price = round(item["price"])
    return {
        "provider": item["provider"],
        "pack": name,
        "volume": _human_mb(item["volume"]),
        "price": f"{price:,}",
        "price/MB": f"{item['price_per_mb']:.1f}",
        "count": item["count"],
        "total": f"{price * item['count']:,}",
        "buy code": buy_code,
    }


def compare(providers, budget):
    """Rank by price-per-MB and print what to buy within budget (toman)."""
    plan = rank(providers, budget)
    if not plan:
        print(
            f"No packages found within budget {budget:,} toman (or all sources failed)."
        )
        return
    rows = [_display_row(item) for item in plan]
    print(tabulate(rows, headers="keys", tablefmt="psql"))
    total = sum(round(item["price"]) * item["count"] for item in plan)
    print(f"\nTotal: {total:,} of {budget:,} toman")

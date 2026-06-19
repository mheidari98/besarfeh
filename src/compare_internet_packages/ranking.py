import sys

import pandas as pd
from tabulate import tabulate

from .scrapers import SCRAPERS


def rank(providers, budget):
    """Scrape the requested providers and return a greedy buy-plan (no printing).

    Each entry is {"provider", "count", "pack"} where `pack` is the provider's
    display row (a pandas Series). Returned in cheapest-price-per-MB order.
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
                    "pack": info[row["provider"]].loc[row["id"]],
                }
            )
    return plan


def compare(providers, budget):
    """Rank by price-per-MB and print what to buy within budget."""
    plan = rank(providers, budget)
    if not plan:
        print(f"No packages found within budget {budget} (or all sources failed).")
        return
    for item in plan:
        print(f"you should buy {item['count']} package from {item['provider']}")
        print(tabulate([item["pack"]], headers="keys", tablefmt="psql"))

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
        df = scrape()
        df["provider"], df["id"] = name, df.index
        info[name] = df
        frames.append(df[df["volume"].notna()][["provider", "id", "volume", "price"]])

    if not frames:
        return []
    ranking = pd.concat(frames, ignore_index=True)
    ranking["volume"] = ranking["volume"].astype(float)
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
    for item in rank(providers, budget):
        print(f"you should buy {item['count']} package from {item['provider']}")
        print(tabulate([item["pack"]], headers="keys", tablefmt="psql"))

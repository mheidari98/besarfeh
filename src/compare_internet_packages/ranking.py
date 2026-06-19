import pandas as pd
from tabulate import tabulate

from .scrapers import SCRAPERS


def compare(providers, budget):
    """Scrape the requested providers, rank by price-per-MB, print what to buy."""
    frames, info = [], {}
    for name, scrape in SCRAPERS.items():  # fixed order: mci, mtn, rightel
        if name not in providers:
            continue
        df = scrape()
        df["provider"], df["id"] = name, df.index
        info[name] = df
        frames.append(df[df["volume"].notna()][["provider", "id", "volume", "price"]])

    if not frames:
        return
    ranking = pd.concat(frames, ignore_index=True)
    ranking["volume"] = ranking["volume"].astype(float)
    ranking["price/meg"] = ranking["price"] / ranking["volume"]
    ranking.sort_values("price/meg", inplace=True)

    for _, row in ranking.iterrows():
        if budget <= 0:
            break
        count = int(budget // row["price"])
        budget -= count * row["price"]
        if count:
            print(f"you should buy {count} package from {row['provider']}")
            print(
                tabulate(
                    [info[row["provider"]].loc[row["id"]]],
                    headers="keys",
                    tablefmt="psql",
                )
            )

"""Read the committed DB/*.csv into one uniform JSON the web UI consumes.

The scrapers write provider-specific columns; this flattens them to a single
record shape (provider, name, volume_mb, duration, price, price_per_mb,
buy_code) so the static site needs no per-provider logic.
"""

import json
import math
from pathlib import Path

import pandas as pd

# per-provider source columns -> uniform fields
_MAP = {
    "mci": {
        "file": "mci.csv",
        "name": "package_volume_info",
        "duration": None,
        "buy": "ussd_code_block",
    },
    "mtn": {
        "file": "mtn.csv",
        "name": "pack-name",
        "duration": "data-duration",
        "buy": "offer-code",
    },
    "rightel": {
        "file": "rightel.csv",
        "name": "pack-name",
        "duration": "data-duration",
        "buy": "offer-code",
    },
}


def _isnan(v):
    return v is None or (isinstance(v, float) and math.isnan(v))


def _txt(v):
    return "" if _isnan(v) else str(v).strip()


def to_records(db_dir="DB"):
    """Flatten the three CSVs into a list of uniform package dicts."""
    out = []
    for provider, m in _MAP.items():
        df = pd.read_csv(Path(db_dir) / m["file"])
        for _, row in df.iterrows():
            vol = row.get("volume")
            vol = None if _isnan(vol) else float(vol)
            price = round(float(row["price"]))
            out.append(
                {
                    "provider": provider,
                    "name": _txt(row.get(m["name"])),
                    "volume_mb": vol,
                    "duration": _txt(row.get(m["duration"])) if m["duration"] else "",
                    "price": price,
                    "price_per_mb": round(price / vol, 2) if vol else None,
                    "buy_code": _txt(row.get(m["buy"])),
                }
            )
    return out


def export_json(path="web/data/packages.json", db_dir="DB"):
    """Write to_records() as {"packages": [...]} for the static site (console script)."""
    recs = to_records(db_dir)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"packages": recs}, f, ensure_ascii=False)
    print(f"wrote {len(recs)} packages -> {path}")

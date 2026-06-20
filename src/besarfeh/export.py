"""Read the committed DB/*.csv into one uniform JSON the web UI consumes.

The scrapers write provider-specific columns; this flattens them to a single
record shape (provider, name, volume_mb, duration, duration_days, flags, price,
price_per_mb, buy_code) so the static site needs no per-provider logic.

`duration_days` normalizes every provider's period to whole days (mtn/rightel
from the duration field, mci from the spelled-out name) for the UI's duration
filter. `flags` carries buyability caveats parsed from the name (new_sub / night
/ morning) that the UI renders as badges.
"""

import json
import math
import re
from pathlib import Path

import pandas as pd

ZWNJ = "‌"
# duration field unit (mtn/rightel) -> days; "روزانه" (daily-renew) handled separately
_DUR_UNIT = {"روزه": 1, "ماهه": 30, "ساله": 365}
# MCI spells the period out in the NAME (ZWNJ-joined), no duration field -> map tokens
_MCI_DUR = {
    "یکروزه": 1, "سهروزه": 3, "هفتروزه": 7, "پانزدهروزه": 15, "سیروزه": 30,
    "یکماهه": 30, "دوماهه": 60, "سهماهه": 90, "چهارماهه": 120, "ششماهه": 180,
    "یکساله": 365,
}  # fmt: skip


def _duration_days(name, duration):
    """Normalize any provider's period to whole days, or None if unparseable."""
    if duration:  # mtn/rightel: numeric phrase in the duration field
        if "روزانه" in duration:  # daily-renewing quota
            return 1
        if m := re.search(r"([\d.]+)\s*(روزه|ماهه|ساله)", duration):
            return round(float(m.group(1)) * _DUR_UNIT[m.group(2)])
    flat = name.replace(ZWNJ, "")  # mci: spelled out in the name (سی‌روزه ...)
    for token, days in _MCI_DUR.items():
        if token in flat:
            return days
    return None


def _dur_label(days):
    """Human duration label from days (30 -> '1 ماهه', 7 -> '7 روزه')."""
    if days is None:
        return ""
    if days >= 365 and days % 365 == 0:
        return f"{days // 365} ساله"
    if days >= 30 and days % 30 == 0:
        return f"{days // 30} ماهه"
    return f"{days} روزه"


def _flags(name):
    """Buyability/usage caveats parsed from the name (badges in the UI)."""
    f = []
    if "مشترکین جدید" in name:  # only new subscribers can buy
        f.append("new_sub")
    if "شبانه" in name or "بامداد" in name:  # night-only window
        f.append("night")
    if "صبحانت" in name:  # morning-only window (MCI brand)
        f.append("morning")
    return f


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
            name = _txt(row.get(m["name"]))
            raw_dur = _txt(row.get(m["duration"])) if m["duration"] else ""
            days = _duration_days(name, raw_dur)
            out.append(
                {
                    "provider": provider,
                    "name": name,
                    "volume_mb": vol,
                    "duration": raw_dur or _dur_label(days),  # mci has no field; derive
                    "duration_days": days,
                    "flags": _flags(name),
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

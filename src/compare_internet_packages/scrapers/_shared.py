"""Bits every provider scraper shares: user-agent, base headers, CSV writer."""

from pathlib import Path

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# Base headers for the Persian operator sites (mci, irancell). RighTel's JSON API
# needs extra keys, so it spreads USER_AGENT and builds its own dict.
HEADERS = {
    "User-Agent": USER_AGENT,
    "accept-language": "fa",
}


def write_csv(df, path):
    """Persist a scrape: UTF-8-BOM, no index; create the dir if missing."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, encoding="utf-8-sig", index=False)

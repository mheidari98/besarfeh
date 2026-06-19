"""Bits every provider scraper shares: user-agent, headers, session, CSV writer."""

import sys
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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


def http_session():
    """requests.Session that retries transient errors (these portals 50x often)."""
    s = requests.Session()
    retry = Retry(
        total=3, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504)
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def warn_if_low(df, name, expected):
    """Warn on stderr if a scrape returns far fewer rows than expected.

    Catches silent drift: a site redesign that parses 3 rows instead of ~85
    would otherwise rank on bad data with no signal. Returns df for chaining.
    """
    if len(df) < expected * 0.5:
        print(
            f"warning: {name} scraped {len(df)} rows (expected ~{expected})",
            file=sys.stderr,
        )
    return df


def write_csv(df, path):
    """Persist a scrape: UTF-8-BOM, no index; create the dir if missing."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, encoding="utf-8-sig", index=False)

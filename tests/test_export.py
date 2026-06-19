"""Tests for the CSV -> uniform JSON export that feeds the web UI.

Uses the committed DB/*.csv as fixtures (run from the repo root).
"""

from besarfeh.export import to_records

_FIELDS = {
    "provider",
    "name",
    "volume_mb",
    "duration",
    "price",
    "price_per_mb",
    "buy_code",
}


def test_records_have_uniform_shape():
    recs = to_records()
    assert len(recs) > 100  # mci ~40 + mtn ~38 + rightel ~85
    assert all(set(r) >= _FIELDS for r in recs)


def test_all_three_providers_present():
    assert {r["provider"] for r in to_records()} == {"mci", "mtn", "rightel"}


def test_price_per_mb_matches_price_over_volume():
    for r in to_records():
        if r["volume_mb"]:
            assert abs(r["price_per_mb"] - r["price"] / r["volume_mb"]) < 0.5
        else:
            assert r["price_per_mb"] is None  # unrankable (e.g. mci unlimited)

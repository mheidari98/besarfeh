"""Tests for the greedy ranking core, with SCRAPERS monkeypatched (no network)."""

import pandas as pd

from compare_internet_packages import ranking


def _patch(monkeypatch, scrapers):
    monkeypatch.setattr(ranking, "SCRAPERS", scrapers)


def test_rank_picks_cheapest_per_mb_and_counts(monkeypatch):
    # a: 1000MB @10000 -> 10 t/MB (best); c: 2000MB @30000 -> 15 t/MB; b: NaN -> dropped
    df = pd.DataFrame(
        {
            "volume": [1000, float("nan"), 2000],
            "price": [10000, 5000, 30000],
            "name": ["a", "b", "c"],
        }
    )
    _patch(monkeypatch, {"fake": lambda: df})

    plan = ranking.rank(["fake"], 25000)

    assert len(plan) == 1
    assert plan[0]["count"] == 2  # 25000 // 10000
    assert plan[0]["provider"] == "fake"
    assert plan[0]["pack"]["name"] == "a"  # NaN-volume "b" never ranked


def test_rank_empty_when_no_provider_matches(monkeypatch):
    _patch(monkeypatch, {"fake": lambda: pd.DataFrame({"volume": [1], "price": [1]})})
    assert ranking.rank(["nonexistent"], 10000) == []

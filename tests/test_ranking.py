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


_GOOD = pd.DataFrame({"volume": [1000], "price": [10000], "name": ["g"]})


def test_one_provider_failure_does_not_kill_others(monkeypatch):
    def boom():
        raise RuntimeError("site down")

    _patch(monkeypatch, {"bad": boom, "good": lambda: _GOOD})
    plan = ranking.rank(["bad", "good"], 10000)
    assert len(plan) == 1 and plan[0]["pack"]["name"] == "g"


def test_empty_provider_is_skipped_not_crash(monkeypatch):
    _patch(monkeypatch, {"empty": lambda: pd.DataFrame(), "good": lambda: _GOOD})
    plan = ranking.rank(["empty", "good"], 10000)
    assert len(plan) == 1 and plan[0]["pack"]["name"] == "g"


def test_zero_price_pack_does_not_crash(monkeypatch):
    df = pd.DataFrame(
        {"volume": [100, 1000], "price": [0, 10000], "name": ["free", "x"]}
    )
    _patch(monkeypatch, {"f": lambda: df})
    plan = ranking.rank(["f"], 10000)  # must not raise ZeroDivisionError
    assert all(p["pack"]["name"] != "free" for p in plan)
    assert any(p["pack"]["name"] == "x" for p in plan)


def test_compare_reports_when_nothing_bought(monkeypatch, capsys):
    _patch(monkeypatch, {"good": lambda: _GOOD})
    ranking.compare(["good"], 100)  # budget below cheapest pack
    out = capsys.readouterr().out
    assert "No packages" in out

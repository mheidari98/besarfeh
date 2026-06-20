"""Tests for the CLI-level refresh entrypoint (used by the daily data Action)."""

import pandas as pd

from besarfeh import cli


def test_refresh_runs_all_scrapers_despite_one_failure(monkeypatch):
    called = []

    def ok(name):
        def scrape():
            called.append(name)
            return pd.DataFrame()

        return scrape

    def boom():
        raise RuntimeError("site down")

    monkeypatch.setattr(cli, "SCRAPERS", {"a": ok("a"), "bad": boom, "c": ok("c")})
    cli.refresh()  # must not raise
    assert called == ["a", "c"]  # bad skipped, others still ran

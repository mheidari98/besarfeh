"""Tests for the shared scraper helpers: retry session + drift warning + CSV."""

import pandas as pd
import requests

from besarfeh.scrapers._shared import http_session, warn_if_low, write_csv


def test_warn_if_low_warns_on_few_rows(capsys):
    warn_if_low(pd.DataFrame({"a": [1, 2]}), "mci", 40)
    err = capsys.readouterr().err
    assert "mci" in err and "2" in err


def test_warn_if_low_silent_when_healthy(capsys):
    warn_if_low(pd.DataFrame({"a": range(40)}), "mci", 40)
    assert capsys.readouterr().err == ""


def test_warn_if_low_returns_the_df():
    df = pd.DataFrame({"a": [1]})
    assert warn_if_low(df, "x", 40) is df


def test_http_session_retries_transient_errors():
    s = http_session()
    assert isinstance(s, requests.Session)
    assert s.get_adapter("https://example.com").max_retries.total == 3


def test_write_csv_sorts_rows_for_stable_diffs(tmp_path):
    df = pd.DataFrame({"name": ["b", "a"], "volume": [1, 1], "price": [1, 1]})
    p = tmp_path / "x.csv"
    write_csv(df, str(p))
    assert list(pd.read_csv(p)["name"]) == ["a", "b"]  # deterministic order


def test_write_csv_sort_ignores_price(tmp_path):
    # two rows identical except price -> price must not reorder them (stays stable)
    df = pd.DataFrame({"name": ["a", "a"], "volume": [1, 1], "price": [90, 10]})
    p = tmp_path / "x.csv"
    write_csv(df, str(p))
    assert list(pd.read_csv(p)["price"]) == [90, 10]

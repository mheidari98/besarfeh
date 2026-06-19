"""Tests for the shared scraper helpers: retry session + drift warning."""

import pandas as pd
import requests

from besarfeh.scrapers._shared import http_session, warn_if_low


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

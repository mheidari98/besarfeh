"""Pure, network-free parser tests for the RighTel name parsers.

These lock in the regex behavior that silently breaks when the site changes
pack-name wording (volume / duration / time-range). No mocking needed.
"""

from besarfeh.scrapers.rightel import (
    _FA_DIGITS,
    _duration,
    _time_range,
    _volume_mb,
)


def test_volume_mb_gigabytes():
    assert _volume_mb("1 روزه 10 گیگابایت") == 10 * 1024


def test_volume_mb_megabytes():
    assert _volume_mb("500 مگابایت") == 500


def test_volume_mb_decimal_gigabytes():
    assert _volume_mb("1.5 گیگابایت") == 1.5 * 1024


def test_volume_mb_voice_pack_is_none():
    assert _volume_mb("100 دقیقه مکالمه") is None


def test_volume_mb_persian_digits_normalized():
    # Defensive: site used to return Persian numerals; caller translates first.
    assert _volume_mb("۲ گیگابایت".translate(_FA_DIGITS)) == 2 * 1024


def test_duration_extracted():
    assert _duration("1 روزه 10 گیگابایت") == "1 روزه"
    assert _duration("1 ماهه 15 گیگابایت") == "1 ماهه"


def test_duration_absent_is_empty():
    assert _duration("10 گیگابایت") == ""


def test_time_range_night():
    assert _time_range("بسته شبانه 2 گیگابایت") == "شبانه"


def test_time_range_iraq():
    assert _time_range("بسته ویژه عراق") == "ویژه عراق"


def test_time_range_international():
    assert _time_range("بسته بین الملل") == "بین الملل"


def test_time_range_normal_is_empty():
    assert _time_range("1 ماهه 15 گیگابایت") == ""

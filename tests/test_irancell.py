"""Pure tests for the Irancell per-pack row builder (no network)."""

from compare_internet_packages.scrapers.irancell import _pack_row


def _pack(**over):
    pack = {
        "name": {"fa": "4\xa0گیگابایت"},
        "price": 1000,
        "vat_percentage": 0.1,
        "sub_title": {"fa": ""},
        "specification_contents": [
            {"key": "traffic", "desc": {"fa": "4096"}},
            {"key": "package_type", "desc": {"fa": "30 روزه"}},
        ],
        "prepaid_offer_code": "PO123",
        "postpaid_offer_code": "PO999",
    }
    pack.update(over)
    return pack


def test_pack_row_basic_fields():
    row = _pack_row(_pack(), allow_limited_packs=False)
    assert row["pack-name"] == "4 گیگابایت"  # nbsp normalized
    assert row["volume"] == "4096"
    assert row["data-duration"] == "30 روزه"
    assert row["price"] == 1100  # 1000 * (1 + 0.1)
    assert row["offer-code"] == "PO123"  # prepaid preferred


def test_pack_row_offer_code_falls_back_to_postpaid():
    row = _pack_row(_pack(prepaid_offer_code=""), allow_limited_packs=False)
    assert row["offer-code"] == "PO999"


def test_pack_row_skips_non_data_pack():
    voice = _pack(specification_contents=[])  # no traffic spec
    assert _pack_row(voice, allow_limited_packs=False) is None


def test_pack_row_skips_time_limited_unless_allowed():
    night = _pack(sub_title={"fa": "شبانه"})
    assert _pack_row(night, allow_limited_packs=False) is None
    assert _pack_row(night, allow_limited_packs=True) is not None

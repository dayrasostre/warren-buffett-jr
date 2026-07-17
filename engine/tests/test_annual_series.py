"""Tests for wbj.cli._annual_series (EDGAR companyfacts -> annual series)."""

from wbj.cli import _annual_series


def _facts(tag_rows: dict[str, list[dict]]) -> dict:
    """Wrap {tag: rows} in a companyfacts-shaped dict."""
    return {
        "facts": {
            "us-gaap": {
                tag: {"units": {"USD": rows}} for tag, rows in tag_rows.items()
            }
        }
    }


def _row(start, end, val, filed="2026-01-01", form="10-K", fp="FY"):
    return {"start": start, "end": end, "val": val, "filed": filed, "form": form, "fp": fp}


def test_later_tags_fill_years_the_earlier_tag_leaves_empty():
    # An issuer that switched tags mid-history: neither tag spans it alone.
    facts = _facts(
        {
            "RevenueFromContractWithCustomerExcludingAssessedTax": [
                _row("2019-01-29", "2020-01-26", 200),
            ],
            "Revenues": [
                _row("2017-01-30", "2018-01-28", 100),
                _row("2023-01-30", "2024-01-28", 400),
            ],
        }
    )

    series = _annual_series(
        facts, ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"]
    )

    assert [r["val"] for r in series] == [100, 200, 400]


def test_earlier_tag_wins_a_year_both_tags_report():
    facts = _facts(
        {
            "RevenueFromContractWithCustomerExcludingAssessedTax": [
                _row("2019-01-29", "2020-01-26", 200),
            ],
            "Revenues": [
                _row("2019-01-29", "2020-01-26", 999),
            ],
        }
    )

    series = _annual_series(
        facts, ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"]
    )

    assert [r["val"] for r in series] == [200]


def test_quarterly_row_sharing_an_end_with_the_fiscal_year_is_excluded():
    # A 10-K reports Q4 and FY under fp="FY", both ending on the same date;
    # the 90-day row must never stand in for the year.
    facts = _facts(
        {
            "Revenues": [
                _row("2023-01-30", "2024-01-28", 400, filed="2024-02-21"),
                _row("2023-10-30", "2024-01-28", 90, filed="2024-02-22"),
            ]
        }
    )

    series = _annual_series(facts, ["Revenues"])

    assert [r["val"] for r in series] == [400]


def test_restatement_keeps_the_latest_filing_for_a_year():
    facts = _facts(
        {
            "Revenues": [
                _row("2023-01-30", "2024-01-28", 400, filed="2024-02-21"),
                _row("2023-01-30", "2024-01-28", 410, filed="2025-02-26"),
            ]
        }
    )

    series = _annual_series(facts, ["Revenues"])

    assert [r["val"] for r in series] == [410]


def test_instant_facts_have_no_duration_and_are_kept():
    # Balance-sheet items are instants: no `start` to measure.
    facts = _facts(
        {
            "StockholdersEquity": [
                {"end": "2024-01-28", "val": 42, "filed": "2024-02-21", "form": "10-K", "fp": "FY"},
            ]
        }
    )

    assert [r["val"] for r in _annual_series(facts, ["StockholdersEquity"])] == [42]


def test_non_annual_forms_are_ignored():
    facts = _facts(
        {
            "Revenues": [
                _row("2023-01-30", "2024-01-28", 400, form="10-Q", fp="Q3"),
            ]
        }
    )

    assert _annual_series(facts, ["Revenues"]) == []


def test_missing_tag_returns_empty_series():
    assert _annual_series(_facts({}), ["Revenues"]) == []

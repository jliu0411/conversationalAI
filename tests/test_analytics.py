import math
import pandas as pd
import pytest

from economic_ai.analytics import analyze, core_inflation, gdp_growth, quarterly_comparison


def test_gdp_yoy(data):
    gdp, _ = data
    growth = gdp_growth(gdp)
    assert math.isnan(growth.iloc[0])
    assert growth.iloc[4] == pytest.approx((1.01 ** 4 - 1) * 100)


def test_core_cpi_yoy_missing_12_month_earlier(data):
    _, cpi = data
    inflation = core_inflation(cpi)
    assert pd.isna(inflation.loc["2026-10-01"])
    assert inflation.loc["2026-09-01"] == pytest.approx((1.002 ** 12 - 1) * 100)


def test_latest_core_cpi_uses_last_valid_yoy(data):
    result = analyze("cpi_latest", *data)
    assert "September 2026" in result.answer
    assert "October 2026" in result.answer
    assert "index" in result.answer


def test_quarterly_cpi_rejects_incomplete_quarters(data):
    result = quarterly_comparison(*data)
    assert pd.Timestamp("2025-10-01") not in result.index
    assert pd.Timestamp("2026-07-01") in result.index
    assert result.index.is_unique
    assert list(result.columns) == ["Nominal GDP growth (YoY %)", "Core CPI inflation (YoY %)"]


@pytest.mark.parametrize("intent", [
    "gdp_latest", "gdp_history", "cpi_latest", "cpi_trend", "relationship", "comparison_chart", "summary",
])
def test_all_assignment_requests_produce_grounded_analytics(intent, data):
    result = analyze(intent, *data)
    assert result.answer
    assert len(result.data) > 0
    assert result.chart_kind in ("gdp_level", "cpi_rate", "comparison")


def test_gdp_ten_year_change_is_nominal(data):
    result = analyze("gdp_history", *data, years=10)
    assert "nominal" in result.answer.lower()
    assert "2016" in result.answer
    assert "2026" in result.answer


def test_relationship_has_warning(data):
    result = analyze("relationship", *data)
    assert "does not establish causation" in result.answer
    assert "nominal" in result.answer


def test_invalid_intent(data):
    with pytest.raises(ValueError, match="Unsupported intent"):
        analyze("predict_economy", *data)

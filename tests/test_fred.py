import pandas as pd
import pytest

from economic_ai.fred import FredDataError, parse_fred_csv, download_series


def test_csv_parser_handles_missing_values():
    dates = pd.date_range("2020-01-01", periods=15, freq="MS")
    rows = "DATE,CPILFESL\n" + "\n".join(
        f"{date.strftime('%Y-%m-%d')},{'.' if i == 5 else 250+i}"
        for i, date in enumerate(dates)
    )
    result = parse_fred_csv(rows, "CPILFESL")
    assert len(result) == 15
    assert pd.isna(result.iloc[5])
    assert result.iloc[-1] == 264


def test_csv_parser_accepts_observation_date():
    dates = pd.date_range("2015-01-01", periods=16, freq="QS")
    raw = "observation_date,GDP\n" + "\n".join(f"{d.date()},{20000+i}" for i, d in enumerate(dates))
    result = parse_fred_csv(raw, "GDP")
    assert len(result) == 16
    assert result.iloc[0] == 20000


def test_reject_bad_columns():
    with pytest.raises(FredDataError):
        parse_fred_csv("DATE,WHATEVER\n2020-01-01,2\n", "GDP")


def test_reject_nonwhitelisted_series():
    with pytest.raises(ValueError):
        download_series("OTHER")

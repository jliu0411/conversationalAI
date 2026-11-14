"""Read original observations from FRED's publicly downloadable CSV graphs."""
from __future__ import annotations

from io import StringIO
import pandas as pd
import requests

VALID_SERIES = {"GDP", "CPILFESL"}
SERIES_PAGES = {
    "GDP": "https://fred.stlouisfed.org/series/GDP",
    "CPILFESL": "https://fred.stlouisfed.org/series/CPILFESL",
}
CSV_ENDPOINT = "https://fred.stlouisfed.org/graph/fredgraph.csv"


class FredDataError(RuntimeError):
    """FRED data is not accessible or usable."""


def parse_fred_csv(csv_text: str, series_id: str) -> pd.Series:
    """Parse FRED export; preserve missing observations instead of inventing values."""
    if series_id not in VALID_SERIES:
        raise ValueError(f"Unsupported series: {series_id}")
    try:
        frame = pd.read_csv(StringIO(csv_text))
        date_col = next((col for col in ("observation_date", "DATE", "date") if col in frame), None)
        if date_col is None or series_id not in frame:
            raise FredDataError(f"Unexpected columns for {series_id}: {list(frame.columns)}")
        date = pd.to_datetime(frame[date_col], errors="coerce")
        value = pd.to_numeric(frame[series_id], errors="coerce")
        data = pd.Series(value.to_numpy(), index=pd.DatetimeIndex(date), name=series_id)
        data = data.loc[~data.index.isna()].sort_index()
        data = data.loc[~data.index.duplicated(keep="last")]
        # Calendar frequencies: GDP quarter starts, CPILFESL month starts.
        data = data.asfreq("QS" if series_id == "GDP" else "MS")
        if data.dropna().empty or len(data.dropna()) < 13:
            raise FredDataError(f"Too few usable observations for {series_id}")
        return data
    except FredDataError:
        raise
    except Exception as exc:
        raise FredDataError(f"Could not parse FRED {series_id} CSV: {exc}") from exc


def download_series(series_id: str, timeout: int = 30) -> pd.Series:
    if series_id not in VALID_SERIES:
        raise ValueError(f"Unsupported series: {series_id}")
    try:
        response = requests.get(
            CSV_ENDPOINT,
            params={"id": series_id},
            headers={"User-Agent": "EconomicAI-education/1.0", "Accept": "text/csv"},
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise FredDataError(
            f"Could not reach FRED for {series_id}. Check internet access and retry. Details: {exc}"
        ) from exc
    return parse_fred_csv(response.text, series_id)

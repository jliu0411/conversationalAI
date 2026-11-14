"""Reproducible economic calculations. All displayed numbers originate here."""
from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass
class AnalysisResult:
    title: str
    answer: str
    data: pd.DataFrame
    chart_kind: str
    period: str
    notes: str


def year_over_year(series: pd.Series, periods_per_year: int) -> pd.Series:
    """YoY percent change, NOT forward-filling missing observations."""
    return 100 * (series / series.shift(periods_per_year) - 1)


def gdp_growth(gdp: pd.Series) -> pd.Series:
    return year_over_year(gdp.asfreq("QS"), 4).rename("Nominal GDP growth (YoY %)")


def core_inflation(cpi: pd.Series) -> pd.Series:
    return year_over_year(cpi.asfreq("MS"), 12).rename("Core CPI inflation (YoY %)")


def quarterly_comparison(gdp: pd.Series, cpi: pd.Series) -> pd.DataFrame:
    """Match nominal GDP YoY to YoY Core CPI using *complete* quarterly CPI averages."""
    monthly = cpi.asfreq("MS")
    mean_index = monthly.resample("QS").mean()
    complete = monthly.resample("QS").count() == 3
    quarterly_cpi = mean_index.where(complete)
    quarterly_cpi_yoy = year_over_year(quarterly_cpi, 4)
    return pd.concat(
        [gdp_growth(gdp), quarterly_cpi_yoy.rename("Core CPI inflation (YoY %)")],
        axis=1,
        join="inner",
    ).dropna()


def _window(series: pd.Series | pd.DataFrame, years: int):
    if series.empty:
        return series
    cutoff = series.index.max() - pd.DateOffset(years=years)
    return series.loc[series.index >= cutoff]


def _latest(series: pd.Series, label: str) -> tuple[pd.Timestamp, float]:
    values = series.dropna()
    if values.empty:
        raise ValueError(f"No valid {label} observations were found")
    date = values.index[-1]
    return date, float(values.iloc[-1])


def _q(date: pd.Timestamp) -> str:
    return f"{date.year} Q{date.quarter}"


def _m(date: pd.Timestamp) -> str:
    return date.strftime("%B %Y")


def analyze(intent: str, gdp: pd.Series, cpi: pd.Series, years: int = 10) -> AnalysisResult:
    """Answer supported requests using only downloaded GDP and CPILFESL values."""
    years = max(1, min(30, int(years)))
    gd, gv = _latest(gdp, "GDP")
    cd, cv = _latest(cpi, "Core CPI")
    gy = gdp_growth(gdp)
    cy = core_inflation(cpi)
    gyd, gyv = _latest(gy, "GDP growth")
    cyd, cyv = _latest(cy, "Core CPI inflation")

    fundamentals = (
        "GDP is nominal (current-dollar) GDP, billions of dollars at a seasonally "
        "adjusted annual rate (not inflation-adjusted). Core CPI (CPILFESL) is a "
        "monthly, seasonally adjusted price index. YoY changes are percentages."
    )
    if intent == "gdp_latest":
        answer = (
            f"The latest reported U.S. nominal GDP observation is **${gv/1000:,.3f} trillion** "
            f"(**${gv:,.3f} billion**) for **{_q(gd)}**. "
            f"Nominal GDP grew **{gyv:+.2f}% year over year** in **{_q(gyd)}**. "
            "GDP here is reported at a seasonally adjusted annual rate; it is not real GDP."
        )
        return AnalysisResult("Latest U.S. GDP", answer, _window(gdp.to_frame("Nominal GDP ($ billions, SAAR)"), 5), "gdp_level", _q(gd), fundamentals)

    if intent == "gdp_history":
        segment = _window(gdp.dropna(), years)
        start, end = segment.iloc[0], segment.iloc[-1]
        total = 100 * (end / start - 1)
        elapsed = (segment.index[-1] - segment.index[0]).days / 365.2425
        annual = ((end / start) ** (1 / elapsed) - 1) * 100 if elapsed > 0 else 0
        answer = (
            f"From **{_q(segment.index[0])}** to **{_q(segment.index[-1])}**, "
            f"nominal GDP rose from **${start/1000:,.2f}T** to **${end/1000:,.2f}T**, "
            f"a **{total:+.2f}%** change (approximately **{annual:+.2f}%** compound annual growth). "
            "These nominal changes include price increases and should not be read as real output growth."
        )
        return AnalysisResult(f"GDP over roughly {years} years", answer, segment.to_frame("Nominal GDP ($ billions, SAAR)"), "gdp_level", f"{_q(segment.index[0])} to {_q(segment.index[-1])}", fundamentals)

    if intent == "cpi_latest":
        dated = "" if cd == cyd else f" The latest index observation is **{_m(cd)}**, but the latest computable YoY rate is **{_m(cyd)}** because a required year-earlier observation may be missing."
        answer = (
            f"The latest **calculable 12-month Core CPI inflation rate** is "
            f"**{cyv:+.2f}%** for **{_m(cyd)}**. The latest Core CPI *index level* "
            f"is **{cv:,.3f}** for **{_m(cd)}**; the index is not an inflation percentage."
            + dated
        )
        return AnalysisResult("Latest Core CPI inflation", answer, _window(cy.dropna().to_frame("Core CPI inflation (YoY %)"), 5), "cpi_rate", _m(cyd), fundamentals)

    if intent == "cpi_trend":
        segment = _window(cy.dropna(), years)
        begin = float(segment.iloc[0])
        end = float(segment.iloc[-1])
        peak_date = segment.idxmax()
        peak = float(segment.max())
        answer = (
            f"Over roughly **{years} years**, the Core CPI 12-month inflation rate "
            f"went from **{begin:.2f}%** in **{_m(segment.index[0])}** "
            f"to **{end:.2f}%** in **{_m(segment.index[-1])}**. "
            f"It peaked at **{peak:.2f}%** in **{_m(peak_date)}** during this window. "
            "This measures changes in the price index, not the level of prices."
        )
        return AnalysisResult(f"Core CPI inflation over roughly {years} years", answer, segment.to_frame("Core CPI inflation (YoY %)"), "cpi_rate", f"{_m(segment.index[0])} to {_m(segment.index[-1])}", fundamentals)

    if intent in {"relationship", "comparison_chart"}:
        match = _window(quarterly_comparison(gdp, cpi), years)
        if len(match) < 3:
            raise ValueError("At least three aligned quarters are required to compare growth and inflation")
        correlation = float(match.iloc[:, 0].corr(match.iloc[:, 1]))
        answer = (
            f"For **{len(match)} complete, aligned quarters** from **{_q(match.index[0])}** "
            f"to **{_q(match.index[-1])}**, the Pearson correlation between "
            f"**nominal GDP YoY growth** and **Core CPI YoY inflation** is **{correlation:+.2f}**. "
            "The figure plots both annual changes on one quarterly timeline. "
            "Correlation is descriptive and does not establish causation. "
            "Nominal GDP growth includes price effects, so this is not a real-growth-versus-inflation comparison."
        )
        return AnalysisResult("GDP growth vs. Core CPI inflation", answer, match, "comparison", f"{_q(match.index[0])} to {_q(match.index[-1])}", fundamentals)

    if intent == "summary":
        match = _window(quarterly_comparison(gdp, cpi), years)
        answer = (
            f"**GDP:** nominal U.S. GDP is **${gv/1000:,.3f}T** in **{_q(gd)}**, "
            f"with **{gyv:+.2f}%** YoY nominal growth in **{_q(gyd)}**. "
            f"**Prices:** the Core CPI index is **{cv:,.3f}** in **{_m(cd)}**, "
            f"while the latest computable 12-month Core CPI inflation rate is **{cyv:+.2f}%** "
            f"for **{_m(cyd)}**. Inflation is the rate of change in the index, "
            "not the index level. These series describe economic activity and price pressures, "
            "but by themselves do not prove one causes the other."
        )
        return AnalysisResult("U.S. economic indicators - summary", answer, match, "comparison", f"Latest observations: {_q(gd)}, {_m(cd)}", fundamentals)

    raise ValueError(f"Unsupported intent: {intent}")

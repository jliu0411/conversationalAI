"""Reproduce optional report figures using FRED table values verified 2026-11-13.

These values are a fixed, *partial* historical snapshot for the report only.
The interactive app does not use them; it always downloads complete FRED series.
Sources: https://fred.stlouisfed.org/data/GDP and /data/CPILFESL.
"""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

from economic_ai.analytics import gdp_growth, core_inflation, quarterly_comparison

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
FIGURES.mkdir(exist_ok=True)

# Quarterly GDP levels: USD billions, nominal SAAR (FRED GDP).
GDP = {
    "2023-01-01":27241.282, "2023-04-01":27533.925, "2023-07-01":28064.032, "2023-10-01":28464.306,
    "2024-01-01":28793.191, "2024-04-01":29232.964, "2024-07-01":29568.256, "2024-10-01":29929.552,
    "2025-01-01":30171.979, "2025-04-01":30630.174, "2025-07-01":31180.493, "2025-10-01":31462.523,
    "2026-01-01":31906.274, "2026-04-01":32563.030, "2026-07-01":33010.036,
}
# Monthly Core CPI: 1982-1984=100, seasonally adjusted. October 2025 is missing in FRED.
CPI = {
    "2023-10-01":311.457, "2023-11-01":312.392, "2023-12-01":313.195,
    "2024-01-01":314.319, "2024-02-01":315.564, "2024-03-01":316.792,
    "2024-04-01":317.649, "2024-05-01":318.095, "2024-06-01":318.390,
    "2024-07-01":318.940, "2024-08-01":319.750, "2024-09-01":320.732,
    "2024-10-01":321.731, "2024-11-01":322.657, "2024-12-01":323.259,
    "2025-01-01":324.638, "2025-02-01":325.465, "2025-03-01":325.690,
    "2025-04-01":326.467, "2025-05-01":326.893, "2025-06-01":327.658,
    "2025-07-01":328.682, "2025-08-01":329.700, "2025-09-01":330.418,
    "2025-10-01":None, "2025-11-01":331.043, "2025-12-01":331.814,
    "2026-01-01":332.793, "2026-02-01":333.512, "2026-03-01":334.165,
    "2026-04-01":335.423, "2026-05-01":336.121, "2026-06-01":336.065,
    "2026-07-01":336.789, "2026-08-01":337.765, "2026-09-01":338.896,
    "2026-10-01":339.900,
}


def as_series(table, name, freq):
    series = pd.Series(table, dtype="float64", name=name)
    series.index = pd.to_datetime(series.index)
    return series.asfreq(freq)


def save_fig(fig, name):
    fig.savefig(FIGURES / name, dpi=175, bbox_inches="tight")
    plt.close(fig)


def main():
    gdp = as_series(GDP, "GDP", "QS")
    cpi = as_series(CPI, "CPILFESL", "MS")
    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.plot(gdp.index, gdp.values / 1000, linewidth=2.7, marker="o", markersize=3)
    ax.set(title="Nominal U.S. GDP | Q1 2023-Q3 2026", ylabel="Trillions of USD, SAAR", xlabel="Quarter")
    ax.grid(alpha=.25)
    save_fig(fig, "verified_recent_gdp.png")

    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.plot(cpi.index, cpi.values, linewidth=2.6)
    ax.set(title="Core CPI Index | Oct 2023-Oct 2026", ylabel="Index, 1982-84 = 100", xlabel="Month")
    ax.grid(alpha=.25)
    save_fig(fig, "verified_recent_cpi.png")

    comparison = quarterly_comparison(gdp, cpi)
    fig, ax = plt.subplots(figsize=(9, 3.8))
    for column in comparison.columns:
        ax.plot(comparison.index, comparison[column], marker="o", linewidth=2.2, label=column)
    ax.set(title="Nominal GDP growth vs. Core CPI inflation | Available aligned quarters", ylabel="Year-over-year change (%)", xlabel="Quarter")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=.25)
    save_fig(fig, "verified_recent_comparison.png")

    print("Verified snapshot: GDP", f"${gdp.dropna().iloc[-1]/1000:.3f}T", "Q3 2026")
    print("Verified snapshot: core inflation", f"{core_inflation(cpi).dropna().iloc[-1]:.2f}%", "Sep 2026")
    print("Compared aligned quarters:", len(comparison), ", last", comparison.index.max())


if __name__ == "__main__":
    main()

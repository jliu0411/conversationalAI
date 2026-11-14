import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def data():
    q = pd.date_range("2010-01-01", "2026-07-01", freq="QS")
    m = pd.date_range("2010-01-01", "2026-10-01", freq="MS")
    gdp = pd.Series(15000 * (1.01 ** np.arange(len(q))), index=q, name="GDP")
    cpi = pd.Series(210 * (1.002 ** np.arange(len(m))), index=m, name="CPILFESL")
    # Reflect a missing index observation as a reproducible edge case.
    cpi.loc["2025-10-01"] = np.nan
    return gdp, cpi

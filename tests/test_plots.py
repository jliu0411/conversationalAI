from economic_ai.analytics import analyze
from economic_ai.plots import make_chart


def test_charts_use_result_data(data):
    result = analyze("comparison_chart", *data)
    fig = make_chart(result)
    assert len(fig.data) == 2
    assert len(fig.data[0].x) == len(result.data)

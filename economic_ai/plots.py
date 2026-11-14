"""Charts are rendered entirely from FRED-derived computed series."""
import plotly.graph_objects as go

from economic_ai.analytics import AnalysisResult


COLORS = ("#1463a6", "#e18a2b")


def make_chart(result: AnalysisResult) -> go.Figure:
    frame = result.data
    fig = go.Figure()
    for idx, column in enumerate(frame.columns):
        fig.add_trace(go.Scatter(
            x=frame.index,
            y=frame[column],
            mode="lines",
            name=column,
            line={"width": 2.8, "color": COLORS[idx % len(COLORS)]},
            connectgaps=False,
            hovertemplate="%{x|%b %Y}<br>%{y:,.2f}<extra>%{fullData.name}</extra>",
        ))
    ylabel = {
        "gdp_level": "Billions of nominal dollars (SAAR)",
        "cpi_rate": "12-month change (%)",
        "comparison": "Year-over-year change (%)",
    }[result.chart_kind]
    fig.update_layout(
        title=result.title,
        template="plotly_white",
        xaxis_title="Observation date",
        yaxis_title=ylabel,
        hovermode="x unified",
        legend={"orientation": "h", "y": -0.24, "x": 0.0},
        margin={"l": 25, "r": 20, "t": 58, "b": 80},
        height=420,
    )
    return fig

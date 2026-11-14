"""Conversational AI for Economic Data Analysis - SJSU assignment."""
from __future__ import annotations

import os
from dotenv import load_dotenv
import streamlit as st

from economic_ai.analytics import analyze, core_inflation, gdp_growth
from economic_ai.assistant import GEMINI_DEFAULT_MODEL, Intent, explain_result, route_question
from economic_ai.fred import FredDataError, SERIES_PAGES, download_series
from economic_ai.plots import make_chart

load_dotenv()
st.set_page_config(page_title="EconLens | U.S. GDP and Core CPI", page_icon="📈", layout="wide")


@st.cache_data(ttl=3600, show_spinner=False)
def get_fred_data():
    """Refresh FRED only once per hour per cached Streamlit process."""
    return download_series("GDP"), download_series("CPILFESL")


st.title("📈 EconLens")
st.caption("Conversational AI for U.S. GDP and Core CPI | Evidence: FRED GDP and CPILFESL")

with st.sidebar:
    st.header("Data & configuration")
    st.markdown("**Official datasets**")
    st.markdown(f"- [GDP (nominal, quarterly)]({SERIES_PAGES['GDP']})")
    st.markdown(f"- [CPILFESL (Core CPI, monthly)]({SERIES_PAGES['CPILFESL']})")
    st.caption("FRED CSV data are refreshed at most once per hour. Historical values may be revised.")
    if st.button("Refresh FRED data", use_container_width=True):
        get_fred_data.clear()
        st.rerun()
    ai_enabled = bool(os.environ.get("GEMINI_API_KEY"))
    if ai_enabled:
        st.success(f"AI enabled: {os.environ.get('GEMINI_MODEL', GEMINI_DEFAULT_MODEL)}")
    else:
        st.info("Rule-based demonstration mode. Set GEMINI_API_KEY in .env for LLM routing and explanations.")
    st.divider()
    st.markdown("**Example questions**")
    examples = [
        "What is the latest reported U.S. GDP?",
        "How has U.S. GDP changed over the past 10 years?",
        "What is the current Core CPI inflation rate?",
        "How has Core CPI inflation changed over the past five years?",
        "What is the relationship between GDP growth and Core CPI inflation?",
        "Generate a visualization comparing GDP growth and Core CPI inflation over time.",
        "Summarize the key economic trends observed in both datasets.",
    ]
    for i, item in enumerate(examples):
        if st.button(item, key=f"example_{i}", use_container_width=True):
            st.session_state.queued_question = item
    st.divider()
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.previous_intent = None
        st.rerun()

try:
    with st.spinner("Retrieving official FRED observations..."):
        gdp, cpi = get_fred_data()
except FredDataError as exc:
    st.error(str(exc))
    st.info("This app needs an internet connection to retrieve official FRED CSV observations. It intentionally does not fabricate or silently substitute offline economic data.")
    st.stop()

with st.container():
    gdp_latest = gdp.dropna()
    cpi_latest = cpi.dropna()
    growth = gdp_growth(gdp).dropna()
    inflation = core_inflation(cpi).dropna()
    cols = st.columns(3)
    cols[0].metric("Nominal GDP", f"${gdp_latest.iloc[-1]/1000:,.2f}T")
    cols[0].caption(f"{gdp_latest.index[-1].year} Q{gdp_latest.index[-1].quarter} (SAAR)")
    cols[1].metric("GDP growth (YoY)", f"{growth.iloc[-1]:+.2f}%")
    cols[1].caption(f"{growth.index[-1].year} Q{growth.index[-1].quarter}")
    cols[2].metric("Core CPI inflation (YoY)", f"{inflation.iloc[-1]:+.2f}%")
    cols[2].caption(inflation.index[-1].strftime("%b %Y"))
    if cpi_latest.index[-1] != inflation.index[-1]:
        st.caption("The newest CPI index date differs from the newest computable 12-month inflation rate because a year-earlier observation may be missing.")

st.divider()
st.subheader("Ask about U.S. economic data")
st.caption("Answers use computed values and observation dates; interactive charts can be explored and their data downloaded.")
if "messages" not in st.session_state:
    st.session_state.messages = []
if "previous_intent" not in st.session_state:
    st.session_state.previous_intent = None

for item in st.session_state.messages:
    with st.chat_message(item["role"]):
        st.markdown(item["content"])
        if item.get("interpretation"):
            st.markdown("**AI interpretation:** " + item["interpretation"])
        if item.get("result"):
            result = item["result"]
            st.plotly_chart(make_chart(result), use_container_width=True)
            with st.expander("See calculations and download plot data"):
                st.dataframe(result.data.tail(30), use_container_width=True)
                st.download_button(
                    "Download displayed chart data (CSV)",
                    result.data.to_csv(index_label="DATE").encode("utf-8"),
                    file_name=f"fred_{item['intent']}.csv",
                    mime="text/csv", key=f"download_{item['id']}",
                )
                st.caption(result.notes)
            st.markdown("Sources: [FRED GDP](https://fred.stlouisfed.org/series/GDP) · [FRED CPILFESL](https://fred.stlouisfed.org/series/CPILFESL)")

queued = st.session_state.pop("queued_question", None)
question = st.chat_input("Ask about GDP, inflation, comparisons, or trends...") or queued
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Calculating indicators and preparing an answer..."):
            current_intent, fallback_notice = route_question(question, st.session_state.previous_intent)
            try:
                result = analyze(current_intent.name, gdp, cpi, current_intent.years)
                interpretation = explain_result(question, result)
            except (ValueError, IndexError) as exc:
                result = None
                interpretation = None
                content = f"The available series cannot answer that request: {exc}"
            else:
                content = result.answer
                st.session_state.previous_intent = current_intent
        st.markdown(content)
        if interpretation:
            st.markdown("**AI interpretation:** " + interpretation)
        if fallback_notice:
            st.caption(fallback_notice)
        if result is not None:
            st.plotly_chart(make_chart(result), use_container_width=True, key=f"chat_chart_{i}")
            with st.expander("See calculations and download plot data"):
                st.dataframe(result.data.tail(30), use_container_width=True)
                st.download_button(
                    "Download displayed chart data (CSV)",
                    result.data.to_csv(index_label="DATE").encode("utf-8"),
                    file_name=f"fred_{current_intent.name}.csv", mime="text/csv",
                    key=f"download_{len(st.session_state.messages)}",
                )
                st.caption(result.notes)
            st.markdown("Sources: [FRED GDP](https://fred.stlouisfed.org/series/GDP) · [FRED CPILFESL](https://fred.stlouisfed.org/series/CPILFESL)")
    st.session_state.messages.append({
        "role": "assistant", "content": content, "result": result,
        "interpretation": interpretation, "intent": current_intent.name,
        "id": len(st.session_state.messages),
    })

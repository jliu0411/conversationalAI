"""Gemini-assisted intent detection and optional FRED-grounded interpretation.

All economic quantities come from the deterministic analytics module, never
from Gemini. If Gemini is unavailable, the app still answers with rules.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
from typing import Any

from economic_ai.analytics import AnalysisResult

GEMINI_DEFAULT_MODEL = "gemini-3.5-flash-lite"
ALLOWED_INTENTS = {
    "gdp_latest", "gdp_history", "cpi_latest", "cpi_trend",
    "relationship", "comparison_chart", "summary",
}
DEFAULT_YEARS = {
    "gdp_latest": 5,
    "gdp_history": 10,
    "cpi_latest": 5,
    "cpi_trend": 5,
    "relationship": 10,
    "comparison_chart": 10,
    "summary": 10,
}


@dataclass(frozen=True)
class Intent:
    name: str
    years: int
    method: str  # "AI" or "Rules"


def _extract_years(question: str) -> int | None:
    lower = question.lower()
    patterns = [
        r"(?:last|past|previous|over|for|in)\s+(\d{1,2})\s*(?:years|yrs)\b",
        r"\b(\d{1,2})\s*[- ]?year\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, lower)
        if match:
            return min(30, max(1, int(match.group(1))))
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
             "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
             "fifteen": 15, "twenty": 20, "thirty": 30}
    for word, number in words.items():
        if re.search(rf"\b{word}\s+(?:years|yrs)\b", lower):
            return number
    return None


def rule_based_intent(question: str, previous: Intent | None = None) -> Intent:
    """Offline fallback for assignment examples and short conversational follow-ups."""
    q = question.lower()
    has_gdp = any(t in q for t in ("gdp", "gross domestic", "economic output"))
    has_core = any(t in q for t in ("cpi", "inflation", "consumer price", "prices", "price index"))
    visualization = any(t in q for t in ("chart", "graph", "visual", "plot", "draw"))
    relationship = any(t in q for t in ("relationship", "relate", "correlat", "association", "connected", "link between"))
    history = any(t in q for t in ("changed", "change over", "trend", "histor", "past", "last", "over time", "previous", "years", "year-long"))
    summary = any(t in q for t in ("summari", "overview", "key economic", "both datasets", "both series", "economic trends"))

    if summary:
        name = "summary"
    elif relationship:
        name = "relationship"
    elif (has_gdp and has_core) or (visualization and "compar" in q):
        name = "comparison_chart"
    elif has_core:
        name = "cpi_trend" if (history or visualization) else "cpi_latest"
    elif has_gdp:
        name = "gdp_history" if (history or visualization) else "gdp_latest"
    elif previous is not None and (history or _extract_years(q) is not None):
        name = previous.name
        if name == "gdp_latest":
            name = "gdp_history"
        if name == "cpi_latest":
            name = "cpi_trend"
    else:
        name = "summary"
    years = _extract_years(q)
    if years is None and previous is not None and not has_gdp and not has_core and not summary:
        years = previous.years
    return Intent(name, years or DEFAULT_YEARS[name], "Rules")


def _json_object(output: str) -> dict[str, Any]:
    """Parse a constrained classification object, tolerating markdown wrappers."""
    try:
        start, end = output.index("{"), output.rindex("}") + 1
        result = json.loads(output[start:end])
        return result if isinstance(result, dict) else {}
    except (ValueError, json.JSONDecodeError):
        return {}


def _api_client(api_key: str | None = None):
    """Create the official Google Gen AI SDK client using a Gemini API key."""
    from google import genai

    # Explicitly use GEMINI_API_KEY, avoiding accidental use of another Google key.
    return genai.Client(api_key=api_key or os.environ["GEMINI_API_KEY"])


def route_question(
    question: str,
    previous: Intent | None = None,
    *,
    api_key: str | None = None,
    model: str | None = None,
) -> tuple[Intent, str | None]:
    """Gemini classifies the question; invalid/error responses fall back to rules."""
    fallback = rule_based_intent(question, previous)
    if not (api_key or os.environ.get("GEMINI_API_KEY")):
        return fallback, None
    catalog = ", ".join(sorted(ALLOWED_INTENTS))
    prompt = (
        f"User question: {question}\n"
        f"Prior intent: {previous.name if previous else 'none'}; prior years: {previous.years if previous else 'none'}\n"
        "Return ONLY a JSON object with keys 'intent' and 'years'. "
        f"Choose an intent from: {catalog}. "
        "gdp_latest: current GDP; gdp_history: change over period; "
        "cpi_latest: current Core CPI YoY; cpi_trend: inflation trend; "
        "relationship: correlation; comparison_chart: chart both; summary: overarching view. "
        "Default periods: GDP 10 years, CPI trend 5, comparison 10. "
        "For follow-ups use prior intent. Clamp years to 1..30. "
        "Do not include any observations or calculations."
    )
    try:
        response = _api_client(api_key).models.generate_content(
            model=model or os.environ.get("GEMINI_MODEL", GEMINI_DEFAULT_MODEL),
            contents=prompt,
            config={
                "system_instruction": "You classify natural-language questions into a fixed economics analytics schema.",
                "response_mime_type": "application/json",
                "max_output_tokens": 256,
                "temperature": 0,
            },
        )
        data = _json_object(response.text or "")
        name = data.get("intent")
        if name not in ALLOWED_INTENTS:
            return fallback, "Gemini classification had no valid intent; used rule-based routing."
        raw_years = data.get("years")
        years = min(30, max(1, int(raw_years))) if str(raw_years).isdigit() else fallback.years
        return Intent(name, years, "AI"), None
    except Exception as exc:
        return fallback, f"Gemini routing unavailable ({type(exc).__name__}); used rule-based routing."


def explain_result(
    question: str,
    result: AnalysisResult,
    *,
    api_key: str | None = None,
    model: str | None = None,
) -> str | None:
    """Add interpretation; numeric FRED-derived answer is always shown separately."""
    if not (api_key or os.environ.get("GEMINI_API_KEY")):
        return None
    try:
        response = _api_client(api_key).models.generate_content(
            model=model or os.environ.get("GEMINI_MODEL", GEMINI_DEFAULT_MODEL),
            contents=(
                f"Question: {question}\nVerified analytics: {result.answer}\n"
                f"Methodological notes: {result.notes}"
            ),
            config={
                "system_instruction": (
                    "You are a cautious U.S. economic data explainer. "
                    "Only use the factual, computed answer supplied below. "
                    "Give 2-3 short sentences interpreting meaning or limitations. "
                    "Do not supply new figures, dates, causal explanations, forecasts, "
                    "policy advice, or claims not demonstrated by the result. "
                    "Do not confuse nominal with real GDP, index level with inflation, "
                    "or statistical correlation with causality."
                ),
                "max_output_tokens": 240,
                "temperature": 0.2,
            },
        )
        return (response.text or "").strip() or None
    except Exception:
        return None

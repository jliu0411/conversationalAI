import pytest

from economic_ai.assistant import Intent, rule_based_intent, route_question


@pytest.mark.parametrize(("text", "expected", "years"), [
    ("What is the latest reported U.S. GDP?", "gdp_latest", 5),
    ("How has U.S. GDP changed over the past 10 years?", "gdp_history", 10),
    ("What is the current Core CPI inflation rate?", "cpi_latest", 5),
    ("What happened to GDP in the past seven years?", "gdp_history", 7),
    ("How has Core CPI inflation changed over the past five years?", "cpi_trend", 5),
    ("What is the relationship between GDP growth and Core CPI inflation?", "relationship", 10),
    ("Generate a visualization comparing GDP growth and Core CPI inflation over time.", "comparison_chart", 10),
    ("Summarize the key economic trends observed in both datasets.", "summary", 10),
])
def test_required_questions(text, expected, years):
    route = rule_based_intent(text)
    assert route.name == expected
    assert route.years == years


def test_followup_retains_topic_and_uses_requested_years():
    previous = Intent("cpi_latest", 5, "Rules")
    route = rule_based_intent("What about the last 3 years?", previous)
    assert route.name == "cpi_trend"
    assert route.years == 3


def test_offline_mode_is_usable(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    route, error = route_question("Latest GDP please")
    assert route.name == "gdp_latest"
    assert error is None


def test_clamps_years():
    assert rule_based_intent("GDP over the past 99 years").years == 30


def test_gemini_routes_with_structured_json(monkeypatch):
    """Verify Gemini's SDK call and response schema without an actual API key."""
    from types import SimpleNamespace
    import economic_ai.assistant as assistant

    calls = []

    def generate_content(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(text='{"intent":"gdp_history","years":8}')

    monkeypatch.setattr(
        assistant, "_api_client", lambda api_key=None: SimpleNamespace(
            models=SimpleNamespace(generate_content=generate_content)
        ),
    )
    result, warning = assistant.route_question("GDP trend?", api_key="fake-key")
    assert result == Intent("gdp_history", 8, "AI")
    assert warning is None
    assert calls[0]["model"] == assistant.GEMINI_DEFAULT_MODEL
    assert calls[0]["config"]["response_mime_type"] == "application/json"
    assert "GDP trend?" in calls[0]["contents"]


def test_gemini_error_falls_back_to_rules(monkeypatch):
    import economic_ai.assistant as assistant

    def unavailable(_api_key=None):
        raise ConnectionError("Simulated Gemini offline")

    monkeypatch.setattr(assistant, "_api_client", unavailable)
    result, notice = assistant.route_question("Latest GDP?", api_key="fake-key")
    assert result.name == "gdp_latest"
    assert result.method == "Rules"
    assert "used rule-based routing" in notice


def test_gemini_invalid_intent_falls_back_to_rules(monkeypatch):
    from types import SimpleNamespace
    import economic_ai.assistant as assistant

    client = SimpleNamespace(models=SimpleNamespace(
        generate_content=lambda **_: SimpleNamespace(text='{"intent":"forecast","years":10}')
    ))
    monkeypatch.setattr(assistant, "_api_client", lambda _=None: client)
    result, notice = assistant.route_question("Latest GDP?", api_key="fake-key")
    assert result.name == "gdp_latest"
    assert result.method == "Rules"
    assert "no valid intent" in notice


def test_gemini_interpretation_only_uses_verified_result(monkeypatch):
    from types import SimpleNamespace
    import economic_ai.assistant as assistant

    seen = {}

    def generate_content(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(text="This is nominal GDP, not inflation-adjusted output.  ")

    monkeypatch.setattr(assistant, "_api_client", lambda _=None: SimpleNamespace(
        models=SimpleNamespace(generate_content=generate_content)
    ))
    result = SimpleNamespace(answer="GDP is $32T (2026 Q2)", notes="Nominal GDP SAAR")
    narrative = assistant.explain_result("What is GDP?", result, api_key="fake-key")
    assert narrative == "This is nominal GDP, not inflation-adjusted output."
    assert "GDP is $32T" in seen["contents"]
    assert "Nominal GDP SAAR" in seen["contents"]
    assert "Do not supply new figures" in seen["config"]["system_instruction"]


def test_gemini_explicit_sdk_client_uses_key(monkeypatch):
    """Client creation must target google.genai, not OpenAI or legacy SDK."""
    import sys
    from types import ModuleType, SimpleNamespace
    import economic_ai.assistant as assistant

    sdk = ModuleType("google.genai")
    sdk.Client = lambda **kwargs: SimpleNamespace(received=kwargs)
    google = ModuleType("google")
    google.genai = sdk
    monkeypatch.setitem(sys.modules, "google", google)
    monkeypatch.setitem(sys.modules, "google.genai", sdk)
    assert assistant._api_client("mock-gemini-key").received == {"api_key": "mock-gemini-key"}


def test_no_gemini_key_skips_ai_explanation(monkeypatch):
    from types import SimpleNamespace
    import economic_ai.assistant as assistant

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert assistant.explain_result(
        "GDP?", SimpleNamespace(answer="example", notes="example")
    ) is None

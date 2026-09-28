from openai import APIConnectionError

from app.retrieval import keywords
from app.retrieval.keywords import extract_fts_keywords
from app.retrieval.types import SearchFilters

NVDA = SearchFilters(ticker="NVDA")
QUESTION = "How did NVIDIA describe demand drivers, customer concentration, and supply constraints for its Data Center business?"


def test_short_query_skips_the_model(monkeypatch):
    monkeypatch.setattr(keywords, "_ask_model", lambda *_: (_ for _ in ()).throw(AssertionError("model called")))
    assert extract_fts_keywords("  iPhone net sales ") == "iPhone net sales"


def test_names_from_query_come_first_and_budget_is_five_words(monkeypatch):
    monkeypatch.setattr(keywords, "_ask_model", lambda *_: ["supply constraints", "hyperscalers", "demand"])
    words = extract_fts_keywords(QUESTION, filters=NVDA).split()

    assert words[:4] == ["customer", "concentration", "Data", "Center"]
    assert len(words) == 5


def test_company_name_is_dropped_under_a_ticker_filter(monkeypatch):
    monkeypatch.setattr(keywords, "_ask_model", lambda *_: ["NVIDIA", "export controls", "China"])
    result = extract_fts_keywords("What did NVIDIA say about export controls affecting China sales?", filters=NVDA)
    assert "NVIDIA" not in result.split()
    assert "export" in result and "China" in result


def test_model_failure_falls_back_to_rule_based_terms(monkeypatch):
    def fail(*_):
        raise APIConnectionError(request=None)

    monkeypatch.setattr(keywords, "_ask_model", fail)
    result = extract_fts_keywords(QUESTION, filters=NVDA)
    assert result.split()[:4] == ["customer", "concentration", "Data", "Center"]
    assert "How" not in result and "NVIDIA" not in result

from app.assistant.router import RouteDecision, route


def _decision(
    scope="in_corpus", scope_confidence=1.0, advice=0.0, complexity="complex", complexity_confidence=1.0
) -> RouteDecision:
    return RouteDecision(
        scope=scope,
        scope_confidence=scope_confidence,
        advice_probability=advice,
        complexity=complexity,
        complexity_confidence=complexity_confidence,
        input_tokens=0,
        cost_usd=0,
        seconds=0,
    )


def test_confident_advice_is_refused_even_about_corpus_companies():
    assert route(_decision(advice=0.95)) == "refuse_advice"


def test_confident_out_of_scope_short_circuits():
    assert route(_decision(scope="other_company", scope_confidence=0.9)) == "out_of_corpus"


def test_unsure_scope_or_advice_falls_back_to_the_agent():
    assert route(_decision(scope="other_period", scope_confidence=0.65)) == "agent_large"
    assert route(_decision(advice=0.7)) == "agent_large"


def test_only_a_confidently_simple_question_gets_the_small_model():
    assert route(_decision(complexity="simple", complexity_confidence=0.9)) == "agent_small"
    assert route(_decision(complexity="simple", complexity_confidence=0.75)) == "agent_large"

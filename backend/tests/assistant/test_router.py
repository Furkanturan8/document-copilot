from app.assistant.router import RouteDecision, route

Q = "What was Apple's revenue in 2024?"


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
    assert route(_decision(advice=0.95), Q) == "refuse_advice"


def test_confident_out_of_scope_short_circuits():
    assert route(_decision(scope="other_company", scope_confidence=0.9), "What was Tesla's revenue?") == "out_of_corpus"


def test_unsure_scope_or_advice_falls_back_to_the_agent():
    assert route(_decision(scope="other_period", scope_confidence=0.65), Q) == "agent_large"
    assert route(_decision(advice=0.7), Q) == "agent_large"


def test_only_a_confidently_simple_question_gets_the_small_model():
    assert route(_decision(complexity="simple", complexity_confidence=0.9), Q) == "agent_small"
    assert route(_decision(complexity="simple", complexity_confidence=0.75), Q) == "agent_large"


def test_other_company_verdict_does_not_block_a_question_naming_a_corpus_company():
    other = _decision(scope="other_company", scope_confidence=0.99)

    assert route(other, "Compare Apple and Samsung smartphone revenue in 2024.") == "agent_large"
    assert route(other, "How does Amazon's AWS compare with Oracle's cloud?") == "agent_large"
    assert route(other, "How did GOOGL's cloud compare with IBM's?") == "agent_large"
    assert route(other, "What was Tesla's revenue in 2024?") == "out_of_corpus"


def test_the_company_exception_is_only_for_other_company_verdicts():
    assert route(_decision(scope="other_period", scope_confidence=0.95), "Apple's revenue in 2015?") == "out_of_corpus"
    assert route(_decision(advice=0.95), "Should I buy Apple?") == "refuse_advice"


def test_company_names_match_as_whole_words_only():
    other = _decision(scope="other_company", scope_confidence=0.99)

    assert route(other, "What was Snapple's revenue?") == "out_of_corpus"

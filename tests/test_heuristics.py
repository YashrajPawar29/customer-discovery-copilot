from discovery.heuristics import (LABEL_COMPLIMENT, LABEL_EVIDENCE, LABEL_OPINION,
                                  analyze_interview, classify_statement, review_questions,
                                  themes)


def test_past_behaviour_is_evidence():
    assert classify_statement("Last week I spent 3 hours on this.") == LABEL_EVIDENCE


def test_prediction_is_opinion():
    assert classify_statement("I'd probably use it.") == LABEL_OPINION


def test_compliment_beats_everything():
    assert classify_statement("Great idea, I'd use it every day.") == LABEL_COMPLIMENT


def test_flags_leading_and_hypothetical_questions():
    flags, strong = review_questions([
        "Wouldn't you love an app for this?",
        "Would you pay $5 a month?",
        "Tell me about the last time this happened.",
    ])
    assert [f.issue for f in flags] == ["Leading question", "Hypothetical future"]
    assert strong == ["Tell me about the last time this happened."]


def test_parses_transcript_and_finds_pain():
    a = analyze_interview("t", "Interviewer: Walk me through it.\n"
                               "Customer: It was so frustrating. I gave up after 2 hours.")
    assert len(a.turns) == 2
    assert a.pains
    assert a.strong_questions == ["Walk me through it."]


def test_themes_need_two_interviews():
    a = analyze_interview("a", "Customer: The listings are frustrating.")
    b = analyze_interview("b", "Customer: Old listings waste my time, so frustrating.")
    words = [w for w, _, _ in themes([a, b])]
    assert "listings" in words

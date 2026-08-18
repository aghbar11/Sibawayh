"""Tests for the evidence table and the hint ladder.

The claim under test is that the reasoning shown to a student comes from what the
rule observed, and not from anywhere else. So the tests that matter are the ones
about coverage — every evidence key the eval set produces has words — and the
ones about the order things are revealed in.
"""

from __future__ import annotations

import json
from pathlib import Path

from sibawayh.hints import LOOK_AT_POSITION, NO_REASON, ladder
from sibawayh.renderers.faithful import leaks
from sibawayh.renderers.reasons import NAMED_REASONS, reason_for, reasons_in
from sibawayh.renderers.template import line_for
from sibawayh.schema import Case, Features, Number, Pos, Sentence, Token

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL = json.loads((REPO_ROOT / "data" / "eval" / "sentences.json").read_text(encoding="utf-8"))
GOLD = {record["id"]: Sentence.model_validate(record) for record in EVAL["sentences"]}
EVERY_TOKEN = [token for sentence in GOLD.values() for token in sentence.tokens]

RESTATEMENTS = {
    "case=nom",
    "case=acc",
    "case=gen",
    "pos=noun",
    "pos=adj",
    "pos=verb",
    "pos=prep",
    "voice=passive",
}
"""Keys that repeat what the answer already says. They have no entry on purpose."""


# --- the table ----------------------------------------------------------------------


def test_every_teaching_key_in_the_eval_set_has_words() -> None:
    """A key with no entry cannot become a hint, so a rule that starts emitting
    one would silently teach less. This is what notices."""
    keys = {key for token in EVERY_TOKEN for key in token.evidence}
    assert {key for key in keys if reason_for(key) is None} == RESTATEMENTS


def test_a_restatement_has_no_reason() -> None:
    """`case=nom` repeats مرفوع. A hint made of it would give the answer away
    while pretending not to."""
    assert reason_for("case=nom") is None
    assert reason_for("pos=noun") is None


def test_every_gold_token_has_at_least_one_reason() -> None:
    """If one did not, its ladder would have nothing on the middle rung."""
    assert all(reasons_in(token.evidence) for token in EVERY_TOKEN)


def test_a_key_built_at_runtime_is_matched_by_shape() -> None:
    """`governed_by=jussive_particle` is assembled from a variable, so there is
    no fixed string to look up."""
    jussive = reason_for("governed_by=jussive_particle")
    assert jussive is not None
    assert "جزم" in jussive.because


def test_the_specific_pattern_wins_over_the_bare_one() -> None:
    """`governs_mood=jussive` is about what a particle does to a verb;
    `mood=jussive` is about the verb. Same word, opposite direction."""
    assert reason_for("governs_mood=jussive") is not None
    assert reason_for("mood=jussive_from_governor") is not None


def test_an_unknown_key_has_no_reason() -> None:
    """Inventing one is exactly what this design exists to prevent."""
    assert reason_for("something_no_rule_emits") is None


def test_the_same_reason_is_not_said_twice() -> None:
    """Two keys often mean one thing to a student, and repeating it reads as
    padding."""
    twice = ["head_lemma_in_kana_sisters", "head_lemma_in_kana_sisters"]
    assert len(reasons_in(twice)) == 1


def test_every_reason_carries_an_anchor() -> None:
    """The anchor is what makes an explanation checkable. One missing would let a
    model say anything about that evidence."""
    assert all(
        reason.anchor and reason.hint and reason.because for reason in NAMED_REASONS.values()
    )


def test_an_anchor_appears_in_its_own_reason() -> None:
    """Otherwise the reason we supply would fail the check we apply."""
    for key, reason in NAMED_REASONS.items():
        assert reason.anchor in reason.because, key


# --- the ladder ---------------------------------------------------------------------


def test_the_ladder_is_three_rungs() -> None:
    """A student has to be able to tell how close they are to the answer."""
    for token in EVERY_TOKEN:
        rungs = ladder(token)
        assert rungs is not None
        assert len(rungs.rungs) == 3


def test_the_first_rung_is_a_question_and_gives_nothing_away() -> None:
    token = GOLD["nasikh_inna_01"].tokens[1]
    first = ladder(token).rungs[0]  # type: ignore[union-attr]
    assert first.text == "ما الحرف الذي قبلها، وماذا يفعل بما بعده؟"
    assert "اسم إنّ" not in first.text
    assert not first.reveals


def test_the_second_rung_is_the_reasoning() -> None:
    token = GOLD["idafa_01"].tokens[1]
    second = ladder(token).rungs[1]  # type: ignore[union-attr]
    assert "مضاف" in second.text
    assert not second.reveals


def test_no_rung_before_the_answer_gives_the_answer_away() -> None:
    """The ladder is three rungs only if the first two withhold something. This
    found six reasons that stated the very role they were meant to lead to —
    `لأنها جاءت بعد مضاف، فهي مضاف إليه` is a hint that is also the answer."""
    leaked = [
        (token.form, rung.text)
        for token in EVERY_TOKEN
        if (rungs := ladder(token)) is not None
        for rung in rungs.rungs[:-1]
        if leaks(rung.text, token)
    ]
    assert not leaked


def test_a_particle_is_told_what_it_does_and_not_what_was_done_to_it() -> None:
    """لم *is* the جازم. It was being told that a jussive particle preceded it,
    because one entry answered for both directions."""
    assert reason_for("jussive_particle").because == "لأنه من الحروف التي تجزم الفعل المضارع"
    assert "قبله" in reason_for("governed_by=jussive_particle").because


def test_the_second_rung_holds_nothing_back() -> None:
    """The student has already tried and failed once. Withholding a second reason
    at that point is not teaching."""
    token = GOLD["idafa_01"].tokens[0]
    assert "أول كلمة" in ladder(token).rungs[1].text  # type: ignore[union-attr]
    assert "مضاف" in ladder(token).rungs[1].text  # type: ignore[union-attr]


def test_the_last_rung_is_the_answer_and_says_so() -> None:
    token = GOLD["nasikh_inna_01"].tokens[1]
    rungs = ladder(token)
    assert rungs is not None
    assert rungs.answer == line_for(token)
    assert rungs.rungs[-1].reveals
    assert not any(rung.reveals for rung in rungs.rungs[:-1])


def test_a_word_the_rules_declined_has_no_ladder() -> None:
    """A hint for an analysis we do not have would be a guess dressed as
    teaching."""
    assert ladder(Token(id=1, form="محمد", diac="مُحَمَّد", pos=Pos.NOUN)) is None


def test_a_token_with_only_restatements_is_asked_about_its_position() -> None:
    token = Token(
        id=1,
        form="الكتاب",
        diac="الكِتابُ",
        pos=Pos.NOUN,
        irab_role="مبتدأ",
        evidence=["case=nom", "pos=noun"],
        feats=Features(case=Case.NOM, num=Number.S),
    )
    rungs = ladder(token)
    assert rungs is not None
    assert rungs.rungs[0].text == LOOK_AT_POSITION
    assert rungs.rungs[1].text == NO_REASON


def test_upto_reveals_only_what_was_asked_for() -> None:
    rungs = ladder(GOLD["sifa_01"].tokens[1])
    assert rungs is not None
    assert rungs.upto(0) == ()
    assert len(rungs.upto(1)) == 1
    assert len(rungs.upto(2)) == 2
    assert len(rungs.upto(9)) == 3


def test_the_ladder_needs_no_model() -> None:
    """Offline, free, and identical every time. A model may rephrase a rung, but
    the teaching content is derived rather than generated."""
    first = [ladder(token).rungs for token in EVERY_TOKEN]  # type: ignore[union-attr]
    second = [ladder(token).rungs for token in EVERY_TOKEN]  # type: ignore[union-attr]
    assert first == second

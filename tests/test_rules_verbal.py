"""Verbal sentence rules.

The positives are the four verbal eval sentences, which must come out fully
labelled. The negatives matter more: كان's arguments and a verb serving as خبر
must come back with **no role at all**, because the rules that name them do not
exist yet and a plausible-looking wrong answer is the failure this project
cannot afford.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sibawayh.rules import apply_rules, default_registry
from sibawayh.rules.lexicon import (
    INNA_AND_SISTERS,
    KANA_AND_SISTERS,
    bare,
    is_defective_verb,
    lemma_in,
)
from sibawayh.rules.verbal import (
    PASSIVE_AGENT,
    VERB_IMPERFECT_INDICATIVE,
    VERB_IMPERFECT_JUSSIVE,
    VERB_PERFECT_ACTIVE,
    VERBAL_AGENT,
    VERBAL_OBJECT,
    VERBAL_RULES,
)
from sibawayh.schema import Features, Pos, Sentence, Token

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL = json.loads((REPO_ROOT / "data" / "eval" / "sentences.json").read_text(encoding="utf-8"))[
    "sentences"
]
EVAL_IDS = [s["id"] for s in EVAL]

FULLY_COVERED = {
    "verbal_overt_agent_01",
    "verbal_perfect_01",
    "verbal_passive_01",
}
"""The sentences the verbal rules alone can finish."""

PARTICLE_SENTENCES = {
    "jussive_lam_01": "لم",
    "subjunctive_lan_01": "لن",
}
"""The verb and its arguments are this file's; the جازم/ناصب itself is
`particles.py`'s. Both halves are now covered, so the sentence completes."""


def analysed(sentence_id: str) -> tuple[list[Token], list[Token]]:
    """Gold tokens, and the same tokens re-derived with roles stripped."""
    raw = next(s for s in EVAL if s["id"] == sentence_id)
    gold = Sentence.model_validate(raw).tokens
    blank = [t.model_copy(update={"irab_role": None, "rule_id": None}) for t in gold]
    return gold, apply_rules(blank)


def verb(form: str = "كتب", **feats: object) -> Token:
    return Token(id=1, form=form, pos=Pos.VERB, head=0, feats=Features(**feats))


# --- nothing is ever wrong ----------------------------------------------------------


@pytest.mark.parametrize("raw", EVAL, ids=EVAL_IDS)
def test_no_token_gets_a_wrong_role(raw: dict) -> None:
    """Across all thirteen sentences: abstaining is fine, contradicting gold is not."""
    gold = Sentence.model_validate(raw).tokens
    result = apply_rules([t.model_copy(update={"irab_role": None}) for t in gold])
    for produced, expected in zip(result, gold, strict=True):
        if produced.irab_role is not None:
            assert produced.irab_role == expected.irab_role, f"{produced.form} ({produced.rule_id})"


@pytest.mark.parametrize("sentence_id", sorted(FULLY_COVERED))
def test_verbal_sentences_are_fully_labelled(sentence_id: str) -> None:
    gold, result = analysed(sentence_id)
    assert [t.irab_role for t in result] == [t.irab_role for t in gold]
    assert all(token.rule_id is not None for token in result)


@pytest.mark.parametrize(("sentence_id", "particle"), sorted(PARTICLE_SENTENCES.items()))
def test_particle_sentences_split_between_two_files(sentence_id: str, particle: str) -> None:
    """The verb and its arguments come from here; the particle from particles.py."""
    gold, result = analysed(sentence_id)
    assert [t.irab_role for t in result] == [t.irab_role for t in gold]
    the_particle = next(t for t in result if t.form == particle)
    assert the_particle.rule_id in {"JUSSIVE_PARTICLE", "SUBJUNCTIVE_PARTICLE"}
    assert all(t.rule_id.startswith(("VERB_", "VERBAL_")) for t in result if t.form != particle)


# --- the verb's own form ------------------------------------------------------------


@pytest.mark.parametrize(
    ("sentence_id", "role", "rule_id"),
    [
        ("verbal_overt_agent_01", "فعل مضارع مرفوع", "VERB_IMPERFECT_INDICATIVE"),
        ("verbal_perfect_01", "فعل ماضٍ", "VERB_PERFECT_ACTIVE"),
        ("verbal_passive_01", "فعل ماضٍ مبني للمجهول", "VERB_PERFECT_PASSIVE"),
        ("jussive_lam_01", "فعل مضارع مجزوم", "VERB_IMPERFECT_JUSSIVE"),
        ("subjunctive_lan_01", "فعل مضارع منصوب", "VERB_IMPERFECT_SUBJUNCTIVE"),
    ],
)
def test_each_verb_form_has_its_own_rule(sentence_id: str, role: str, rule_id: str) -> None:
    """One rule per form, so a wrong answer names the exact rule that produced it."""
    _, result = analysed(sentence_id)
    the_verb = next(t for t in result if t.pos is Pos.VERB)
    assert the_verb.irab_role == role
    assert the_verb.rule_id == rule_id


def test_a_verb_under_a_particle_still_heads_its_clause() -> None:
    """لم يقرأ: the particle governs the verb, but the verb is still the verb of
    the sentence, not a predicate."""
    _, result = analysed("jussive_lam_01")
    assert result[1].rule_id == "VERB_IMPERFECT_JUSSIVE"


def test_a_verb_serving_as_khabar_is_left_to_nominal_py() -> None:
    """محمد يقرأ الكتاب: gold calls the verb خبر — جملة فعلية, not فعل مضارع مرفوع.
    The verb-form rules must decline so the nominal rule can answer."""
    _, result = analysed("nominal_verbal_predicate_01")
    the_verb = next(t for t in result if t.pos is Pos.VERB)
    assert the_verb.rule_id == "PREDICATE_VERBAL"
    assert VERB_IMPERFECT_INDICATIVE(the_verb, result[0], result) is None


def test_a_passive_imperfect_abstains() -> None:
    """No gold example, so no rule. Inventing the string would be a guess."""
    passive = verb("يُكتب", mood="indicative", voice="passive")
    assert apply_rules([passive])[0].irab_role is None


# --- arguments ----------------------------------------------------------------------


def test_nominative_under_an_active_verb_is_the_agent() -> None:
    _, result = analysed("verbal_overt_agent_01")
    assert (result[1].irab_role, result[1].rule_id) == ("فاعل", "VERBAL_AGENT")


def test_accusative_under_a_verb_is_the_object() -> None:
    _, result = analysed("verbal_overt_agent_01")
    assert (result[2].irab_role, result[2].rule_id) == ("مفعول به", "VERBAL_OBJECT")


def test_voice_discriminates_agent_from_deputy() -> None:
    """The same nominative under the same arc: only the head's voice differs."""
    _, result = analysed("verbal_passive_01")
    assert (result[1].irab_role, result[1].rule_id) == ("نائب فاعل", "PASSIVE_AGENT")

    active_head = verb("كتب", aspect="perfect", voice="active")
    noun = Token(id=2, form="المقالة", pos=Pos.NOUN, head=1, feats=Features(case="nom"))
    assert VERBAL_AGENT(noun, active_head, [active_head, noun]) is not None
    assert PASSIVE_AGENT(noun, active_head, [active_head, noun]) is None


def test_an_unknown_case_gets_no_role() -> None:
    """Trap 1 in CLAUDE.md: `cas=u` must abstain, not default to nominative."""
    head = verb("كتب", aspect="perfect", voice="active")
    unclear = Token(id=2, form="طالب", pos=Pos.NOUN, head=1, feats=Features(case="unknown"))
    assert VERBAL_AGENT(unclear, head, [head, unclear]) is None
    assert VERBAL_OBJECT(unclear, head, [head, unclear]) is None


def test_a_particle_under_a_verb_is_not_an_argument() -> None:
    head = verb("يقرأ", mood="jussive")
    particle = Token(id=2, form="لم", pos=Pos.PART, head=1, feats=Features(case="nom"))
    assert VERBAL_AGENT(particle, head, [head, particle]) is None


# --- كان وأخواتها are excluded ------------------------------------------------------


def test_kana_is_not_given_a_plain_verb_form() -> None:
    """Gold says فعل ماضٍ ناقص. This file must decline so nawasikh.py can answer."""
    _, result = analysed("nasikh_kana_01")
    assert result[0].form == "كان"
    assert result[0].rule_id == "KANA_VERB"
    assert VERB_PERFECT_ACTIVE(result[0], None, result) is None


def test_kana_arguments_are_not_claimed_as_agent_and_object() -> None:
    """اسم كان and خبر كان belong to nawasikh.py. Labelling them فاعل and
    مفعول به would be a confident wrong answer."""
    _, result = analysed("nasikh_kana_01")
    assert [t.rule_id for t in result[1:]] == ["KANA_SUBJECT", "KANA_PREDICATE"]
    assert VERBAL_AGENT(result[1], result[0], result) is None
    assert VERBAL_OBJECT(result[2], result[0], result) is None


@pytest.mark.parametrize("lemma", ["كان", "صار", "أصبح", "ليس", "ظل", "بات"])
def test_every_sister_of_kana_is_excluded(lemma: str) -> None:
    head = Token(id=1, form=lemma, lemma=lemma, pos=Pos.VERB, head=0, feats=Features())
    noun = Token(id=2, form="اليوم", pos=Pos.NOUN, head=1, feats=Features(case="nom"))
    assert is_defective_verb(head)
    assert VERBAL_AGENT(noun, head, [head, noun]) is None


def test_a_prd_dependent_also_blocks_the_verb_rules() -> None:
    """A second, independent signal: CATiB uses PRD only for النواسخ, so it
    catches a ناسخ whose lemma is not in our list."""
    head = Token(id=1, form="أمسى", pos=Pos.VERB, head=0, feats=Features(aspect="perfect"))
    subject = Token(id=2, form="الجو", pos=Pos.NOUN, head=1, feats=Features(case="nom"))
    predicate = Token(
        id=3, form="باردا", pos=Pos.ADJ, head=1, parser_label="PRD", feats=Features(case="acc")
    )
    sentence = [head, subject, predicate]
    assert VERB_PERFECT_ACTIVE(head, None, sentence) is None
    assert VERBAL_AGENT(subject, head, sentence) is None
    assert VERBAL_OBJECT(predicate, head, sentence) is None


# --- the lexicon --------------------------------------------------------------------


def test_lemma_matching_ignores_diacritics() -> None:
    """CAMeL returns كانَ; the word list is written كان. Both must match."""
    assert bare("كانَ") == "كان"
    assert lemma_in(Token(id=1, form="x", lemma="كانَ"), KANA_AND_SISTERS)
    assert lemma_in(Token(id=1, form="x", lemma="إِنَّ"), INNA_AND_SISTERS)


def test_surface_form_is_a_fallback_when_there_is_no_lemma() -> None:
    """Hand-written test tokens and the eval set's inserted token have no lemma."""
    assert lemma_in(Token(id=1, form="كان"), KANA_AND_SISTERS)


def test_an_ordinary_verb_is_not_defective() -> None:
    assert not is_defective_verb(Token(id=1, form="كتب", lemma="كَتَب"))


# --- registry wiring ----------------------------------------------------------------


def test_every_verbal_rule_is_in_the_default_registry() -> None:
    registry = default_registry()
    for rule in VERBAL_RULES:
        assert rule.id in registry


def test_covert_agent_outranks_the_general_agent_rule() -> None:
    """Both would fire on an inserted pronoun; the specific one must win."""
    ordered = [rule.id for rule in default_registry()]
    assert ordered.index("COVERT_AGENT") < ordered.index("VERBAL_AGENT")


def test_passive_agent_outranks_the_active_one() -> None:
    ordered = [rule.id for rule in default_registry()]
    assert ordered.index("PASSIVE_AGENT") < ordered.index("VERBAL_AGENT")


def test_rule_ids_are_unique() -> None:
    ids = [rule.id for rule in default_registry()]
    assert len(ids) == len(set(ids))


def test_evidence_names_the_governing_verb() -> None:
    """The hint ladder needs the عامل by name."""
    _, result = analysed("verbal_overt_agent_01")
    assert "head_form=يأكل" in result[1].evidence
    assert "head_voice=active" in result[1].evidence


def test_jussive_evidence_records_the_mood() -> None:
    _, result = analysed("jussive_lam_01")
    assert "mood=jussive" in result[1].evidence
    assert VERB_IMPERFECT_JUSSIVE.role == "فعل مضارع مجزوم"

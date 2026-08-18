"""Validator tests.

Two halves. The first pins each check on a token graph built to break it, since
the eval set is by construction the data that passes. The second is the guard
that matters in practice: every eval sentence must survive validation, both as
gold and as the rule engine actually labels it, because a validator that fires
on correct output would silently turn the whole product into a morphology
viewer.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import pytest
from sibawayh.rules import apply_rules, default_registry
from sibawayh.schema import Features, Pos, Sentence, Source, Token
from sibawayh.validate import (
    AGENT_ROLES,
    ROLE_CASE,
    ROLES,
    ValidationResult,
    Violation,
    check_case_agrees_with_role,
    check_one_agent_per_verb,
    check_roles_are_known,
    check_tree,
    enforce,
    strip_syntax,
    validate,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL = json.loads((REPO_ROOT / "data" / "eval" / "sentences.json").read_text(encoding="utf-8"))[
    "sentences"
]
EVAL_IDS = [s["id"] for s in EVAL]


def tokens_of(sentence_id: str) -> list[Token]:
    raw = next(s for s in EVAL if s["id"] == sentence_id)
    return Sentence.model_validate(raw).tokens


def checks(found: Iterable[Violation]) -> list[str]:
    """The check names that fired, in order, for one check's raw output."""
    return [violation.check for violation in found]


# --- the result type ----------------------------------------------------------------


def test_no_violations_is_ok() -> None:
    result = ValidationResult()
    assert result.ok
    assert bool(result) is True
    assert result.checks_failed == ()


def test_any_violation_is_not_ok() -> None:
    result = ValidationResult((Violation("x", "broken"),))
    assert not result.ok
    assert bool(result) is False


def test_checks_failed_deduplicates_and_keeps_order() -> None:
    result = ValidationResult(
        (Violation("b", ""), Violation("a", ""), Violation("b", "")),
    )
    assert result.checks_failed == ("b", "a")


def test_the_empty_sentence_is_valid() -> None:
    """Nothing to contradict. An empty analysis is vacuous, not broken."""
    assert validate([]).ok


# --- the tree -----------------------------------------------------------------------


def test_a_well_formed_tree_passes() -> None:
    tokens = tokens_of("verbal_overt_agent_01")
    assert checks(check_tree(tokens)) == []


def test_two_roots_is_a_violation() -> None:
    tokens = [
        Token(id=1, form="أ", head=0),
        Token(id=2, form="ب", head=0),
    ]
    assert checks(check_tree(tokens)) == ["tree.root_count"]


def test_no_root_is_a_violation() -> None:
    """Every arc points somewhere, but nothing reaches the top."""
    tokens = [
        Token(id=1, form="أ", head=2),
        Token(id=2, form="ب", head=1),
    ]
    assert "tree.root_count" in checks(check_tree(tokens))


def test_a_cycle_is_a_violation() -> None:
    """Rooted, but two tokens off to the side point only at each other."""
    tokens = [
        Token(id=1, form="أ", head=0),
        Token(id=2, form="ب", head=3),
        Token(id=3, form="ج", head=2),
    ]
    assert "tree.cycle" in checks(check_tree(tokens))


def test_a_head_outside_the_sentence_is_a_violation() -> None:
    tokens = [Token(id=1, form="أ", head=0), Token(id=2, form="ب", head=9)]
    assert "tree.dangling_head" in checks(check_tree(tokens))


def test_arcs_are_not_walked_once_they_are_known_not_to_resolve() -> None:
    """A dangling head would make the cycle walk raise instead of report."""
    tokens = [Token(id=1, form="أ", head=0), Token(id=2, form="ب", head=9)]
    assert "tree.cycle" not in checks(check_tree(tokens))


def test_an_unparsed_token_is_a_violation() -> None:
    """`head=None` means the parser has not run. Roles derived without arcs are
    not trustworthy, whatever else holds."""
    tokens = [Token(id=1, form="أ", head=0), Token(id=2, form="ب")]
    assert "tree.unattached" in checks(check_tree(tokens))


def test_the_violation_names_the_tokens_involved() -> None:
    tokens = [Token(id=1, form="أ", head=0), Token(id=2, form="ب", head=0)]
    violation = next(iter(check_tree(tokens)))
    assert violation.token_ids == (1, 2)


# --- the role inventory -------------------------------------------------------------


def test_an_unknown_role_is_a_violation() -> None:
    token = Token(id=1, form="أ", head=0, irab_role="مفعول فيه")
    assert checks(check_roles_are_known([token])) == ["role.unknown"]


def test_no_role_at_all_is_not_a_violation() -> None:
    """Abstention is the system working, not a failure."""
    assert checks(check_roles_are_known([Token(id=1, form="أ", head=0)])) == []


def test_every_rule_emits_a_role_in_the_inventory() -> None:
    """The check that makes the hand-written inventory worth having: a rule
    whose `role` string drifts has to disagree with something."""
    assert {rule.role for rule in default_registry()} <= ROLES


def test_every_gold_role_is_in_the_inventory() -> None:
    gold = {
        token.irab_role
        for raw in EVAL
        for token in Sentence.model_validate(raw).tokens
        if token.irab_role is not None
    }
    assert gold <= ROLES


def test_the_inventory_has_nothing_spare_in_it() -> None:
    """A label nothing produces would only mask the next typo. Tier-2 roles
    arrive with the rules that emit them."""
    produced = {rule.role for rule in default_registry()}
    assert ROLES - produced == set()


def test_the_agent_and_case_tables_use_real_roles() -> None:
    assert AGENT_ROLES <= ROLES
    assert set(ROLE_CASE) <= ROLES


# --- one agent per verb -------------------------------------------------------------


def _verb_with(*dependents: Token) -> list[Token]:
    verb = Token(id=1, form="يقرأ", pos=Pos.VERB, head=0, irab_role="فعل مضارع مرفوع")
    return [verb, *dependents]


def test_two_agents_under_one_verb_is_a_violation() -> None:
    """The shape the covert-pronoun bug took: a ضمير مستتر inserted under a verb
    that already had an overt subject."""
    tokens = _verb_with(
        Token(id=2, form="محمد", pos=Pos.PROPN, head=1, irab_role="فاعل"),
        Token(id=3, form="هو*", pos=Pos.PRON, head=1, inserted=True, irab_role="فاعل — ضمير مستتر"),
    )
    assert checks(check_one_agent_per_verb(tokens)) == ["agent.multiple"]


def test_one_agent_is_fine() -> None:
    tokens = _verb_with(Token(id=2, form="محمد", pos=Pos.PROPN, head=1, irab_role="فاعل"))
    assert checks(check_one_agent_per_verb(tokens)) == []


def test_a_passive_deputy_counts_as_the_agent() -> None:
    """نائب فاعل fills the same slot, so it must not read as a missing agent."""
    tokens = _verb_with(Token(id=2, form="الرسالة", pos=Pos.NOUN, head=1, irab_role="نائب فاعل"))
    assert checks(check_one_agent_per_verb(tokens)) == []


def test_the_subject_of_kana_counts_as_the_agent() -> None:
    """كان is a verb, and its اسم is the same slot under a different name."""
    kana = Token(id=1, form="كان", pos=Pos.VERB, head=0, irab_role="فعل ماضٍ ناقص")
    tokens = [
        kana,
        Token(id=2, form="اليوم", pos=Pos.NOUN, head=1, irab_role="اسم كان"),
        Token(id=3, form="رائعا", pos=Pos.ADJ, head=1, irab_role="خبر كان"),
    ]
    assert checks(check_one_agent_per_verb(tokens)) == []


def test_no_agent_at_all_is_a_violation_when_everything_else_was_labelled() -> None:
    """Nothing abstained, and still nothing is the agent. Arabic has no such verb."""
    tokens = _verb_with(Token(id=2, form="الكتاب", pos=Pos.NOUN, head=1, irab_role="مفعول به"))
    assert checks(check_one_agent_per_verb(tokens)) == ["agent.missing"]


def test_an_abstaining_dependent_excuses_a_missing_agent() -> None:
    """The unlabelled token may well be the agent. Undiacritized input abstains
    constantly, so this is the common case and must not downgrade the sentence."""
    tokens = _verb_with(
        Token(id=2, form="الكتاب", pos=Pos.NOUN, head=1, irab_role="مفعول به"),
        Token(id=3, form="محمد", pos=Pos.PROPN, head=1),
    )
    assert checks(check_one_agent_per_verb(tokens)) == []


def test_a_verb_with_no_dependents_at_all_is_not_a_violation() -> None:
    """Covert insertion has not run, or the sentence is one word. Either way
    there is nothing here that contradicts anything."""
    assert checks(check_one_agent_per_verb(_verb_with())) == []


def test_only_verbs_are_checked() -> None:
    """إنّ takes an اسم, not a فاعل. It is a particle, and out of scope here."""
    inna = Token(id=1, form="إن", pos=Pos.PART, head=0, irab_role="حرف نصب")
    subject = Token(id=2, form="العراقيين", pos=Pos.NOUN, head=1, irab_role="اسم إنّ")
    assert checks(check_one_agent_per_verb([inna, subject])) == []


# --- case agrees with role ----------------------------------------------------------


def test_an_accusative_mubtada_is_a_violation() -> None:
    token = Token(
        id=1, form="الكتاب", pos=Pos.NOUN, head=0, irab_role="مبتدأ", feats=Features(case="acc")
    )
    assert checks(check_case_agrees_with_role([token])) == ["case.disagrees"]


def test_a_nominative_mubtada_is_fine() -> None:
    token = Token(
        id=1, form="الكتاب", pos=Pos.NOUN, head=0, irab_role="مبتدأ", feats=Features(case="nom")
    )
    assert checks(check_case_agrees_with_role([token])) == []


@pytest.mark.parametrize("case", ["unknown", "null", None])
def test_an_unreadable_case_never_contradicts_a_role(case: str | None) -> None:
    """Position standing in for case is deliberate — a bare محمد at the root is
    the مبتدأ whether or not the analyser could read its ending. Only morphology
    that actually spoke can disagree."""
    token = Token(
        id=1, form="محمد", pos=Pos.PROPN, head=0, irab_role="مبتدأ", feats=Features(case=case)
    )
    assert checks(check_case_agrees_with_role([token])) == []


def test_a_sifa_may_carry_any_case() -> None:
    """صفة copies its case from the noun it follows, so the role fixes nothing."""
    for case in ("nom", "acc", "gen"):
        token = Token(
            id=2, form="الجديد", pos=Pos.ADJ, head=1, irab_role="صفة", feats=Features(case=case)
        )
        assert checks(check_case_agrees_with_role([token])) == []


def test_a_verb_role_has_no_case_to_disagree_about() -> None:
    verb = Token(
        id=1, form="كتب", pos=Pos.VERB, head=0, irab_role="فعل ماضٍ", feats=Features(case="null")
    )
    assert checks(check_case_agrees_with_role([verb])) == []


def test_the_nawasikh_pairs_invert_correctly() -> None:
    """اسم إنّ is accusative and خبر إنّ nominative — the opposite of كان. A
    table that had them the wrong way round would fire on correct output."""
    inna_subject = Token(id=1, form="س", head=0, irab_role="اسم إنّ", feats=Features(case="acc"))
    inna_predicate = Token(id=2, form="ص", head=1, irab_role="خبر إنّ", feats=Features(case="nom"))
    kana_subject = Token(id=3, form="ض", head=1, irab_role="اسم كان", feats=Features(case="nom"))
    kana_predicate = Token(id=4, form="ط", head=1, irab_role="خبر كان", feats=Features(case="acc"))
    tokens = [inna_subject, inna_predicate, kana_subject, kana_predicate]
    assert checks(check_case_agrees_with_role(tokens)) == []


# --- the whole thing, over real analyses --------------------------------------------


@pytest.mark.parametrize("raw", EVAL, ids=EVAL_IDS)
def test_gold_passes_validation(raw: dict) -> None:
    """The hand-verified analyses are by definition what a validator must accept.
    Anything firing here is the validator being wrong, not the data."""
    result = validate(Sentence.model_validate(raw).tokens)
    assert result.ok, [v.message for v in result.violations]


@pytest.mark.parametrize("raw", EVAL, ids=EVAL_IDS)
def test_what_the_rules_actually_produce_passes_validation(raw: dict) -> None:
    """The guard that matters. A validator that fires on our own correct output
    would turn the product into a morphology viewer without anyone noticing."""
    gold = Sentence.model_validate(raw).tokens
    produced = apply_rules([t.model_copy(update={"irab_role": None}) for t in gold])
    result = validate(produced)
    assert result.ok, [v.message for v in result.violations]


# --- the downgrade ------------------------------------------------------------------


def test_strip_syntax_removes_the_conclusion() -> None:
    tokens = strip_syntax(tokens_of("nominal_pp_predicate_01"))
    assert all(token.irab_role is None for token in tokens)
    assert all(token.rule_id is None for token in tokens)
    assert all(token.confidence is None for token in tokens)
    assert all("irab_role" not in token.provenance for token in tokens)


def test_strip_syntax_keeps_morphology_heads_and_evidence() -> None:
    before = tokens_of("nominal_pp_predicate_01")
    after = strip_syntax(before)
    assert [t.feats for t in after] == [t.feats for t in before]
    assert [t.head for t in after] == [t.head for t in before]
    assert [t.diac for t in after] == [t.diac for t in before]
    assert [t.evidence for t in after] == [t.evidence for t in before]


def test_strip_syntax_keeps_other_provenance() -> None:
    token = Token(
        id=1,
        form="هو*",
        head=0,
        inserted=True,
        irab_role="مبتدأ",
        provenance={"form": Source.COVERT, "irab_role": Source.RULES},
    )
    stripped = strip_syntax([token])[0]
    assert stripped.provenance == {"form": Source.COVERT}


def test_strip_syntax_does_not_mutate_its_input() -> None:
    tokens = tokens_of("nominal_pp_predicate_01")
    before = [token.model_dump() for token in tokens]
    strip_syntax(tokens)
    assert [token.model_dump() for token in tokens] == before


def test_enforce_keeps_an_analysis_that_holds_together() -> None:
    tokens = tokens_of("nominal_pp_predicate_01")
    assert [t.irab_role for t in enforce(tokens)] == [t.irab_role for t in tokens]


def test_enforce_drops_an_analysis_that_contradicts_itself() -> None:
    """One bad token takes the sentence with it. A مبتدأ and its خبر are derived
    from each other, so there is no principled way to keep the rest."""
    tokens = tokens_of("nominal_pp_predicate_01")
    tokens[0] = tokens[0].model_copy(update={"feats": Features(case="acc", state="def")})
    assert all(token.irab_role is None for token in enforce(tokens))


def test_enforce_does_not_mutate_its_input() -> None:
    tokens = tokens_of("nominal_pp_predicate_01")
    before = [token.model_dump() for token in tokens]
    enforce(tokens)
    assert [token.model_dump() for token in tokens] == before


def test_enforce_of_nothing() -> None:
    assert enforce([]) == []


def test_validate_does_not_mutate_its_input() -> None:
    tokens = tokens_of("nasikh_inna_01")
    before = [token.model_dump() for token in tokens]
    validate(tokens)
    assert [token.model_dump() for token in tokens] == before

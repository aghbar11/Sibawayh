"""Rule engine skeleton tests.

Mostly about the machinery — ordering, first-match-wins, abstention, purity —
because the inventory that will exercise it properly is the next step. The two
starter rules are checked against the eval sentences they apply to.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest
from sibawayh.rules import (
    Finding,
    Registry,
    Rule,
    RuleError,
    apply_rules,
    starter_registry,
)
from sibawayh.rules.starter import COVERT_AGENT, PREP_OBJECT
from sibawayh.schema import Pos, Sentence, Source, Token

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL = json.loads((REPO_ROOT / "data" / "eval" / "sentences.json").read_text(encoding="utf-8"))[
    "sentences"
]


def tokens_of(sentence_id: str) -> list[Token]:
    raw = next(s for s in EVAL if s["id"] == sentence_id)
    return Sentence.model_validate(raw).tokens


def never(token: Token, head: Token | None, tokens: Sequence[Token]):
    return None


def always(token: Token, head: Token | None, tokens: Sequence[Token]):
    return ["matched"]


def rule(rule_id: str, priority: int, when=always, role: str = "دور") -> Rule:
    return Rule(id=rule_id, role=role, priority=priority, when=when)


# --- the contract -------------------------------------------------------------------


def test_a_rule_returns_a_finding_with_its_evidence() -> None:
    found = rule("R", 1)(Token(id=1, form="x"), None, [])
    assert found == Finding(role="دور", rule_id="R", evidence=["matched"])


def test_a_rule_that_does_not_fire_returns_none() -> None:
    assert rule("R", 1, when=never)(Token(id=1, form="x"), None, []) is None


def test_evidence_is_copied_not_shared() -> None:
    """Two tokens matching the same rule must not end up sharing one list."""
    shared = ["matched"]
    fired = Rule(id="R", role="د", priority=1, when=lambda t, h, s: shared)
    first = fired(Token(id=1, form="x"), None, [])
    second = fired(Token(id=2, form="y"), None, [])
    assert first is not None and second is not None
    first.evidence.append("mutated")
    assert second.evidence == ["matched"]
    assert shared == ["matched"]


# --- the registry -------------------------------------------------------------------


def test_rules_are_ordered_by_priority() -> None:
    registry = Registry([rule("C", 30), rule("A", 10), rule("B", 20)])
    assert [r.id for r in registry] == ["A", "B", "C"]


def test_ties_break_on_id_so_ordering_is_deterministic() -> None:
    registry = Registry([rule("Z", 5), rule("A", 5)])
    assert [r.id for r in registry] == ["A", "Z"]


def test_first_match_wins() -> None:
    registry = Registry([rule("SPECIFIC", 10, role="أول"), rule("GENERAL", 20, role="ثانٍ")])
    found = registry.first_match(Token(id=1, form="x"), None, [])
    assert found is not None
    assert found.rule_id == "SPECIFIC"


def test_a_later_rule_fires_when_earlier_ones_decline() -> None:
    registry = Registry([rule("SKIPPED", 10, when=never), rule("FIRES", 20)])
    found = registry.first_match(Token(id=1, form="x"), None, [])
    assert found is not None
    assert found.rule_id == "FIRES"


def test_no_rule_matching_is_abstention_not_an_error() -> None:
    assert Registry([rule("R", 1, when=never)]).first_match(Token(id=1, form="x"), None, []) is None


def test_an_empty_registry_abstains() -> None:
    assert Registry().first_match(Token(id=1, form="x"), None, []) is None


def test_adding_later_still_sorts() -> None:
    registry = Registry([rule("LATE", 90)])
    registry.add(rule("EARLY", 1))
    assert [r.id for r in registry] == ["EARLY", "LATE"]


def test_duplicate_ids_are_refused() -> None:
    """A duplicated id would make `rule_id` on a token ambiguous, which defeats
    the point of recording it."""
    with pytest.raises(RuleError, match="duplicate rule id"):
        Registry([rule("R", 1), rule("R", 2)])


def test_membership_and_length() -> None:
    registry = starter_registry()
    assert len(registry) == 2
    assert "COVERT_AGENT" in registry
    assert "NOT_A_RULE" not in registry


# --- the stage ----------------------------------------------------------------------


def test_stage_writes_role_rule_id_and_provenance() -> None:
    tokens = tokens_of("nominal_pp_predicate_01")
    result = apply_rules(tokens)
    genitive = result[2]
    assert genitive.form == "القفص"
    assert genitive.irab_role == "مجرور"
    assert genitive.rule_id == "PREP_OBJECT"
    assert genitive.provenance["irab_role"] is Source.RULES


def test_stage_abstains_rather_than_guessing() -> None:
    """المبتدأ has no starter rule. It must come back untouched, not blank-labelled."""
    tokens = tokens_of("nominal_single_predicate_01")
    result = apply_rules([t.model_copy(update={"irab_role": None}) for t in tokens])
    assert all(token.irab_role is None for token in result)
    assert all(token.rule_id is None for token in result)
    assert all("irab_role" not in token.provenance for token in result)


def test_stage_does_not_mutate_its_input() -> None:
    tokens = [
        t.model_copy(update={"irab_role": None}) for t in tokens_of("nominal_pp_predicate_01")
    ]
    before = [token.model_dump() for token in tokens]
    apply_rules(tokens)
    assert [token.model_dump() for token in tokens] == before


def test_stage_appends_evidence_rather_than_replacing_it() -> None:
    """The inserted pronoun keeps covert.py's note about why it exists, and
    gains the rule's note about what it is."""
    token = Token(
        id=2,
        form="هو*",
        pos=Pos.PRON,
        head=1,
        inserted=True,
        evidence=["verb_has_no_overt_agent"],
    )
    verb = Token(id=1, form="يقرأ", pos=Pos.VERB, head=0)
    result = apply_rules([verb, token])
    assert result[1].evidence[0] == "verb_has_no_overt_agent"
    assert "head_pos=verb" in result[1].evidence


def test_stage_accepts_a_custom_registry() -> None:
    registry = Registry([rule("EVERYTHING", 1, role="كل شيء")])
    result = apply_rules([Token(id=1, form="x")], registry)
    assert result[0].irab_role == "كل شيء"


def test_stage_of_nothing() -> None:
    assert apply_rules([]) == []


def test_root_token_gets_a_none_head() -> None:
    """A rule must be able to tell the root apart from an unparsed token."""
    seen: list[Token | None] = []

    def record(token: Token, head: Token | None, tokens: Sequence[Token]):
        seen.append(head)
        return None

    tokens = tokens_of("verbal_overt_agent_01")
    apply_rules(tokens, Registry([rule("R", 1, when=record)]))
    assert seen[0] is None
    assert seen[1] is not None and seen[1].form == "يأكل"


# --- the two starter rules ----------------------------------------------------------


def test_covert_agent_fires_on_the_inserted_pronoun() -> None:
    tokens = tokens_of("nominal_verbal_predicate_01")
    result = apply_rules([t.model_copy(update={"irab_role": None}) for t in tokens])
    pronoun = next(token for token in result if token.inserted)
    assert pronoun.irab_role == "فاعل — ضمير مستتر"
    assert pronoun.rule_id == "COVERT_AGENT"


def test_covert_agent_role_matches_gold() -> None:
    gold = next(token for token in tokens_of("nominal_verbal_predicate_01") if token.inserted)
    assert COVERT_AGENT.role == gold.irab_role


def test_covert_agent_ignores_an_overt_pronoun() -> None:
    """It fires on `inserted`, not on being a pronoun. A typed هو is not its business."""
    overt = Token(id=2, form="هو", pos=Pos.PRON, head=1)
    verb = Token(id=1, form="يقرأ", pos=Pos.VERB, head=0)
    assert COVERT_AGENT(overt, verb, [verb, overt]) is None


def test_prep_object_role_matches_gold() -> None:
    gold = next(t for t in tokens_of("nominal_pp_predicate_01") if t.form == "القفص")
    assert PREP_OBJECT.role == gold.irab_role


def test_prep_object_names_the_governing_preposition() -> None:
    """The hint ladder walks locate -> identify the عامل -> name the role, so the
    عامل has to be in the evidence."""
    result = apply_rules(tokens_of("nominal_pp_predicate_01"))
    assert "head_form=في" in result[2].evidence


def test_prep_object_does_not_fire_under_a_noun() -> None:
    """الطاولة in nominal_adv_predicate_01 hangs off فوق, which is a noun, not a
    preposition — it is مضاف إليه and belongs to a rule that does not exist yet."""
    tokens = tokens_of("nominal_adv_predicate_01")
    result = apply_rules([t.model_copy(update={"irab_role": None}) for t in tokens])
    assert result[2].form == "الطاولة"
    assert result[2].irab_role is None


@pytest.mark.parametrize("raw", EVAL, ids=[s["id"] for s in EVAL])
def test_starter_rules_never_contradict_gold(raw: dict) -> None:
    """Whatever the two rules do fire on must agree with the hand-verified role.

    Most tokens get nothing, which is correct — the inventory is the next step.
    What must never happen is a confident wrong answer.
    """
    gold = Sentence.model_validate(raw).tokens
    result = apply_rules([token.model_copy(update={"irab_role": None}) for token in gold])
    for produced, expected in zip(result, gold, strict=True):
        if produced.irab_role is not None:
            assert produced.irab_role == expected.irab_role, produced.form

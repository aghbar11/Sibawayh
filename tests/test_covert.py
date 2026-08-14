"""Covert pronoun insertion tests.

The gold target is `nominal_verbal_predicate_01`, the one eval sentence carrying
`inserted: true`. The other twelve are just as important as negatives: inserting
a ضمير مستتر where the student can see the subject is the failure that matters.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from sibawayh.covert import (
    could_be_agent,
    insert_covert_pronouns,
    needs_covert_agent,
    pronoun_for,
)
from sibawayh.schema import Case, Features, Pos, Sentence, Source, Token

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL = json.loads((REPO_ROOT / "data" / "eval" / "sentences.json").read_text(encoding="utf-8"))[
    "sentences"
]
EVAL_IDS = [sentence["id"] for sentence in EVAL]

INSERTED_IN = "nominal_verbal_predicate_01"


def without_inserted(raw: dict[str, Any]) -> list[Token]:
    """The gold sentence as it reaches this stage — before we add anything."""
    tokens = Sentence.model_validate(raw).tokens
    kept = [token for token in tokens if not token.inserted]
    renumbered = {0: 0} | {token.id: i for i, token in enumerate(kept, start=1)}
    return [
        token.model_copy(update={"id": renumbered[token.id], "head": renumbered[token.head]})
        for token in kept
    ]


# --- against the eval set -----------------------------------------------------------


@pytest.mark.parametrize("raw", EVAL, ids=EVAL_IDS)
def test_reproduces_the_gold_tree(raw: dict[str, Any]) -> None:
    """Ids, heads and forms all match gold after insertion."""
    gold = Sentence.model_validate(raw).tokens
    result = insert_covert_pronouns(without_inserted(raw))

    assert [token.id for token in result] == [token.id for token in gold]
    assert [token.head for token in result] == [token.head for token in gold]
    assert [token.form for token in result] == [token.form for token in gold]
    assert [token.inserted for token in result] == [token.inserted for token in gold]


@pytest.mark.parametrize("raw", EVAL, ids=EVAL_IDS)
def test_only_one_eval_sentence_gains_a_pronoun(raw: dict[str, Any]) -> None:
    """The twelve negatives. A verb with a visible فاعل must be left alone."""
    result = insert_covert_pronouns(without_inserted(raw))
    added = [token for token in result if token.inserted]
    assert len(added) == (1 if raw["id"] == INSERTED_IN else 0)


def test_the_inserted_token_matches_gold_in_full() -> None:
    raw = next(s for s in EVAL if s["id"] == INSERTED_IN)
    gold = next(t for t in Sentence.model_validate(raw).tokens if t.inserted)
    got = next(t for t in insert_covert_pronouns(without_inserted(raw)) if t.inserted)

    assert got.form == gold.form == "هو*"
    assert got.pos is Pos.PRON
    assert got.head == gold.head
    assert got.feats.person == gold.feats.person
    assert got.feats.gen == gold.feats.gen
    assert got.feats.num == gold.feats.num
    assert got.feats.case is Case.NOM
    assert got.evidence == gold.evidence


def test_features_come_from_the_verb() -> None:
    raw = next(s for s in EVAL if s["id"] == INSERTED_IN)
    result = insert_covert_pronouns(without_inserted(raw))
    pronoun = next(t for t in result if t.inserted)
    verb = result[pronoun.head - 1]
    assert (pronoun.feats.person, pronoun.feats.gen, pronoun.feats.num) == (
        verb.feats.person,
        verb.feats.gen,
        verb.feats.num,
    )


def test_verb_only_features_are_not_copied() -> None:
    """A pronoun has no voice, mood or aspect. Copying them would be nonsense
    the renderer would then have to describe."""
    raw = next(s for s in EVAL if s["id"] == INSERTED_IN)
    pronoun = next(t for t in insert_covert_pronouns(without_inserted(raw)) if t.inserted)
    assert pronoun.feats.voice is None
    assert pronoun.feats.mood is None
    assert pronoun.feats.aspect is None


def test_role_is_left_to_the_rule_engine() -> None:
    """Gold names it فاعل — ضمير مستتر. That naming is not this stage's job."""
    raw = next(s for s in EVAL if s["id"] == INSERTED_IN)
    pronoun = next(t for t in insert_covert_pronouns(without_inserted(raw)) if t.inserted)
    assert pronoun.irab_role is None
    assert pronoun.rule_id is None


def test_provenance_marks_the_whole_token_as_ours() -> None:
    raw = next(s for s in EVAL if s["id"] == INSERTED_IN)
    pronoun = next(t for t in insert_covert_pronouns(without_inserted(raw)) if t.inserted)
    assert pronoun.provenance == {
        "form": Source.COVERT,
        "feats": Source.COVERT,
        "head": Source.COVERT,
    }


@pytest.mark.parametrize("raw", EVAL, ids=EVAL_IDS)
def test_output_is_a_valid_sentence(raw: dict[str, Any]) -> None:
    """Sequential ids and resolvable heads — the schema's invariants survive
    renumbering."""
    result = insert_covert_pronouns(without_inserted(raw))
    Sentence(sentence=raw["sentence"], tokens=result)


# --- purity and renumbering ---------------------------------------------------------


def test_does_not_mutate_its_input() -> None:
    raw = next(s for s in EVAL if s["id"] == INSERTED_IN)
    tokens = without_inserted(raw)
    before = [token.model_dump() for token in tokens]
    insert_covert_pronouns(tokens)
    assert [token.model_dump() for token in tokens] == before


def test_insertion_shifts_later_ids_and_heads() -> None:
    """محمد يقرأ الكتاب: الكتاب moves from 3 to 4 and keeps pointing at the verb."""
    raw = next(s for s in EVAL if s["id"] == INSERTED_IN)
    before = without_inserted(raw)
    assert [(t.id, t.head) for t in before] == [(1, 0), (2, 1), (3, 2)]
    after = insert_covert_pronouns(before)
    assert [(t.id, t.head) for t in after] == [(1, 0), (2, 1), (3, 2), (4, 2)]


def test_root_head_is_never_shifted() -> None:
    tokens = [
        Token(id=1, form="يقرأ", pos=Pos.VERB, head=0, feats=Features(person=3, gen="m", num="s")),
        Token(id=2, form="الكتاب", pos=Pos.NOUN, head=1, feats=Features(case="acc")),
    ]
    result = insert_covert_pronouns(tokens)
    assert result[0].head == 0
    assert [t.id for t in result] == [1, 2, 3]


def test_two_agentless_verbs_both_get_one() -> None:
    """Renumbering has to survive more than one insertion."""
    tokens = [
        Token(id=1, form="يقرأ", pos=Pos.VERB, head=0, feats=Features(person=3, gen="m", num="s")),
        Token(id=2, form="الكتاب", pos=Pos.NOUN, head=1, feats=Features(case="acc")),
        Token(id=3, form="يكتب", pos=Pos.VERB, head=1, feats=Features(person=3, gen="f", num="s")),
        Token(id=4, form="الدرس", pos=Pos.NOUN, head=3, feats=Features(case="acc")),
    ]
    result = insert_covert_pronouns(tokens)
    assert [t.form for t in result] == ["يقرأ", "هو*", "الكتاب", "يكتب", "هي*", "الدرس"]
    assert [t.id for t in result] == [1, 2, 3, 4, 5, 6]
    assert [t.head for t in result] == [0, 1, 1, 1, 4, 4]


def test_empty_input() -> None:
    assert insert_covert_pronouns([]) == []


def test_running_twice_changes_nothing() -> None:
    """Idempotent: the pronoun it added last time is itself a candidate agent."""
    raw = next(s for s in EVAL if s["id"] == INSERTED_IN)
    once = insert_covert_pronouns(without_inserted(raw))
    assert insert_covert_pronouns(once) == once


# --- the decision ------------------------------------------------------------------


def test_a_nominative_dependent_blocks_insertion() -> None:
    verb = Token(id=1, form="كتب", pos=Pos.VERB, head=0)
    agent = Token(id=2, form="الطالب", pos=Pos.NOUN, head=1, feats=Features(case="nom"))
    assert not needs_covert_agent(verb, [verb, agent])


def test_an_sbj_label_blocks_insertion_even_with_the_wrong_case() -> None:
    """CAMeL reads الرجل in verbal_overt_agent_01 as accusative. The parser's
    SBJ is what stops that from producing a spurious pronoun."""
    verb = Token(id=1, form="يأكل", pos=Pos.VERB, head=0)
    agent = Token(
        id=2, form="الرجل", pos=Pos.NOUN, head=1, parser_label="SBJ", feats=Features(case="acc")
    )
    assert could_be_agent(agent)
    assert not needs_covert_agent(verb, [verb, agent])


def test_an_unknown_case_blocks_insertion() -> None:
    """The abstaining direction: an unreadable case might be the agent."""
    verb = Token(id=1, form="كتب", pos=Pos.VERB, head=0)
    maybe = Token(id=2, form="طالب", pos=Pos.NOUN, head=1, feats=Features(case="unknown"))
    assert not needs_covert_agent(verb, [verb, maybe])


def test_an_accusative_dependent_does_not_block() -> None:
    verb = Token(id=1, form="يقرأ", pos=Pos.VERB, head=0)
    obj = Token(id=2, form="الكتاب", pos=Pos.NOUN, head=1, feats=Features(case="acc"))
    assert needs_covert_agent(verb, [verb, obj])


def test_a_particle_dependent_does_not_block() -> None:
    """لم is not a candidate agent, whatever its case field says. Under Sibawayh
    convention the particle heads the verb, so this is the reverse arc — but the
    guard matters wherever a non-nominal hangs off a verb."""
    particle = Token(id=1, form="لم", pos=Pos.PART, head=2)
    assert not could_be_agent(particle)
    verb = Token(id=2, form="يقرأ", pos=Pos.VERB, head=0)
    assert needs_covert_agent(verb, [particle, verb])


def test_passive_needs_no_special_case() -> None:
    """نائب فاعل is nominative, so it registers through the same test."""
    verb = Token(id=1, form="كتبت", pos=Pos.VERB, head=0, feats=Features(voice="passive"))
    deputy = Token(id=2, form="المقالة", pos=Pos.NOUN, head=1, feats=Features(case="nom"))
    assert not needs_covert_agent(verb, [verb, deputy])


def test_only_verbs_are_considered() -> None:
    noun = Token(id=1, form="الشمس", pos=Pos.NOUN, head=0)
    assert not needs_covert_agent(noun, [noun])


@pytest.mark.parametrize(
    ("person", "gen", "num", "expected"),
    [
        (3, "m", "s", "هو"),
        (3, "f", "s", "هي"),
        (3, "m", "p", "هم"),
        (3, "f", "p", "هن"),
        (1, "m", "s", "أنا"),
        (1, "m", "p", "نحن"),
        (2, "m", "s", "أنت"),
        (3, "m", "d", "هما"),
    ],
)
def test_pronoun_agrees_with_the_verb(person: int, gen: str, num: str, expected: str) -> None:
    verb = Token(id=1, form="x", pos=Pos.VERB, feats=Features(person=person, gen=gen, num=num))
    assert pronoun_for(verb) == expected


def test_incomplete_features_fall_back_to_the_unmarked_form() -> None:
    verb = Token(id=1, form="x", pos=Pos.VERB, feats=Features(person=3))
    assert pronoun_for(verb) == "هو"


def test_inserted_forms_are_marked() -> None:
    """A student must never mistake an inserted token for one they typed."""
    raw = next(s for s in EVAL if s["id"] == INSERTED_IN)
    pronoun = next(t for t in insert_covert_pronouns(without_inserted(raw)) if t.inserted)
    assert pronoun.form.endswith("*")

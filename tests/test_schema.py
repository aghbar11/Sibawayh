"""Schema tests, driven by the hand-verified eval set — never a live model call."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from sibawayh.schema import (
    ROOT_HEAD,
    Analysis,
    Case,
    Features,
    Pos,
    Sentence,
    Source,
    State,
    Token,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL_PATH = REPO_ROOT / "data" / "eval" / "sentences.json"


def _load_eval() -> list[dict[str, Any]]:
    # The eval set is the spec; a missing file is a broken checkout, not a reason to skip.
    return json.loads(EVAL_PATH.read_text(encoding="utf-8"))["sentences"]


EVAL_SENTENCES = _load_eval()
EVAL_IDS = [s["id"] for s in EVAL_SENTENCES]


def _assert_preserved(original: dict[str, Any], restored: dict[str, Any], path: str) -> None:
    """Every key of `original` appears in `restored` with an equal value.

    Nested dicts are compared key by key: a dumped `feats` also carries the
    features the gold file left unset, and those extra `None`s are not a loss.
    """
    for key, value in original.items():
        got = restored[key]
        if isinstance(value, dict):
            _assert_preserved(value, got, f"{path}.{key}")
        elif key == "person" and isinstance(value, int):
            # `person` is a string enum for us; the gold file writes a bare int.
            assert got == str(value), f"{path}.{key}"
        else:
            assert got == value, f"{path}.{key}"


# --- the eval set loads, and survives a JSON round trip --------------------------


@pytest.mark.parametrize("raw", EVAL_SENTENCES, ids=EVAL_IDS)
def test_eval_sentence_validates(raw: dict[str, Any]) -> None:
    sentence = Sentence.model_validate(raw)
    assert sentence.tokens
    assert sentence.sentence == raw["sentence"]


@pytest.mark.parametrize("raw", EVAL_SENTENCES, ids=EVAL_IDS)
def test_json_round_trip_is_stable(raw: dict[str, Any]) -> None:
    sentence = Sentence.model_validate(raw)
    assert Sentence.model_validate_json(sentence.model_dump_json()) == sentence
    assert Sentence.model_validate(sentence.model_dump(mode="json")) == sentence


@pytest.mark.parametrize("raw", EVAL_SENTENCES, ids=EVAL_IDS)
def test_no_field_is_dropped_or_altered(raw: dict[str, Any]) -> None:
    """Every key present in the gold file survives with an equal value."""
    dumped = Sentence.model_validate(raw).model_dump(mode="json")
    for key, value in raw.items():
        if key == "tokens":
            continue
        assert dumped[key] == value, key
    for original, restored in zip(raw["tokens"], dumped["tokens"], strict=True):
        _assert_preserved(original, restored, f"{raw['id']}.{original['id']}")


def test_dump_is_plain_json_types() -> None:
    """StrEnum values serialize as bare strings, not `Case.NOM`."""
    dumped = Sentence.model_validate(EVAL_SENTENCES[0]).model_dump(mode="json")
    assert dumped["tokens"][1]["feats"]["case"] == "nom"
    assert isinstance(json.dumps(dumped), str)


def test_exactly_one_eval_token_is_inserted() -> None:
    """The covert-pronoun sentence is the only one carrying `inserted: true`."""
    inserted = [
        (s["id"], t.id)
        for s in EVAL_SENTENCES
        for t in Sentence.model_validate(s).tokens
        if t.inserted
    ]
    assert inserted == [("nominal_verbal_predicate_01", 3)]


# --- defaults and absence semantics ----------------------------------------------


def test_minimal_token_defaults() -> None:
    token = Token(id=1, form="الشمس")
    assert token.head is None
    assert token.pos is None
    assert token.evidence == []
    assert token.alternatives == []
    assert token.provenance == {}
    assert token.confidence is None
    assert token.inserted is False
    assert token.feats == Features()


def test_null_and_unknown_are_distinct() -> None:
    """`na` (not applicable) and `u` (undetermined) must not collapse."""
    assert Case.NULL != Case.UNKNOWN
    assert Case.NULL == "null"
    assert Features(case="null").case is not None
    assert Features().case is None
    assert Features(case="null").model_dump(mode="json")["case"] == "null"


def test_person_accepts_int_and_str() -> None:
    assert Features(person=3).person == Features(person="3").person == "3"


def test_features_keep_unmodeled_gold_annotations() -> None:
    feats = Features.model_validate({"case": "gen", "defective": True})
    assert feats.model_dump(mode="json")["defective"] is True


def test_construct_state_is_reachable() -> None:
    """`stt=c` is the إضافة signal; idafa_01 depends on it surviving."""
    idafa = next(s for s in EVAL_SENTENCES if s["id"] == "idafa_01")
    states = [t.feats.state for t in Sentence.model_validate(idafa).tokens]
    assert State.CONSTRUCT in states


# --- rejections -------------------------------------------------------------------


def test_rejects_self_head() -> None:
    with pytest.raises(ValidationError, match="its own head"):
        Token(id=2, form="كتاب", head=2)


def test_rejects_dangling_head() -> None:
    with pytest.raises(ValidationError, match="outside 0"):
        Sentence(sentence="x y", tokens=[Token(id=1, form="x"), Token(id=2, form="y", head=9)])


def test_rejects_non_sequential_ids() -> None:
    with pytest.raises(ValidationError, match="token ids must be"):
        Sentence(sentence="x y", tokens=[Token(id=1, form="x"), Token(id=3, form="y")])


def test_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        Token.model_validate({"id": 1, "form": "x", "irab_rôle": "فاعل"})


def test_rejects_out_of_range_confidence() -> None:
    with pytest.raises(ValidationError):
        Token(id=1, form="x", confidence=1.4)


def test_rejects_unknown_enum_value() -> None:
    with pytest.raises(ValidationError):
        Features(case="nominative")


def test_provenance_keys_must_name_token_fields() -> None:
    with pytest.raises(ValidationError, match="must name Token fields"):
        Token(id=1, form="x", provenance={"morphology": Source.CAMEL})
    token = Token(id=1, form="x", provenance={"feats": "camel", "irab_role": "rules"})
    assert token.provenance["feats"] is Source.CAMEL


# --- the fields that exist because i'rab is not a single-answer problem -----------


def test_alternatives_hold_runner_up_analyses() -> None:
    token = Token(
        id=1,
        form="كتاب",
        pos=Pos.NOUN,
        feats=Features(case="nom", state="construct"),
        alternatives=[
            Analysis(lemma="كِتاب", pos=Pos.NOUN, feats=Features(case="acc"), score=0.31),
        ],
        confidence=0.62,
    )
    restored = Token.model_validate_json(token.model_dump_json())
    assert restored == token
    assert restored.alternatives[0].feats.case is Case.ACC


def test_parser_label_and_irab_role_stay_separate() -> None:
    token = Token(
        id=3,
        form="العراقيين",
        head=2,
        parser_label="Sb",
        irab_role="اسم إنّ",
        rule_id="NASIKH_ISM",
        evidence=["case=acc", "head_lemma_in_inna_sisters"],
        provenance={"feats": Source.CAMEL, "head": Source.PARSER, "irab_role": Source.RULES},
    )
    dumped = token.model_dump(mode="json")
    assert dumped["parser_label"] == "Sb"
    assert dumped["irab_role"] == "اسم إنّ"
    assert dumped["provenance"] == {"feats": "camel", "head": "parser", "irab_role": "rules"}


def test_evidence_is_a_list_not_prose() -> None:
    """The hint ladder reveals evidence one item at a time."""
    token = Sentence.model_validate(EVAL_SENTENCES[0]).tokens[1]
    assert token.evidence == ["case=nom", "head_pos=verb", "follows_verb"]


# --- navigation helpers ------------------------------------------------------------


def test_head_navigation() -> None:
    sentence = Sentence.model_validate(EVAL_SENTENCES[0])
    verb, agent = sentence.tokens[0], sentence.tokens[1]
    assert verb.head == ROOT_HEAD
    assert sentence.head_of(verb) is None
    assert sentence.head_of(agent) is verb
    assert sentence.by_id(2) is agent

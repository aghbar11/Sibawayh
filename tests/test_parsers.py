"""Parser interface tests. No backend exists yet, so these use stand-ins."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest
from sibawayh.parsers import Formalism, Parse, Parser, ParserError, attach
from sibawayh.schema import ROOT_HEAD, Sentence, Source, Token

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL = json.loads((REPO_ROOT / "data" / "eval" / "sentences.json").read_text(encoding="utf-8"))[
    "sentences"
]


class FixedParser(Parser):
    """Returns whatever it was handed. Stands in for a real backend."""

    name = "fixed"
    formalism = Formalism.CATIB

    def __init__(self, parse: Parse) -> None:
        self.parse_result = parse
        self.calls = 0

    def parse(self, tokens: Sequence[Token]) -> Parse:
        self.calls += 1
        return self.parse_result


class GoldParser(Parser):
    """Reads heads off the tokens it is given — a perfect parser, for testing
    that `attach` puts back exactly what a backend returns."""

    name = "gold"
    formalism = Formalism.SIBAWAYH

    def parse(self, tokens: Sequence[Token]) -> Parse:
        return Parse.of([token.head or ROOT_HEAD for token in tokens])


def tokens_of(sentence_id: str) -> list[Token]:
    raw = next(s for s in EVAL if s["id"] == sentence_id)
    return Sentence.model_validate(raw).tokens


def bare(count: int) -> list[Token]:
    return [Token(id=i, form=f"w{i}") for i in range(1, count + 1)]


# --- Parse ------------------------------------------------------------------------


def test_parse_holds_heads_and_confidence() -> None:
    parse = Parse.of([0, 1, 1], [0.9, 0.8, 0.7])
    assert parse.heads == (0, 1, 1)
    assert parse.confidence_for(1) == 0.9
    assert parse.confidence_for(3) == 0.7


def test_confidence_is_optional() -> None:
    parse = Parse.of([0, 1])
    assert parse.confidence == ()
    assert parse.confidence_for(1) is None


def test_confidence_may_be_missing_per_arc() -> None:
    """A backend that can score some arcs and not others says so with None."""
    assert Parse.of([0, 1], [0.9, None]).confidence_for(2) is None


def test_parse_is_frozen() -> None:
    parse = Parse.of([0, 1])
    with pytest.raises(Exception):  # noqa: B017 - dataclasses raise FrozenInstanceError
        parse.heads = (1, 0)  # type: ignore[misc]


def test_confidence_length_must_match() -> None:
    with pytest.raises(ParserError, match="2 confidences for 3 heads"):
        Parse.of([0, 1, 1], [0.9, 0.8])


@pytest.mark.parametrize("heads", [[0, 5], [3], [-1, 0]])
def test_heads_must_name_a_token(heads: list[int]) -> None:
    with pytest.raises(ParserError, match="outside"):
        Parse.of(heads)


def test_a_token_may_not_head_itself() -> None:
    with pytest.raises(ParserError, match="token 2 is its own head"):
        Parse.of([0, 2, 1])


def test_root_is_allowed_and_is_zero() -> None:
    assert Parse.of([ROOT_HEAD, 1]).heads[0] == 0


def test_empty_parse_is_allowed() -> None:
    """An empty sentence is a degenerate case, not an error."""
    assert Parse.of([]).heads == ()


# --- the interface ----------------------------------------------------------------


def test_parser_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError):
        Parser()  # type: ignore[abstract]


def test_backends_are_shippable_unless_they_say_otherwise() -> None:
    """`eval_only` is opt-in, so forgetting it cannot accidentally gate a free
    backend — and a licensed one must declare itself deliberately."""
    assert FixedParser(Parse.of([])).eval_only is False


def test_eval_only_is_declarable() -> None:
    class Licensed(Parser):
        name = "licensed"
        formalism = Formalism.PADT
        eval_only = True

        def parse(self, tokens: Sequence[Token]) -> Parse:
            return Parse.of([0] * len(tokens))

    assert Licensed().eval_only is True


# --- formalism ---------------------------------------------------------------------


def test_formalism_must_be_declared() -> None:
    """Unlike `eval_only`, this has no safe default — so it is refused outright.

    A missing declaration would surface as wrongly normalized arcs in step 9,
    which reads as a parsing bug. Failing at class definition keeps the error
    where the omission is.
    """
    with pytest.raises(TypeError, match="must declare `formalism`"):

        class Undeclared(Parser):
            name = "undeclared"

            def parse(self, tokens: Sequence[Token]) -> Parse:
                return Parse.of([0] * len(tokens))


def test_formalism_is_readable_without_naming_the_backend() -> None:
    """Step 9 dispatches on this. It says what convention the arcs follow, not
    which backend produced them — the firewall stays intact."""
    assert FixedParser(Parse.of([])).formalism is Formalism.CATIB
    assert GoldParser().formalism is Formalism.SIBAWAYH


def test_formalism_values_cover_the_schemes_that_disagree() -> None:
    """CLAUDE.md's table: i'rab, PADT analytical and UD differ structurally.
    CATiB is the fourth, and what our backend speaks.

    `sibawayh` rather than `irab`: the other three name published specifications,
    this one names ours."""
    assert {f.value for f in Formalism} == {"catib", "ud", "padt", "sibawayh"}


# --- attach -----------------------------------------------------------------------


def test_attach_writes_heads_onto_tokens() -> None:
    tokens = bare(3)
    attached = attach(tokens, FixedParser(Parse.of([0, 1, 1])))
    assert [token.head for token in attached] == [0, 1, 1]


def test_attach_does_not_mutate_its_input() -> None:
    """Stages are pure functions. A backend or a caller holding the old tokens
    must not see them change underneath."""
    tokens = bare(2)
    attach(tokens, FixedParser(Parse.of([0, 1])))
    assert [token.head for token in tokens] == [None, None]


def test_attach_stamps_provenance() -> None:
    attached = attach(bare(2), FixedParser(Parse.of([0, 1])))
    assert all(token.provenance["head"] == Source.PARSER for token in attached)


def test_attach_keeps_existing_provenance() -> None:
    tokens = [Token(id=1, form="كتاب", provenance={"feats": Source.CAMEL})]
    attached = attach(tokens, FixedParser(Parse.of([0])))
    assert attached[0].provenance == {"feats": Source.CAMEL, "head": Source.PARSER}


def test_attach_carries_arc_confidence() -> None:
    attached = attach(bare(2), FixedParser(Parse.of([0, 1], [0.95, 0.4])))
    assert [token.arc_confidence for token in attached] == [0.95, 0.4]


def test_attach_leaves_arc_confidence_unset_when_unscored() -> None:
    attached = attach(bare(2), FixedParser(Parse.of([0, 1])))
    assert all(token.arc_confidence is None for token in attached)


def test_attach_touches_nothing_else() -> None:
    """Attachment only. Roles, features and forms come back untouched, which is
    what keeps parser output and i'rab output separate."""
    before = tokens_of("idafa_01")
    after = attach(before, GoldParser())
    for old, new in zip(before, after, strict=True):
        assert new.model_dump(exclude={"head", "provenance", "arc_confidence"}) == old.model_dump(
            exclude={"head", "provenance", "arc_confidence"}
        )


def test_attach_rejects_a_length_mismatch() -> None:
    with pytest.raises(ParserError, match="2 heads for 3 tokens"):
        attach(bare(3), FixedParser(Parse.of([0, 1])))


def test_attach_calls_the_parser_once() -> None:
    parser = FixedParser(Parse.of([0, 1]))
    attach(bare(2), parser)
    assert parser.calls == 1


@pytest.mark.parametrize("sentence_id", [s["id"] for s in EVAL], ids=[s["id"] for s in EVAL])
def test_round_trip_over_the_eval_set(sentence_id: str) -> None:
    """A parser that returns the gold heads must reproduce the gold tree exactly."""
    tokens = tokens_of(sentence_id)
    attached = attach(tokens, GoldParser())
    assert [token.head for token in attached] == [token.head for token in tokens]

"""Arc normalization tests.

The fixture in `tests/data/catib_trees.json` is the input side and the eval set
is the target, so the central test is one claim: re-rooting a CATiB tree at its
first token yields the gold i'rab tree, for every tier-1 sentence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from sibawayh.arcs import (
    SIBAWAYH_ROOT_POSITION,
    ArcError,
    normalize_arcs,
    normalize_heads,
    reroot,
)
from sibawayh.parsers import Formalism, Parse, Parser, attach
from sibawayh.schema import ROOT_HEAD, Sentence, Source, Token

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL = json.loads((REPO_ROOT / "data" / "eval" / "sentences.json").read_text(encoding="utf-8"))[
    "sentences"
]
CATIB = json.loads(
    (Path(__file__).parent / "data" / "catib_trees.json").read_text(encoding="utf-8")
)
TREES = CATIB["trees"]
TREE_IDS = [tree["id"] for tree in TREES]

EVAL_BY_ID = {sentence["id"]: sentence for sentence in EVAL}


def catib_heads(tree: dict[str, Any]) -> list[int]:
    return [token["head"] for token in tree["tokens"]]


def gold_heads(sentence_id: str) -> list[int]:
    """Gold i'rab heads with inserted tokens dropped and ids closed up.

    Arc normalization runs before covert pronoun insertion, so the tree it has
    to produce is the gold one minus anything we inserted ourselves.
    """
    tokens = Sentence.model_validate(EVAL_BY_ID[sentence_id]).tokens
    inserted = {token.id for token in tokens if token.inserted}
    assert not any(token.head in inserted for token in tokens), (
        f"{sentence_id}: an inserted token is a governor; this helper only drops leaves"
    )
    kept = [token for token in tokens if not token.inserted]
    renumbered = {ROOT_HEAD: ROOT_HEAD} | {token.id: i for i, token in enumerate(kept, start=1)}
    return [renumbered[token.head] for token in kept]


# --- the claim ---------------------------------------------------------------------


@pytest.mark.parametrize("tree", TREES, ids=TREE_IDS)
def test_catib_rerooted_is_the_gold_irab_tree(tree: dict[str, Any]) -> None:
    got = normalize_heads(catib_heads(tree), Formalism.CATIB)
    assert list(got) == gold_heads(tree["id"])


def test_every_eval_sentence_has_a_catib_tree() -> None:
    """The fixture is only evidence if it covers the whole spec."""
    assert [sentence["id"] for sentence in EVAL] == TREE_IDS


@pytest.mark.parametrize("tree", TREES, ids=TREE_IDS)
def test_catib_fixture_is_a_well_formed_tree(tree: dict[str, Any]) -> None:
    """Guards the hand-derived input itself — a typo here would look like a bug
    in the normalizer."""
    tokens = tree["tokens"]
    ids = [token["id"] for token in tokens]
    assert ids == list(range(1, len(tokens) + 1))
    heads = catib_heads(tree)
    assert heads.count(ROOT_HEAD) == 1, "exactly one root"
    assert all(ROOT_HEAD <= head <= len(tokens) for head in heads)
    assert all(head != token_id for token_id, head in zip(ids, heads, strict=True))
    root = heads.index(ROOT_HEAD)
    assert tokens[root]["label"] == "---", "the model labels a governorless token `---`"
    assert tree["sentence"] == EVAL_BY_ID[tree["id"]]["sentence"]


@pytest.mark.parametrize("tree", TREES, ids=TREE_IDS)
def test_catib_forms_match_the_eval_set(tree: dict[str, Any]) -> None:
    """Minus covert pronouns, which no parser emits."""
    gold = Sentence.model_validate(EVAL_BY_ID[tree["id"]]).tokens
    assert [token["form"] for token in tree["tokens"]] == [
        token.form for token in gold if not token.inserted
    ]


def test_the_sentences_that_actually_needed_flipping() -> None:
    """Five trees already match i'rab; eight move. Records which, so a change in
    either direction is visible rather than silent."""
    unchanged = {
        tree["id"]
        for tree in TREES
        if list(normalize_heads(catib_heads(tree), Formalism.CATIB)) == catib_heads(tree)
    }
    assert unchanged == {
        "verbal_overt_agent_01",
        "verbal_perfect_01",
        "verbal_passive_01",
        "nasikh_kana_01",
        "nasikh_inna_01",
    }


# --- reroot ------------------------------------------------------------------------


def test_reroot_at_the_existing_root_is_a_no_op() -> None:
    assert reroot([0, 1, 1]) == (0, 1, 1)


def test_reroot_reverses_only_the_path_to_the_root() -> None:
    """كتاب الطالب جديد: the root is two arcs away, and المضاف إليه must not move."""
    assert reroot([3, 1, 0]) == (0, 1, 1)


def test_reroot_leaves_every_other_governor_alone() -> None:
    """The minimal-edit property: siblings of the path keep their heads."""
    assert reroot([2, 0, 2, 2]) == (0, 1, 2, 2)


def test_reroot_defaults_to_the_first_token() -> None:
    assert SIBAWAYH_ROOT_POSITION == 1
    assert reroot([2, 0]) == reroot([2, 0], 1)


def test_reroot_elsewhere_is_possible() -> None:
    """A chain 1 <- 2 <- 3, re-rooted at its tail: every arc on the path flips."""
    assert reroot([0, 1, 2], at=3) == (2, 3, 0)


def test_reroot_of_nothing() -> None:
    assert reroot([]) == ()


def test_reroot_rejects_a_cycle() -> None:
    with pytest.raises(ArcError, match="cycle"):
        reroot([2, 1, 0])


def test_reroot_rejects_a_position_outside_the_sentence() -> None:
    with pytest.raises(ArcError, match="cannot root at 4"):
        reroot([0, 1, 1], at=4)


# --- dispatch ----------------------------------------------------------------------


def test_sibawayh_arcs_pass_through() -> None:
    """Already in our convention — a gold tree, or a backend that emits one."""
    assert normalize_heads([0, 1, 1], Formalism.SIBAWAYH) == (0, 1, 1)


@pytest.mark.parametrize("formalism", [Formalism.UD, Formalism.PADT])
def test_unimplemented_formalisms_refuse_rather_than_guess(formalism: Formalism) -> None:
    """No backend emits these, so a normalizer for them could not be tested."""
    with pytest.raises(ArcError, match="no .* normalizer"):
        normalize_heads([1, 0], formalism)


def test_every_formalism_is_dispatchable() -> None:
    """A new `Formalism` member must not fall through to a KeyError."""
    for formalism in Formalism:
        try:
            normalize_heads([0], formalism)
        except ArcError as error:
            assert "unknown formalism" not in str(error)


# --- the stage ---------------------------------------------------------------------


def catib_tokens(sentence_id: str) -> list[Token]:
    tree = next(t for t in TREES if t["id"] == sentence_id)
    return [
        Token(id=token["id"], form=token["form"], head=token["head"], parser_label=token["label"])
        for token in tree["tokens"]
    ]


def test_stage_writes_irab_heads() -> None:
    normalized = normalize_arcs(catib_tokens("nominal_pp_predicate_01"), Formalism.CATIB)
    assert [token.head for token in normalized] == [0, 1, 2]


def test_stage_does_not_touch_its_input() -> None:
    tokens = catib_tokens("idafa_01")
    before = [token.model_dump() for token in tokens]
    normalize_arcs(tokens, Formalism.CATIB)
    assert [token.model_dump() for token in tokens] == before


def test_stage_stamps_provenance_only_where_the_head_moved() -> None:
    """So a reader can see which arcs this stage owns, rather than having it
    claim the whole tree."""
    tokens = catib_tokens("jussive_lam_01")
    normalized = normalize_arcs(tokens, Formalism.CATIB)
    moved = [token.id for token in normalized if token.provenance.get("head") is Source.ARCS]
    assert moved == [1, 2]


def test_stage_keeps_everything_that_is_not_an_arc() -> None:
    """No token added or dropped, no role invented, labels untouched."""
    tokens = catib_tokens("sifa_01")
    normalized = normalize_arcs(tokens, Formalism.CATIB)
    assert len(normalized) == len(tokens)
    assert [token.id for token in normalized] == [token.id for token in tokens]
    assert [token.form for token in normalized] == [token.form for token in tokens]
    assert [token.parser_label for token in normalized] == [token.parser_label for token in tokens]
    assert all(token.irab_role is None for token in normalized)
    assert all(not token.inserted for token in normalized)


def test_stage_refuses_unparsed_tokens() -> None:
    with pytest.raises(ArcError, match="run `attach` before normalizing"):
        normalize_arcs([Token(id=1, form="x"), Token(id=2, form="y")], Formalism.CATIB)


def test_stage_of_nothing() -> None:
    assert normalize_arcs([], Formalism.CATIB) == []


def test_stage_output_validates_as_a_sentence() -> None:
    tokens = normalize_arcs(catib_tokens("nasikh_inna_01"), Formalism.CATIB)
    sentence = Sentence(sentence="إن العراقيين قادرون", tokens=tokens)
    assert [token.head for token in sentence.tokens].count(ROOT_HEAD) == 1


# --- with the rest of the pipeline -------------------------------------------------


def test_attach_then_normalize() -> None:
    """The two stages compose: a backend's answer, then i'rab convention."""

    class CatibStandIn(Parser):
        name = "catib-stand-in"
        formalism = Formalism.CATIB

        def parse(self, tokens):
            return Parse.of(catib_heads(next(t for t in TREES if t["id"] == "idafa_01")))

    parser = CatibStandIn()
    bare = [Token(id=i, form=f"w{i}") for i in (1, 2, 3)]
    attached = attach(bare, parser)
    assert [token.head for token in attached] == [3, 1, 0]

    normalized = normalize_arcs(attached, parser.formalism)
    assert [token.head for token in normalized] == gold_heads("idafa_01")
    assert normalized[0].provenance["head"] is Source.ARCS
    assert normalized[1].provenance["head"] is Source.PARSER

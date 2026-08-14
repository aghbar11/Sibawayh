"""CATiB backend tests.

Two tiers, because the model is 440MB and is not in version control:

* unmarked — the wrapper's own logic, with no model present
* `@pytest.mark.parser` — the real model, deselected by default, run with
  `pytest -m parser`. These are the only tests that can catch the model
  changing under us, so they exist despite being slow.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sibawayh.arcs import normalize_arcs
from sibawayh.parsers import Formalism, Parser, ParserError, attach
from sibawayh.parsers.catib import MODEL_DIR_ENV, CatibParser, is_available, model_dir
from sibawayh.schema import ROOT_HEAD, Sentence, Source, Token

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL = json.loads((REPO_ROOT / "data" / "eval" / "sentences.json").read_text(encoding="utf-8"))[
    "sentences"
]
TREES = json.loads(
    (Path(__file__).parent / "data" / "catib_trees.json").read_text(encoding="utf-8")
)["trees"]

needs_model = pytest.mark.skipif(not is_available(), reason="converted CATiB model not present")


def tokens_for(tree: dict) -> list[Token]:
    return [Token(id=t["id"], form=t["form"]) for t in tree["tokens"]]


# --- the contract, without loading anything ----------------------------------------


def test_declares_catib_and_is_shippable() -> None:
    """The formalism drives `arcs.py`; `eval_only` is the licence gate. The
    weights are MIT, so this backend is not gated — see docs/CHANGES.md."""
    assert CatibParser.formalism is Formalism.CATIB
    assert CatibParser.eval_only is False
    assert issubclass(CatibParser, Parser)


def test_model_dir_is_overridable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(MODEL_DIR_ENV, str(tmp_path))
    assert model_dir() == tmp_path
    assert not is_available(tmp_path)


def test_availability_needs_both_files(tmp_path: Path) -> None:
    assert not is_available(tmp_path)
    (tmp_path / "weights.pt").write_bytes(b"")
    assert not is_available(tmp_path)
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    assert is_available(tmp_path)


def test_missing_model_says_how_to_fix_it(tmp_path: Path) -> None:
    with pytest.raises(ParserError, match="convert_catib_checkpoint"):
        CatibParser(tmp_path).parse([Token(id=1, form="كتاب")])


def test_empty_input_needs_no_model(tmp_path: Path) -> None:
    """Degenerate, and cheap enough that it must not drag 440MB in."""
    assert CatibParser(tmp_path).parse([]).heads == ()
    assert CatibParser(tmp_path).labels([]) == []


def test_importing_does_not_import_torch() -> None:
    """Loading is deferred so the morphology-only CLI stays fast. If this fails,
    someone moved an import to module scope."""
    import subprocess
    import sys

    probe = "import sibawayh.parsers.catib, sys; print('torch' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)
    assert out.stdout.strip() == "False", out.stderr


# --- against the real model --------------------------------------------------------


@pytest.mark.parser
@needs_model
@pytest.mark.parametrize("tree", TREES, ids=[t["id"] for t in TREES])
def test_model_reproduces_the_recorded_trees(tree: dict) -> None:
    """The fixture `arcs.py` is tested against is the model's real output. This
    is what stops it drifting back into being an assumption."""
    parse = CatibParser().parse(tokens_for(tree))
    assert list(parse.heads) == [t["head"] for t in tree["tokens"]]


@pytest.mark.parser
@needs_model
@pytest.mark.parametrize("tree", TREES, ids=[t["id"] for t in TREES])
def test_model_reproduces_the_recorded_labels(tree: dict) -> None:
    assert CatibParser().labels(tokens_for(tree)) == [t["label"] for t in tree["tokens"]]


@pytest.mark.parser
@needs_model
def test_arc_confidence_is_produced() -> None:
    """The biaffine score matrix was `reachable` after all — this is what the
    abstention layer will read."""
    tree = next(t for t in TREES if t["id"] == "idafa_01")
    parse = CatibParser().parse(tokens_for(tree))
    assert len(parse.confidence) == len(tree["tokens"])
    assert all(0.0 <= c <= 1.0 for c in parse.confidence)
    assert any(c > 0.5 for c in parse.confidence)


@pytest.mark.parser
@needs_model
@pytest.mark.parametrize("raw", EVAL, ids=[s["id"] for s in EVAL])
def test_end_to_end_reaches_the_gold_tree(raw: dict) -> None:
    """parse -> attach -> normalize_arcs, against the hand-written gold trees.

    The whole point of the backend: the real model plus re-rooting reproduces
    the i'rab tree a human wrote by hand.
    """
    gold = Sentence.model_validate(raw).tokens
    kept = [token for token in gold if not token.inserted]
    renumbered = {ROOT_HEAD: ROOT_HEAD} | {t.id: i for i, t in enumerate(kept, start=1)}
    want = [renumbered[token.head] for token in kept]

    parser = CatibParser()
    bare = [Token(id=i, form=t.form) for i, t in enumerate(kept, start=1)]
    normalized = normalize_arcs(attach(bare, parser), parser.formalism)

    assert [token.head for token in normalized] == want
    assert any(token.provenance.get("head") is Source.PARSER for token in normalized) or all(
        token.provenance.get("head") is Source.ARCS for token in normalized
    )

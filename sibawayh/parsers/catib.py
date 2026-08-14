"""CATiB backend: CAMeL Lab's biaffine dependency parser, run without its pickle.

The published checkpoint (`CAMeL-Lab/camelbert-catib-parser`, MIT) is a 2023
`torch.save` of live Python objects: supar's config, its data transform, and a
`transformers` 4.29 tokenizer frozen mid-flight. Loading it as published needs
four things we are not willing to ship — supar pinned to an unreleased git
commit, `weights_only=False`, a module alias for a `transformers` path that no
longer exists, and a fork-only multiprocessing pool that cannot run on Windows.

So the checkpoint is converted **once** into two version-neutral files, and this
module reads only those:

    weights.pt    plain tensors, loadable with `weights_only=True`
    config.json   the architecture settings and the CATiB label inventory

The tokenizer is not among them. It is rebuilt at load time from the HuggingFace
repo the checkpoint itself names in `args.bert`, verified to line up: the model's
word-embedding matrix has 30000 rows and that tokenizer's vocabulary has 30000
entries. Nothing pickled by anyone else is executed here.

See `scripts/convert_catib_checkpoint.py` for the one-time conversion, and
`docs/CHANGES.md` for why it is done that way.

Licence. The weights are MIT, published by CAMeL Lab, trained on CamelTB (open)
combined with PATB (LDC) — the checkpoint's own `args.train` records
`PATB123-train+CamelTB-ALL-train`. `eval_only` is therefore left `False`: there
is an explicit MIT grant from the rights holder. That is not the same as
unencumbered, and the question is filed in `docs/CHANGES.md` rather than settled
here.
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sibawayh.parsers.base import Formalism, Parse, Parser, ParserError
from sibawayh.schema import Token

if TYPE_CHECKING:  # pragma: no cover - import cost is the whole point of deferring
    import torch

MODEL_DIR_ENV = "SIBAWAYH_CATIB_MODEL"
"""Where the converted artifacts live. Overrides the default cache location."""

DEFAULT_MODEL_DIR = Path.home() / ".cache" / "sibawayh" / "catib"

WEIGHTS_FILE = "weights.pt"
CONFIG_FILE = "config.json"


def model_dir() -> Path:
    """The directory holding the converted artifacts."""
    return Path(os.environ.get(MODEL_DIR_ENV) or DEFAULT_MODEL_DIR)


def is_available(directory: Path | None = None) -> bool:
    """True when the converted artifacts are present.

    They are ~440MB and are not in version control, so callers — the CLI, the
    test suite — check this rather than assuming.
    """
    directory = directory or model_dir()
    return (directory / WEIGHTS_FILE).is_file() and (directory / CONFIG_FILE).is_file()


class CatibParser(Parser):
    """Head indices from CAMeL Lab's CATiB biaffine parser.

    Loading is deferred to the first `parse`, because importing torch and
    reading 440MB of weights is far too expensive to pay for at import time —
    the morphology-only CLI must not become slow because this class exists.

    The tokens handed in are used for their `form` only. Their morphology is
    already settled and this backend has no business revising it; what it
    returns is `Parse`, which holds integers and cannot carry a role.
    """

    name = "camelbert-catib"
    formalism = Formalism.CATIB
    eval_only = False

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or model_dir()

    @cached_property
    def _loaded(self) -> tuple[Any, Any, dict[str, Any]]:
        """The model, the tokenizer and the config. Built once, on first use."""
        weights, config = self.directory / WEIGHTS_FILE, self.directory / CONFIG_FILE
        if not (weights.is_file() and config.is_file()):
            # Checked before the imports: torch and supar together cost seconds,
            # and a missing model is the one failure that should be instant.
            raise ParserError(
                f"no converted CATiB model in {self.directory}. "
                f"Run scripts/convert_catib_checkpoint.py, or set ${MODEL_DIR_ENV}."
            )

        import torch
        from supar.models.dep.biaffine.model import BiaffineDependencyModel
        from transformers import AutoTokenizer

        cfg = json.loads(config.read_text(encoding="utf-8"))
        state = torch.load(weights, map_location="cpu", weights_only=True)

        model = BiaffineDependencyModel(**{k: v for k, v in cfg.items() if not k.startswith("_")})
        model.load_state_dict(state, strict=True)
        model.eval()

        tokenizer = AutoTokenizer.from_pretrained(cfg["bert"])
        embedded = state["encoder.model.embeddings.word_embeddings.weight"].shape[0]
        if embedded != tokenizer.vocab_size:
            raise ParserError(
                f"tokenizer vocabulary ({tokenizer.vocab_size}) does not match the "
                f"model's embedding table ({embedded}); every word would map to the "
                f"wrong row"
            )
        return model, tokenizer, cfg

    def _encode(self, forms: Sequence[str]) -> tuple[torch.Tensor, int]:
        """Surface forms to the `(1, seq, fix_len)` subword tensor supar wants.

        Built here rather than through supar's own `Dataset`, which drives a
        fork-only multiprocessing pool over a local closure and so cannot run on
        Windows at all. Position 0 is the `[CLS]` row the model expects; the
        encoder adds nothing else.
        """
        import torch

        _, tokenizer, cfg = self._loaded
        fix_len = cfg["_fix_len"]
        unk, pad = tokenizer.unk_token_id, tokenizer.pad_token_id

        rows: list[list[int]] = [[tokenizer.cls_token_id]]
        for form in forms:
            pieces = tokenizer.convert_tokens_to_ids(tokenizer.tokenize(form)) or [unk]
            rows.append(pieces[:fix_len])

        width = max(len(row) for row in rows)
        words = torch.full((1, len(rows), width), pad, dtype=torch.long)
        for position, row in enumerate(rows):
            words[0, position, : len(row)] = torch.tensor(row, dtype=torch.long)
        return words, len(rows)

    def parse(self, tokens: Sequence[Token]) -> Parse:
        """Head indices and per-arc confidence for `tokens`."""
        if not tokens:
            return Parse.of([])

        import torch

        model, _, cfg = self._loaded
        words, length = self._encode([token.form for token in tokens])
        mask = torch.zeros((1, length), dtype=torch.bool)
        mask[0, 1:] = True  # position 0 is [CLS], never a token

        with torch.no_grad():
            arc_scores, rel_scores = model(words, [])
            heads, _ = model.decode(
                arc_scores, rel_scores, mask, cfg.get("tree", True), cfg.get("proj", True)
            )
            # P(this head | this dependent), the biaffine matrix the plan hoped
            # would be reachable. It is.
            probabilities = arc_scores.softmax(-1)

        predicted = heads[mask].tolist()
        confidence = [
            round(float(probabilities[0, position, head]), 4)
            for position, head in enumerate(predicted, start=1)
        ]
        if len(predicted) != len(tokens):  # pragma: no cover - shape is fixed above
            raise ParserError(f"model returned {len(predicted)} heads for {len(tokens)} tokens")
        return Parse.of(predicted, confidence)

    def labels(self, tokens: Sequence[Token]) -> list[str]:
        """CATiB relation names, positionally aligned with `tokens`.

        Deliberately not part of `Parser`. `parse` returns integers so that no
        backend can smuggle a role into the pipeline, and this stays a separate
        call for the one caller that wants labels as *evidence* — never as a
        role. A governorless token comes back `---`.
        """
        if not tokens:
            return []

        import torch

        model, _, cfg = self._loaded
        words, length = self._encode([token.form for token in tokens])
        mask = torch.zeros((1, length), dtype=torch.bool)
        mask[0, 1:] = True
        with torch.no_grad():
            arc_scores, rel_scores = model(words, [])
            _, relations = model.decode(
                arc_scores, rel_scores, mask, cfg.get("tree", True), cfg.get("proj", True)
            )
        inventory = cfg["_rels"]
        return [inventory[index] for index in relations[mask].tolist()]

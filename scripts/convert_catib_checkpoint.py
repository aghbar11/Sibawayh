"""One-time conversion of CAMeL Lab's CATiB checkpoint into files we can ship against.

    python scripts/convert_catib_checkpoint.py [--source PATH] [--out DIR]

Downloads `CAMeL-Lab/camelbert-catib-parser` if no source is given, then writes
`weights.pt` and `config.json` next to each other. `sibawayh.parsers.catib` reads
only those two, and reads them with `weights_only=True`.

Why this exists
---------------
The published file is a `torch.save` of live 2023 Python objects. Loading it as
published requires all of:

* supar pinned to an unreleased git commit, where `Config` lived at
  `supar.config` rather than `supar.utils.config`
* `weights_only=False`, because torch >= 2.6 refuses pickled classes by default
  and the safe-globals allowlist cannot bridge a *renamed* module — it keys on
  the class's real `__module__`
* a `sys.modules` alias for `transformers.models.bert.tokenization_bert_fast`,
  removed in transformers 5.x
* a serial replacement for supar's `mp.Pool`, which is fork-only

None of that belongs in a shipping dependency. It is all confined to this script,
which runs once. What comes out the other side is plain tensors and JSON.

**This script executes code from the checkpoint** — that is what
`weights_only=False` means, and it is unavoidable when opening someone else's
pickle. Run it only against the official CAMeL Lab file, and check the size.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

MODEL_URL = (
    "https://huggingface.co/CAMeL-Lab/camelbert-catib-parser/"
    "resolve/main/CAMeLBERT-CATiB-biaffine.model"
)
EXPECTED_BYTES = 445_288_869
"""Size published by the HuggingFace API. A short read leaves a file that opens
as a zip and then fails on a missing central directory, which is a confusing way
to find out the download was truncated — so it is checked."""

DEFAULT_OUT = Path.home() / ".cache" / "sibawayh" / "catib"


def download(destination: Path) -> Path:
    """Fetch the checkpoint, resuming if a previous attempt was cut short."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, 9):
        have = destination.stat().st_size if destination.exists() else 0
        if have == EXPECTED_BYTES:
            return destination
        if have > EXPECTED_BYTES:
            destination.unlink()
            have = 0
        print(f"  attempt {attempt}: {have:,} / {EXPECTED_BYTES:,}", flush=True)
        request = urllib.request.Request(
            MODEL_URL, headers={"User-Agent": "sibawayh", "Range": f"bytes={have}-"}
        )
        try:
            with (
                urllib.request.urlopen(request, timeout=120) as response,  # noqa: S310
                destination.open("ab") as out,
            ):
                while chunk := response.read(1 << 20):
                    out.write(chunk)
        except OSError as error:
            print(f"  interrupted: {type(error).__name__}", flush=True)
    raise SystemExit(f"could not download the checkpoint to {destination}")


def open_checkpoint(source: Path) -> dict[str, Any]:
    """Unpickle the 2023 checkpoint, with every compatibility shim it needs."""
    import torch
    import transformers.models.bert.tokenization_bert as tokenization_bert

    # transformers 5.x removed this module; the class it held still exists.
    sys.modules.setdefault("transformers.models.bert.tokenization_bert_fast", tokenization_bert)
    return torch.load(source, map_location="cpu", weights_only=False)  # noqa: S614


def convert(source: Path, out: Path) -> None:
    import torch

    checkpoint = open_checkpoint(source)
    state = checkpoint["state_dict"]
    args = dict(checkpoint["args"])
    transform = checkpoint["transform"]

    # A constant buffer newer transformers dropped. Not a learned weight, and
    # keeping it would make `load_state_dict(strict=True)` fail.
    state = {k: v for k, v in state.items() if not k.endswith("embeddings.position_ids")}

    form = transform.FORM
    form = form[0] if isinstance(form, list | tuple) else form

    config: dict[str, Any] = {
        key: value
        for key, value in args.items()
        if isinstance(value, str | int | float | bool | type(None))
    }
    config["_rels"] = list(transform.DEPREL.vocab.stoi)
    config["_fix_len"] = form.fix_len
    config["_source"] = MODEL_URL

    out.mkdir(parents=True, exist_ok=True)
    torch.save(state, out / "weights.pt")
    (out / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # Prove the result is readable without any of the shims above.
    reloaded = torch.load(out / "weights.pt", map_location="cpu", weights_only=True)
    print(f"wrote {out / 'weights.pt'} ({len(reloaded)} tensors, weights_only=True verified)")
    print(f"wrote {out / 'config.json'} (n_rels={config['n_rels']}, bert={config['bert']})")
    print(f"CATiB labels: {config['_rels']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="an already-downloaded checkpoint")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="where to write")
    arguments = parser.parse_args()

    source = arguments.source or download(DEFAULT_OUT.parent / "CAMeLBERT-CATiB-biaffine.model")
    size = source.stat().st_size
    if size != EXPECTED_BYTES:
        raise SystemExit(f"{source} is {size:,} bytes, expected {EXPECTED_BYTES:,} — truncated?")
    convert(source, arguments.out)


if __name__ == "__main__":
    main()

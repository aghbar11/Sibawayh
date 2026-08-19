"""Parser backends behind a single interface.

The licensing firewall lives here. A backend trained on LDC2018T08 is
evaluation-only. Nothing outside this package may know which one is running —
but a backend does declare its `formalism`, because arc normalization has to
know which convention the heads arrived in. That is a property of the answer,
not the identity of who gave it.

`Parser` is the component — tokens in, head indices out. `attach` is the pipeline
stage that writes those heads onto tokens, and it is the only place that
bookkeeping happens, so backends cannot drift in how they do it.

    tokens = attach(tokens, parser)

No backend exists yet. The CATiB backend lands with the parser backend, `PadtParser` with the
evaluation work, and the env-var gate that reads `Parser.eval_only` comes with
the latter.
"""

from __future__ import annotations

from collections.abc import Sequence

from sibawayh.parsers.base import Formalism, Parse, Parser, ParserError
from sibawayh.schema import Source, Token

__all__ = ["Formalism", "Parse", "Parser", "ParserError", "attach"]


def attach(tokens: Sequence[Token], parser: Parser) -> list[Token]:
    """Run `parser` over `tokens` and return copies carrying its heads.

    Pure: the tokens handed in are not touched. Returns new tokens with `head`
    set and `provenance["head"]` stamped, so a later layer can tell a parsed
    attachment from a gold one or an inserted one.

    Arc confidence is carried over to `arc_confidence` as-is. It is raw evidence
    for the abstention layer, not a verdict, and nothing here interprets it.

    Only `head`, `arc_confidence` and `provenance` change. A backend that tried
    to return roles could not — `Parse` holds integers.
    """
    parse = parser.parse(tokens)
    if len(parse.heads) != len(tokens):
        raise ParserError(
            f"{parser.name} returned {len(parse.heads)} heads for {len(tokens)} tokens"
        )

    attached = []
    for position, (token, head) in enumerate(zip(tokens, parse.heads, strict=True), start=1):
        if head != 0 and head > len(tokens):  # pragma: no cover - Parse checks this
            raise ParserError(f"head {head} does not name a token")
        attached.append(
            token.model_copy(
                update={
                    "head": head,
                    "arc_confidence": parse.confidence_for(position),
                    "provenance": {**token.provenance, "head": Source.PARSER},
                }
            )
        )
    return attached

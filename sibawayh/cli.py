"""Command line entry point: morphology in, a readable table out.

    python -m sibawayh analyze "الشمس مشرقة"

Nothing here decides anything. It runs the stages that exist so far and prints
what they produced, so the analysis can be inspected before there is any parser,
any rule engine or any UI to look at it through.

Rendering is a pure function over a `Sentence`, which keeps it testable without
a model and reusable once later stages fill in heads and roles.

Two things about Arabic in a terminal. Diacritics are zero-width combining marks
that `len()` counts anyway, so column padding is computed from display width
instead. And the terminal reorders right-to-left text on its own — inside a cell
that is what you want, but a line of mixed Arabic and Latin can still come out
visually shuffled. `--json` is the escape hatch when the layout gets in the way.
"""

from __future__ import annotations

import argparse
import unicodedata
from collections.abc import Sequence

from sibawayh import __version__
from sibawayh.arcs import normalize_arcs
from sibawayh.covert import insert_covert_pronouns
from sibawayh.hints import ladder
from sibawayh.renderers import Renderer, describe
from sibawayh.renderers.template import TemplateRenderer
from sibawayh.rules import apply_rules
from sibawayh.schema import Sentence, Token
from sibawayh.validate import enforce

FEATURE_ORDER = ("aspect", "mood", "voice", "case", "state", "person", "gen", "num")
"""Feature display order: verbal categories, then case and state, then agreement."""

HIDDEN_VALUES = frozenset({"null"})
"""`null` means "not applicable here" — true of most features on most tokens, and
noise in a table. `unknown` is never hidden: it is the abstention signal."""

COLUMNS = ("#", "form", "diac", "lemma", "root", "pos", "features", "alt")
"""`form` is the word as typed; `diac` is CAMeL's vowelling of it, and the column
the student should be reading."""


def display_width(text: str) -> int:
    """Character count ignoring combining marks, which occupy no column."""
    return sum(1 for char in text if not unicodedata.combining(char))


def _pad(text: str, width: int) -> str:
    return text + " " * max(0, width - display_width(text))


def format_features(token: Token) -> str:
    """Set features as `key=value`, in a fixed order, skipping the inapplicable."""
    parts = []
    for name in FEATURE_ORDER:
        value = getattr(token.feats, name, None)
        if value is not None and value not in HIDDEN_VALUES:
            parts.append(f"{name}={value}")
    parts.extend(f"{key}={value}" for key, value in (token.feats.model_extra or {}).items())
    return " ".join(parts)


def _row(token: Token) -> tuple[str, ...]:
    return (
        str(token.id),
        token.form,
        token.diac or "",
        token.lemma or "",
        token.root or "",
        token.pos_fine or (token.pos or ""),
        format_features(token),
        str(len(token.alternatives)) if token.alternatives else "",
    )


def format_table(sentence: Sentence) -> str:
    """The token table: one row per token, columns padded to fit."""
    rows = [COLUMNS, *(_row(token) for token in sentence.tokens)]
    widths = [max(display_width(row[i]) for row in rows) for i in range(len(COLUMNS))]
    lines = [
        " ".join(_pad(cell, width) for cell, width in zip(row, widths, strict=True)).rstrip()
        for row in rows
    ]
    lines.insert(1, " ".join("-" * width for width in widths))
    return "\n".join(lines)


def format_alternatives(sentence: Sentence, limit: int) -> str:
    """Runner-up readings, with the scores that make a thin win visible.

    CAMeL scores relative to its own winner, so a runner-up at 0.99 means the top
    analysis barely won. That is the number abstention will read.
    """
    blocks = []
    for token in sentence.tokens:
        if not token.alternatives:
            continue
        lines = [f"{token.id} {token.form}"]
        for alternative in token.alternatives[:limit]:
            score = "     " if alternative.score is None else f"{alternative.score:.3f}"
            lines.append(f"    {score}  {alternative.diac or ''}  {alternative.pos_fine or ''}")
        blocks.append("\n".join(lines))
    return "\n".join(blocks)


def format_sentence(sentence: Sentence, alternatives: int = 0) -> str:
    """Everything the CLI prints for one sentence."""
    parts = [sentence.sentence, "", format_table(sentence)]
    if alternatives:
        rendered = format_alternatives(sentence, alternatives)
        if rendered:
            parts += ["", "alternatives", "", rendered]
    return "\n".join(parts)


UNCERTAIN = "— لم تتضح"
"""Shown where the rules abstained. The student sees that the word was reached
and not analyzed, which is a different thing from the word being skipped."""


def format_irab(sentence: Sentence, renderer: Renderer | None = None) -> str:
    """The إعراب of every token, one line each, word first.

    The renderer returns the analysis alone; putting the word in front of it is
    the caller's job, and this is the caller.
    """
    rendering = describe(sentence.tokens, renderer or TemplateRenderer())
    words = [token.diac or token.form for token in sentence.tokens]
    width = max((display_width(word) for word in words), default=0)
    return "\n".join(
        f"{_pad(word, width)}  {line or UNCERTAIN}"
        for word, line in zip(words, rendering.lines, strict=True)
    )


def format_hints(sentence: Sentence, revealed: int) -> str:
    """The hint ladder for every token, revealed as far as `revealed`.

    The third rung is the answer, so a caller asking for one or two is asking to
    be taught rather than told. Words the rules declined have no ladder and say
    so, which is the same thing the answer view says about them.
    """
    blocks = []
    for token in sentence.tokens:
        rungs = ladder(token)
        word = token.diac or token.form
        if rungs is None:
            blocks.append(f"{word}\n    {UNCERTAIN}")
            continue
        steps = "\n".join(
            f"    {number}. {rung.text}"
            for number, rung in enumerate(rungs.upto(revealed), start=1)
        )
        blocks.append(f"{word}\n{steps}" if steps else word)
    return "\n\n".join(blocks)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sibawayh",
        description="Arabic morphological analysis and إعراب.",
    )
    parser.add_argument("--version", action="version", version=f"sibawayh {__version__}")
    subcommands = parser.add_subparsers(dest="command", required=True)

    analyze = subcommands.add_parser("analyze", help="analyze one sentence")
    analyze.add_argument("text", help="the sentence, in Arabic")
    analyze.add_argument(
        "--top",
        type=int,
        default=None,
        metavar="N",
        help="how many analyses to keep per word (default: the module default)",
    )
    analyze.add_argument(
        "--alternatives",
        "-a",
        type=int,
        nargs="?",
        const=3,
        default=0,
        metavar="N",
        help="also print up to N runner-up readings per token",
    )
    analyze.add_argument(
        "--raw",
        action="store_true",
        help="skip normalization and pass the text to the analyzer as typed",
    )
    analyze.add_argument("--json", action="store_true", help="print the Sentence as JSON")

    irab = subcommands.add_parser("irab", help="the إعراب of one sentence")
    irab.add_argument("text", help="the sentence, in Arabic")
    irab.add_argument(
        "--raw",
        action="store_true",
        help="skip normalization and pass the text to the analyzer as typed",
    )
    irab.add_argument(
        "--llm",
        action="store_true",
        help="rephrase each line as teaching prose with Gemini (needs $GEMINI_API_KEY)",
    )
    irab.add_argument(
        "--hints",
        type=int,
        nargs="?",
        const=1,
        default=0,
        metavar="N",
        help="show the first N hints for each word instead of the answer (1-3)",
    )
    irab.add_argument("--json", action="store_true", help="print the Sentence as JSON")
    return parser


def _analyze(args: argparse.Namespace) -> int:
    if not args.text.strip():
        print("nothing to analyze", flush=True)
        return 2

    from sibawayh.morphology import DEFAULT_TOP, CamelMorphology

    analyzer = CamelMorphology(top=args.top or DEFAULT_TOP)
    sentence = analyzer.analyze(args.text, normalize_input=not args.raw)
    if args.json:
        print(sentence.model_dump_json(indent=2))
    else:
        print(format_sentence(sentence, alternatives=args.alternatives))
    return 0


def _irab(args: argparse.Namespace) -> int:
    if not args.text.strip():
        print("nothing to analyze", flush=True)
        return 2

    from sibawayh.morphology import CamelMorphology
    from sibawayh.parsers import attach
    from sibawayh.parsers.catib import CatibParser

    parser = CatibParser()
    sentence = CamelMorphology().analyze(args.text, normalize_input=not args.raw)
    tokens = enforce(
        apply_rules(
            insert_covert_pronouns(
                normalize_arcs(attach(sentence.tokens, parser), parser.formalism)
            )
        )
    )
    analyzed = sentence.model_copy(update={"tokens": tokens})

    if args.json:
        print(analyzed.model_dump_json(indent=2))
    elif args.hints:
        print(format_hints(analyzed, args.hints))
    else:
        renderer: Renderer = TemplateRenderer()
        if args.llm:
            from sibawayh.renderers.gemini import GeminiRenderer

            renderer = GeminiRenderer()
        print(format_irab(analyzed, renderer))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "analyze":
        return _analyze(args)
    if args.command == "irab":
        return _irab(args)
    raise AssertionError(f"unhandled command {args.command!r}")  # pragma: no cover

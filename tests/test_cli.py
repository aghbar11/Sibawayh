"""CLI tests. Rendering is pure, so these run without loading a model."""

from __future__ import annotations

import json
from itertools import takewhile
from pathlib import Path
from typing import Any

import pytest
from sibawayh.cli import (
    UNCERTAIN,
    build_parser,
    display_width,
    format_alternatives,
    format_features,
    format_irab,
    format_sentence,
    format_table,
    main,
)
from sibawayh.morphology import sentence_from_analyses
from sibawayh.schema import (
    Analysis,
    Case,
    Features,
    Gender,
    Number,
    Pos,
    Sentence,
    State,
    Token,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
RECORDED = json.loads(
    (REPO_ROOT / "tests" / "data" / "camel_analyses.json").read_text(encoding="utf-8")
)["sentences"]


def build(sentence_id: str) -> Sentence:
    record = RECORDED[sentence_id]
    words: list[tuple[str, list[tuple[dict[str, Any], float]]]] = [
        (word["word"], [(a["analysis"], a["score"]) for a in word["analyses"]])
        for word in record["words"]
    ]
    return sentence_from_analyses(record["text"], words, sentence_id=sentence_id)


# --- display width ---------------------------------------------------------------


def test_display_width_ignores_combining_marks() -> None:
    """Diacritics take no column, so `len` overcounts and columns drift."""
    bare = "كتاب"
    marked = "كِتابِ"
    assert len(marked) > len(bare)
    assert display_width(marked) == display_width(bare) == 4


def test_table_columns_line_up() -> None:
    """Every row must be the same display width, diacritics or not."""
    lines = format_table(build("idafa_01")).splitlines()
    widths = {display_width(line.rstrip()) for line in lines}
    assert len(widths) <= len(lines), widths
    assert all(display_width(line) <= max(widths) for line in lines)


# --- features --------------------------------------------------------------------


def test_features_hide_null_but_keep_unknown() -> None:
    """`null` is inapplicable and just noise. `unknown` is the abstention signal
    and has to stay visible."""
    token = Token(
        id=1,
        form="محمد",
        feats=Features(case=Case.UNKNOWN, state=State.INDEF, voice="null"),
    )
    rendered = format_features(token)
    assert "case=unknown" in rendered
    assert "state=indef" in rendered
    assert "voice" not in rendered


def test_features_follow_a_fixed_order() -> None:
    token = Token(
        id=1,
        form="يكتب",
        feats=Features(num="s", case=Case.NOM, aspect="imperfect"),
    )
    assert format_features(token) == "aspect=imperfect case=nom num=s"


def test_features_include_the_clitic_role() -> None:
    """`enc0`'s role rides along in the feature block, where it is visible."""
    pronoun = build("clitic_pronoun").tokens[-1]
    assert "clitic_role=poss" in format_features(pronoun)


# --- table -----------------------------------------------------------------------


def test_table_has_a_header_and_one_row_per_token() -> None:
    sentence = build("jussive_lam_01")
    lines = format_table(sentence).splitlines()
    assert lines[0].split() == ["#", "form", "diac", "lemma", "root", "pos", "features", "alt"]
    assert set(lines[1]) <= {"-", " "}
    assert len(lines) == len(sentence.tokens) + 2


def test_table_shows_every_token_form() -> None:
    sentence = build("attached_preposition")
    table = format_table(sentence)
    for token in sentence.tokens:
        assert token.form in table


def test_table_reports_the_fine_grained_pos() -> None:
    """`part_neg` is what identifies لم/لن/لا; collapsing it to `part` in the
    table would hide the distinction the rules key on."""
    assert "part_neg" in format_table(build("jussive_lam_01"))


# --- alternatives ----------------------------------------------------------------


def test_alternatives_are_limited_and_scored() -> None:
    sentence = build("verbal_passive_01")
    rendered = format_alternatives(sentence, limit=2)
    verb = sentence.tokens[0]
    assert len(verb.alternatives) > 2

    lines = rendered.splitlines()
    assert lines[0] == f"{verb.id} {verb.form}"
    readings = list(takewhile(lambda line: line.startswith("    "), lines[1:]))
    assert len(readings) == 2  # limit honoured, not the four we hold
    assert all("0.9" in reading for reading in readings)


def test_alternatives_omitted_unless_asked() -> None:
    sentence = build("idafa_01")
    assert "alternatives" not in format_sentence(sentence)
    assert "alternatives" in format_sentence(sentence, alternatives=2)


def test_alternatives_block_skips_tokens_without_any() -> None:
    sentence = build("clitic_pronoun")
    pronoun = sentence.tokens[-1]
    assert pronoun.alternatives == []
    rendered = format_alternatives(sentence, limit=3)
    assert not rendered.startswith(f"{pronoun.id} ")


def test_alternative_without_a_score_still_renders() -> None:
    sentence = Sentence(
        sentence="كتاب",
        tokens=[Token(id=1, form="كتاب", alternatives=[Analysis(diac="كُتّاب", pos=Pos.NOUN)])],
    )
    assert "كُتّاب" in format_alternatives(sentence, limit=1)


# --- argument parsing ------------------------------------------------------------


def test_analyze_requires_text() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["analyze"])


def test_a_command_is_required() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_analyze_defaults() -> None:
    args = build_parser().parse_args(["analyze", "الشمس مشرقة"])
    assert args.text == "الشمس مشرقة"
    assert args.alternatives == 0
    assert args.top is None
    assert args.raw is False
    assert args.json is False


def test_alternatives_flag_has_a_bare_form() -> None:
    assert build_parser().parse_args(["analyze", "س", "-a"]).alternatives == 3
    assert build_parser().parse_args(["analyze", "س", "-a", "5"]).alternatives == 5


def test_version_exits_cleanly() -> None:
    with pytest.raises(SystemExit) as exit_info:
        build_parser().parse_args(["--version"])
    assert exit_info.value.code == 0


@pytest.mark.parametrize("text", ["", "   "])
def test_empty_text_is_refused_without_loading_a_model(text: str, capsys) -> None:
    """Exit before importing camel_tools — an empty string is not worth a model load."""
    assert main(["analyze", text]) == 2
    assert "nothing to analyze" in capsys.readouterr().out


# --- the live path, off by default -----------------------------------------------


@pytest.mark.camel
def test_analyze_end_to_end(capsys) -> None:
    assert main(["analyze", "الشمس مشرقة"]) == 0
    out = capsys.readouterr().out
    assert "case=" in out
    assert "noun" in out


@pytest.mark.camel
def test_json_output_round_trips(capsys) -> None:
    assert main(["analyze", "كتاب الطالب جديد", "--json"]) == 0
    sentence = Sentence.model_validate_json(capsys.readouterr().out)
    assert len(sentence.tokens) == 3
    assert sentence.tokens[0].feats.state == State.CONSTRUCT


def test_format_irab_puts_the_word_in_front_of_its_analysis() -> None:
    """The renderer returns the analysis alone; pairing it with the word is the
    caller's job, and the CLI is the caller."""
    sentence = Sentence(
        sentence="الكتاب مفيد",
        tokens=[
            Token(
                id=1,
                form="الكتاب",
                diac="الكِتابُ",
                pos=Pos.NOUN,
                irab_role="مبتدأ",
                feats=Features(case=Case.NOM, num=Number.S, gen=Gender.M),
            ),
            Token(id=2, form="مفيد", diac="مُفيدٌ", pos=Pos.ADJ),
        ],
    )
    lines = format_irab(sentence).splitlines()
    assert lines[0].startswith("الكِتابُ")
    assert "مبتدأ مرفوع" in lines[0]


def test_format_irab_marks_a_token_the_rules_declined() -> None:
    """Not the same as skipping it. The student sees the word was reached."""
    sentence = Sentence(
        sentence="مفيد",
        tokens=[Token(id=1, form="مفيد", diac="مُفيدٌ", pos=Pos.ADJ)],
    )
    assert UNCERTAIN in format_irab(sentence)


def test_the_irab_subcommand_exists() -> None:
    args = build_parser().parse_args(["irab", "الكتاب مفيد"])
    assert args.command == "irab"
    assert args.text == "الكتاب مفيد"


def test_format_hints_stops_before_the_answer() -> None:
    """Asking for one or two rungs is asking to be taught rather than told."""
    from sibawayh.cli import format_hints

    sentence = Sentence(
        sentence="الكتاب مفيد",
        tokens=[
            Token(
                id=1,
                form="الكتاب",
                diac="الكِتابُ",
                pos=Pos.NOUN,
                irab_role="مبتدأ",
                evidence=["sentence_initial"],
                feats=Features(case=Case.NOM, num=Number.S, gen=Gender.M),
            )
        ],
    )
    shown = format_hints(sentence, 1)
    assert "بأي كلمة بدأت الجملة؟" in shown
    assert "مرفوع" not in shown

    assert "مرفوع" in format_hints(sentence, 3)


def test_format_hints_says_when_there_is_nothing_to_teach() -> None:
    from sibawayh.cli import UNCERTAIN, format_hints

    sentence = Sentence(sentence="مفيد", tokens=[Token(id=1, form="مفيد", pos=Pos.ADJ)])
    assert UNCERTAIN in format_hints(sentence, 2)

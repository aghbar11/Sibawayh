"""Normalization tests. Pure strings, no model call, no fixtures beyond the eval set."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sibawayh.normalize import (
    AGGRESSIVE,
    DIACRITICS,
    SAFE,
    NormalizationOptions,
    collapse_whitespace,
    fold_alef_wasla,
    fold_lookalikes,
    normalize,
    strip_diacritics,
    strip_tatweel,
    strip_zero_width,
    unify_alef,
    unify_alef_maksura,
    unify_teh_marbuta,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL_PATH = REPO_ROOT / "data" / "eval" / "sentences.json"

EVAL_SENTENCES = json.loads(EVAL_PATH.read_text(encoding="utf-8"))["sentences"]


# --- the mark table is derived from Unicode, so assert what it must contain ------


@pytest.mark.parametrize(
    "mark",
    [
        "ً",  # ً tanween fath
        "ٌ",  # ٌ tanween damm
        "ٍ",  # ٍ tanween kasr
        "َ",  # َ fatha
        "ُ",  # ُ damma
        "ِ",  # ِ kasra
        "ّ",  # ّ shadda
        "ْ",  # ْ sukun
        "ٰ",  # ٰ superscript alef
        "ۢ",  # ۢ small high meem (Quranic)
    ],
)
def test_diacritic_table_contains(mark: str) -> None:
    assert mark in DIACRITICS


@pytest.mark.parametrize(
    "char",
    [
        "ا",  # ا alef — a letter, not a mark
        "ـ",  # ـ tatweel — spacing, removed separately
        "۝",  # ۝ end of ayah — category Cf, must not be swallowed
        "۞",  # ۞ start of rub el hizb
        " ",
    ],
)
def test_diacritic_table_excludes(char: str) -> None:
    assert char not in DIACRITICS


# --- individual transformations --------------------------------------------------


def test_strip_diacritics_bare_verb() -> None:
    assert strip_diacritics("كَتَبَ الطَّالِبُ") == "كتب الطالب"


def test_strip_diacritics_keeps_letters_with_hamza() -> None:
    """أ is a letter (U+0623), not alef-plus-mark. It must survive."""
    assert strip_diacritics("أَكَلَ") == "أكل"


def test_strip_tatweel() -> None:
    assert strip_tatweel("كتـــاب") == "كتاب"


def test_strip_zero_width() -> None:
    assert strip_zero_width("‏الكتاب‎﻿") == "الكتاب"


def test_fold_alef_wasla() -> None:
    assert fold_alef_wasla("ٱلكتاب") == "الكتاب"


def test_fold_lookalikes() -> None:
    assert fold_lookalikes("کتابی") == "كتابي"


def test_unify_alef() -> None:
    assert unify_alef("آأإ") == "ااا"


def test_unify_alef_maksura() -> None:
    assert unify_alef_maksura("مصطفى") == "مصطفي"


def test_unify_teh_marbuta() -> None:
    assert unify_teh_marbuta("مدرسة") == "مدرسه"


def test_collapse_whitespace() -> None:
    assert collapse_whitespace("  كتب\t\nالطالب  ") == "كتب الطالب"


# --- SAFE preserves every MSA contrast -------------------------------------------


@pytest.mark.parametrize(
    ("text", "why"),
    [
        ("إن", "إنَّ the ناسخ, not أنْ the مصدرية"),
        ("أن", "أنْ the مصدرية"),
        ("آسف", "madda is a distinct letter"),
        ("إلى", "إلى the preposition, not إلي"),
        ("مدرسة", "the feminine marker صفة agreement needs"),
        ("رائع", "hamza on ya seat"),
        ("مسؤول", "hamza on waw seat"),
        ("شيء", "bare hamza"),
    ],
)
def test_safe_preserves_contrast(text: str, why: str) -> None:
    assert normalize(text) == text, why


def test_safe_still_cleans_noise() -> None:
    assert normalize("  إنَّ‏ الطـــالبَ  ") == "إن الطالب"


def test_safe_composes_decomposed_hamza() -> None:
    """NFC runs before mark stripping, so a decomposed hamza is kept, not lost."""
    decomposed = "أكل"  # ا + hamza above + كل
    assert normalize(decomposed) == "أكل"


def test_no_compose_loses_decomposed_hamza() -> None:
    """The inverse, to show the ordering is what saves it."""
    options = NormalizationOptions(compose=False)
    assert normalize("أكل", options) == "اكل"


# --- AGGRESSIVE is the lossy preset ----------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("إن", "ان"),
        ("أن", "ان"),
        ("آسف", "اسف"),
        ("إلى", "الي"),
        ("مصطفى", "مصطفي"),
        ("مدرسة", "مدرسه"),
    ],
)
def test_aggressive_unifies(text: str, expected: str) -> None:
    assert normalize(text, AGGRESSIVE) == expected


def test_aggressive_collapses_inna_and_anna() -> None:
    """The distinction AGGRESSIVE destroys, stated as a test so nobody ships it
    into the analysis path by accident."""
    assert normalize("إن", AGGRESSIVE) == normalize("أن", AGGRESSIVE)
    assert normalize("إن", SAFE) != normalize("أن", SAFE)


# --- options are honoured individually -------------------------------------------


@pytest.mark.parametrize(
    ("field", "text"),
    [
        ("strip_diacritics", "كَتَبَ"),
        ("strip_tatweel", "كتـاب"),
        ("strip_zero_width", "كتاب‏"),
        ("fold_alef_wasla", "ٱلكتاب"),
        ("fold_lookalikes", "کتاب"),
        ("collapse_whitespace", " كتاب "),
    ],
)
def test_disabling_an_option_skips_it(field: str, text: str) -> None:
    off = NormalizationOptions(**{field: False})
    assert normalize(text, off) == text
    assert normalize(text, SAFE) != text


# --- invariants ------------------------------------------------------------------


SAMPLES = [
    "",
    "   ",
    "كَتَبَ الطَّالِبُ المَقالةَ",
    "إنَّ العراقيين قادرون",
    "‏كتـ__ـاب الطالب﻿",
    "ٱلْحَمْدُ لِلَّٰهِ",
    "Hello, world! 123",
    "الكتاب: ما رأيك؟ (نعم!) ١٢٣",
    "کتاب فارسی",
]


@pytest.mark.parametrize("options", [SAFE, AGGRESSIVE], ids=["safe", "aggressive"])
@pytest.mark.parametrize("text", SAMPLES)
def test_idempotent(text: str, options: NormalizationOptions) -> None:
    once = normalize(text, options)
    assert normalize(once, options) == once


@pytest.mark.parametrize("options", [SAFE, AGGRESSIVE], ids=["safe", "aggressive"])
@pytest.mark.parametrize("text", SAMPLES)
def test_never_grows(text: str, options: NormalizationOptions) -> None:
    assert len(normalize(text, options)) <= len(text)


@pytest.mark.parametrize("text", ["", "   ", "‏﻿", "ًَُِّْ"])
def test_degenerate_input_yields_empty(text: str) -> None:
    assert normalize(text) == ""


@pytest.mark.parametrize(
    "text",
    ["Hello, world!", "123 456", "sentence_id_01", "الكتاب: نعم؟ (لا!)"],
)
def test_non_arabic_and_punctuation_untouched(text: str) -> None:
    assert normalize(text, AGGRESSIVE) == text


# --- the eval set is the spec: SAFE must be a no-op on it -------------------------


@pytest.mark.parametrize(
    "sentence",
    [s["sentence"] for s in EVAL_SENTENCES],
    ids=[s["id"] for s in EVAL_SENTENCES],
)
def test_safe_is_noop_on_eval_set(sentence: str) -> None:
    """Gold sentences are already clean MSA. If SAFE changed one, either the gold
    is dirty or SAFE has become lossy."""
    assert normalize(sentence) == sentence


@pytest.mark.parametrize(
    "sentence",
    [s["sentence"] for s in EVAL_SENTENCES],
    ids=[s["id"] for s in EVAL_SENTENCES],
)
def test_normalization_preserves_token_count(sentence: str) -> None:
    """Whitespace handling must not merge or split words."""
    assert len(normalize(sentence).split()) == len(sentence.split())

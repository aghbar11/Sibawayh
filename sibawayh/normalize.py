"""Orthographic normalization of raw input, before anything else touches it.

Pure string functions, standard library only. This is the first pipeline stage:
raw text in, cleaner text out, ready for the CAMeL disambiguator.

Two classes of transformation live here, and the difference matters:

*Lossless* cleanups remove noise the writer did not intend as a distinction —
tatweel, zero-width and bidi control characters, stray diacritics, Quranic
recitation marks, alef wasla, Persian/Urdu letter shapes. Nothing an i'rab rule
could ever key on is lost. These are on by default.

*Lossy* unifications collapse letters that Arabic actually contrasts:

===============  ===================================================
أ إ آ → ا        destroys إنَّ (ناسخ) / أنْ (مصدرية) / إنْ (شرطية)
ى → ي            destroys إلى / إلي, مصطفى / مصطفي
ة → ه            destroys the feminine marker صفة agreement depends on
===============  ===================================================

They are off by default. A student who typed the hamza handed us evidence, and
the analyzer accepts hamzated input; folding it away only to have the
disambiguator guess it back is a net loss. Turn them on for fuzzy *matching* —
comparing a typed sentence against a bank entry, say — not for analysis. `SAFE`
and `AGGRESSIVE` are the two presets for exactly that split.

Not handled here, deliberately: Arabic presentation forms (U+FB50–U+FEFF) are
stripped of their combining marks but not mapped back to their base letters,
and no offset map back to the raw input is produced. Both are gaps to revisit
if real input demands it.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

TATWEEL = "ـ"
"""ـ ARABIC TATWEEL — pure typographic stretching, never meaningful."""

ZERO_WIDTH = (
    "​‌‍"  # zero-width space / non-joiner / joiner
    "‎‏"  # LRM, RLM
    "‪‫‬‭‮"  # bidi embedding and override
    "⁦⁧⁨⁩"  # bidi isolates
    "﻿"  # byte-order mark
)
"""Invisible joiners and bidi controls. Text pasted from the web is full of these."""

ALEF = "ا"  # ا
YEH = "ي"  # ي
HEH = "ه"  # ه
KAF = "ك"  # ك
ALEF_MAKSURA = "ى"  # ى
TEH_MARBUTA = "ة"  # ة
ALEF_WASLA = "ٱ"  # ٱ

HAMZATED_ALEF = "آأإ"
"""آ أ إ — contrastive in MSA, folded only by `unify_alef`."""

WAVY_HAMZA_ALEF = "ٲٳٵ"
"""ٲ ٳ ٵ — extended-Arabic alef shapes, unused in MSA orthography."""

LOOKALIKES = {
    "ی": YEH,  # ی FARSI YEH
    "ک": KAF,  # ک KEHEH
    "ھ": HEH,  # ھ HEH DOACHASHMEE
}
"""Persian/Urdu letter shapes that carry no Arabic contrast."""

_ARABIC_RANGES = (
    (0x0600, 0x06FF),  # Arabic
    (0x0750, 0x077F),  # Arabic Supplement
    (0x08A0, 0x08FF),  # Arabic Extended-A
    (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
    (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
)


def _arabic_combining_marks() -> frozenset[str]:
    """Every nonspacing mark in the Arabic blocks.

    Derived from the Unicode database rather than hard-coded, so harakat,
    tanween, shadda, sukun, superscript alef and the Quranic recitation marks
    are all covered without maintaining a list. Spacing characters that sit in
    the same range but are not marks — U+06DD END OF AYAH, U+06DE START OF RUB
    EL HIZB — are category `Cf`/`So` and correctly excluded.
    """
    return frozenset(
        char
        for start, end in _ARABIC_RANGES
        for codepoint in range(start, end + 1)
        if unicodedata.category(char := chr(codepoint)) == "Mn"
    )


DIACRITICS = _arabic_combining_marks()

_DIACRITIC_TABLE = str.maketrans("", "", "".join(DIACRITICS))
_TATWEEL_TABLE = str.maketrans("", "", TATWEEL)
_ZERO_WIDTH_TABLE = str.maketrans("", "", ZERO_WIDTH)
_ALEF_TABLE = str.maketrans({char: ALEF for char in HAMZATED_ALEF + WAVY_HAMZA_ALEF})
_ALEF_WASLA_TABLE = str.maketrans(ALEF_WASLA, ALEF)
_ALEF_MAKSURA_TABLE = str.maketrans(ALEF_MAKSURA, YEH)
_TEH_MARBUTA_TABLE = str.maketrans(TEH_MARBUTA, HEH)
_LOOKALIKE_TABLE = str.maketrans(LOOKALIKES)

_WHITESPACE = re.compile(r"\s+")


def strip_diacritics(text: str) -> str:
    """Remove harakat, tanween, shadda, sukun and Quranic marks."""
    return text.translate(_DIACRITIC_TABLE)


def strip_tatweel(text: str) -> str:
    """Remove the kashida stretching character."""
    return text.translate(_TATWEEL_TABLE)


def strip_zero_width(text: str) -> str:
    """Remove zero-width joiners, bidi controls and the byte-order mark."""
    return text.translate(_ZERO_WIDTH_TABLE)


def fold_alef_wasla(text: str) -> str:
    """ٱ → ا. Quranic orthography; no MSA contrast."""
    return text.translate(_ALEF_WASLA_TABLE)


def fold_lookalikes(text: str) -> str:
    """Persian/Urdu shapes (ی ک ھ) → their Arabic equivalents."""
    return text.translate(_LOOKALIKE_TABLE)


def unify_alef(text: str) -> str:
    """آ أ إ → ا. **Lossy** — see the module docstring before enabling."""
    return text.translate(_ALEF_TABLE)


def unify_alef_maksura(text: str) -> str:
    """ى → ي. **Lossy.**"""
    return text.translate(_ALEF_MAKSURA_TABLE)


def unify_teh_marbuta(text: str) -> str:
    """ة → ه. **Lossy** — discards the feminine marker."""
    return text.translate(_TEH_MARBUTA_TABLE)


def collapse_whitespace(text: str) -> str:
    """Runs of whitespace become one space; leading and trailing space goes."""
    return _WHITESPACE.sub(" ", text).strip()


@dataclass(frozen=True)
class NormalizationOptions:
    """Which transformations `normalize` applies. Use `SAFE` or `AGGRESSIVE`."""

    compose: bool = True
    """Apply Unicode NFC first, so a decomposed ا + ٔ becomes أ rather than
    losing its hamza to `strip_diacritics`."""

    strip_zero_width: bool = True
    strip_tatweel: bool = True
    strip_diacritics: bool = True
    fold_alef_wasla: bool = True
    fold_lookalikes: bool = True
    collapse_whitespace: bool = True

    unify_alef: bool = False
    unify_alef_maksura: bool = False
    unify_teh_marbuta: bool = False


SAFE = NormalizationOptions()
"""Default. Removes noise only; every MSA letter contrast survives.

This is what feeds the disambiguator.
"""

AGGRESSIVE = NormalizationOptions(
    unify_alef=True,
    unify_alef_maksura=True,
    unify_teh_marbuta=True,
)
"""For fuzzy matching between two strings. Never for analysis."""


def normalize(text: str, options: NormalizationOptions = SAFE) -> str:
    """Normalize raw input for the rest of the pipeline.

    Order is fixed: compose, then strip noise, then fold letters, then tidy
    whitespace. Composing first is what keeps a decomposed hamza; stripping
    before folding keeps the fold tables free of mark-bearing sequences.

    Idempotent under both presets: `normalize(normalize(t)) == normalize(t)`.
    """
    if options.compose:
        text = unicodedata.normalize("NFC", text)
    if options.strip_zero_width:
        text = strip_zero_width(text)
    if options.strip_tatweel:
        text = strip_tatweel(text)
    if options.strip_diacritics:
        text = strip_diacritics(text)
    if options.fold_alef_wasla:
        text = fold_alef_wasla(text)
    if options.fold_lookalikes:
        text = fold_lookalikes(text)
    if options.unify_alef:
        text = unify_alef(text)
    if options.unify_alef_maksura:
        text = unify_alef_maksura(text)
    if options.unify_teh_marbuta:
        text = unify_teh_marbuta(text)
    if options.collapse_whitespace:
        text = collapse_whitespace(text)
    return text

# Foundations

The token model everything else reads and writes, the sentences the whole
project is measured against, the text cleaning that happens before any
analysis, and the command line that made each of them visible.

## The token schema

**Amended during morphology.** `Gender` gained `BOTH` and `UNKNOWN`; `Number` gained `BOTH`.

CAMeL's `db.defines` declares `gen: b f m na u` and `num: b d na p s u`. Without those members
`b` and `u` had nowhere to go, and folding them into `null` would have destroyed the `na` vs `u`
distinction CLAUDE.md calls load-bearing. Additive only — no existing value changed, the eval
set was unaffected.

**Corrected later.** The wording above originally said these were CAMeL's "real inventories",
implying `b` had been encountered. It had not. Scanning **all 74,014 entries** in
`morphology-db-msa-r13` — stem, prefix and suffix tables — finds:

    gen  {'-': 64639, 'm': 4474, 'f': 3582, None: 1280, 'u': 39}
    num  {'-': 65984, 'p': 6617, None: 1280, 's': 91, 'd': 26, 'u': 14, ...}

Zero occurrences of `b` in either. So `Gender.BOTH` and `Number.BOTH` are justified
**defensively** — the schema declares the value legal and `morphology-db-msa-s31` may use it —
not by observation. `UNKNOWN` on both is earned: `u` really does occur.

Two things the scan turned up incidentally. `num` contains one entry valued `'؛'` (an Arabic
semicolon) and one valued `'pf'`; neither is a legal value, and either would raise
`MorphologyError` out of `_lookup` if it ever surfaced — a latent crash rather than a wrong
answer, unhandled. And `-` is not the oddity morphology treats it as: at 64,639 of 74,014 it is the
commonest value in the database by a factor of fourteen. The handling is right; the framing
understates it.

**Amended during the parser interface.** `Token.arc_confidence` added.

the confidence layer combines arc confidence with the morphology margin, so the arc number has to survive
from the parser backend to the confidence layer. It was homeless: `Token.confidence` is the *combined* score the confidence layer
produces, and overloading it would leave the confidence layer unable to tell an input from its own output.
Additive, defaults to `None`.

---

## The evaluation set

The eval set shipped at `docs/eval/sentences.json` while CLAUDE.md, the plan and the README all
named `data/eval/sentences.json`. Canonicalised on `data/eval/`.

`tests/test_schema.py` had a two-path fallback that called `pytest.skip` when neither path
existed; replaced with a single path that raises. A missing spec file is a broken checkout, not
a reason to skip.

---

## Text normalization

**All three letter unifications ship opt-in, not just ة → ه.** They are exposed as the
`AGGRESSIVE` preset. The default `SAFE` preset does the lossless cleanups only: NFC, tatweel,
diacritics, zero-width and bidi controls, ٱ → ا, Persian ی ک ھ.

`SAFE` is what feeds the disambiguator, and folding alef there would collapse إنَّ (ناسخ) /
أنْ (مصدرية) / إنْ (شرطية) — the contrast `nasikh_inna_01` rests on. ى → ي kills إلى / إلي.
ة → ه kills the feminine marker صفة agreement reads. A student who typed the hamza handed us
evidence; discarding it so the disambiguator can guess it back is a net loss. `AGGRESSIVE`
exists for fuzzy *matching* — a typed sentence against a bank entry — never for analysis.

Also added, beyond the original item: Unicode NFC before mark stripping, so a decomposed
ا + U+0654 survives as أ rather than losing its hamza; zero-width and bidi stripping; and the
diacritic set derived from the Unicode database rather than hard-coded.

Known gaps, recorded in the module docstring: presentation forms U+FB50–FEFF are not mapped back
to base letters, and no offset map back to the raw input is produced.

---

## The command line

The package was renamed in the package layout, so the invocation is `python -m sibawayh analyze`, not
`python -m irab analyze`.

Four flags beyond the bare table: `--json` (the `Sentence` as JSON, and the escape hatch when
the terminal's bidi reordering makes the table unreadable), `-a/--alternatives N` (runner-up
readings with their scores — the thin-win evidence steps 14 and 16 will need), `--raw` (skip
normalization), `--top N` (analyses kept per word).

Column padding is computed from display width, not `len`: diacritics are zero-width combining
marks and `len` counts them, which drifts every column after the first.

The table gained a `diac` column once the morphology defect above was fixed and the two columns
stopped showing the same thing.

---

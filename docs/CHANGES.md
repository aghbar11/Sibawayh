# Changes

Where the code departs from `CLAUDE.md` or `docs/PLAN.md`, and why.

Those two files stay as written — the spec and the plan of record. Anything that shipped
differently is recorded here instead of being edited into them, so the original intent and the
departure from it stay separately readable.

**The rule.** Flag every deviation, or ask first. Small and obvious: state it in the summary and
log it here. Changes what the step is: ask before doing it. Nothing gets absorbed silently.

`docs/PLAN.md` is gitignored, so anything here that matters to a reader of the repo needs to
stand on its own without it.

---

## Log

Newest last.

| step | change |
|---|---|
| 3 | eval set moved `docs/eval/` → `data/eval/`; test skip replaced with a raise |
| 4 | all three letter unifications opt-in behind `AGGRESSIVE`, not just ة → ه |
| 4 | added NFC composition, zero-width/bidi stripping, Unicode-derived diacritic set |
| 2 | `Gender.BOTH/UNKNOWN`, `Number.BOTH` added — amended during step 5 |
| 5 | six extra CAMeL POS tags mapped by function, `pos_fine` keeps the original |
| 5 | ال folded back onto the stem despite d3tok splitting it |
| 5 | undocumented `-` and `NOAN` values handled |
| 5 | `enc0` role recorded as `feats.clitic_role` via `Features(extra="allow")` |
| 5 | `tests/data/camel_analyses.json` fixture + `camel` pytest marker, deselected by default |
| 5 | `Token.form` held the diacritized stem; now bare, `diac` carries the vowelling, `None` on backoff |
| 6 | invocation is `python -m sibawayh`, not `python -m irab` — package renamed in step 1 |
| 6 | four flags added: `--json`, `-a/--alternatives`, `--raw`, `--top` |
| 6 | table gained a `diac` column once `form` and `diac` stopped being identical |
| 7 | `parse` returns a self-validating `Parse`, not a bare `list[int]` |
| 7 | parser is a component; `attach` is the stage that applies its result |
| 2 | `Token.arc_confidence` added — step 14's input had nowhere to live |

Two edits were made directly to `CLAUDE.md`, both requested: the `prc0` bullet now records that
`d3tok` splits ال and that folding it back is the rule, and the conventions section now
distinguishes a component from a pipeline stage. They are corrections to the spec rather than
departures from it, which is why they live there and not only here.

---

## Step 2 — token schema

**Amended during step 5.** `Gender` gained `BOTH` and `UNKNOWN`; `Number` gained `BOTH`.

CAMeL's real inventories are `gen: b f m na u` and `num: b d na p s u`. Without those members
`b` and `u` had nowhere to go, and folding them into `null` would have destroyed the `na` vs `u`
distinction CLAUDE.md calls load-bearing. Additive only — no existing value changed, the eval
set was unaffected.

**Amended during step 7.** `Token.arc_confidence` added.

Step 14 combines arc confidence with the morphology margin, so the arc number has to survive
from step 8 to step 14. It was homeless: `Token.confidence` is the *combined* score step 14
produces, and overloading it would leave step 14 unable to tell an input from its own output.
Additive, defaults to `None`.

---

## Step 3 — eval set

The eval set shipped at `docs/eval/sentences.json` while CLAUDE.md, the plan and the README all
named `data/eval/sentences.json`. Canonicalised on `data/eval/`.

`tests/test_schema.py` had a two-path fallback that called `pytest.skip` when neither path
existed; replaced with a single path that raises. A missing spec file is a broken checkout, not
a reason to skip.

---

## Step 4 — text normalization

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

## Step 5 — CAMeL morphology wrapper

Five things were settled against real CAMeL output (`camel-tools` 1.6.0,
`morphology-db-msa-r13`, `disambig-mle-calima-msa-r13`), not against the documentation.

**1. `d3tok` splits ال, and CLAUDE.md says not to.** The two instructions conflict: `d3tok`
emits `ال+` as its own segment, while CLAUDE.md says `Al_det` is a feature and not a token. The
ال surface is folded back onto the stem, so `الكتاب` stays one token carrying `state=def`. That
matches CLAUDE.md's own example, where `form` is `العراقيين`. Every other clitic does become a
token. CLAUDE.md now records this.

**2. Two undocumented CAMeL values.** `-` turns up in feature fields and is not in `db.defines`
at all; `d3tok == "NOAN"` marks an out-of-vocabulary backoff guess. `-` maps to `unknown` — to
`null` for `Aspect` and `Person`, which have no `UNKNOWN` member — and a NOAN analysis falls
back to the surface word with no segmentation. Without both, the pipeline crashes on ordinary
input: `أتقرأ` alone triggers each of them.

**3. Six POS tags CLAUDE.md's collapse table does not cover.** `abbrev`, `digit`, `foreign` and
`latin` map to `noun` — they fill nominal slots, and CAMeL's own CATiB tag for them is `NOM`.
`interj` and `part_voc` map to `part`. The exact tag always survives in `pos_fine`.

**4. `enc0`'s role is recorded as `feats.clitic_role`** (`dobj` / `poss` / `pron`), using the
`extra="allow"` escape hatch on `Features`. It is a hint from morphology, not an i'rab role:
`irab_role` stays empty until the rule engine runs.

**5. Two new test assets.** `tests/data/camel_analyses.json` holds recorded analyzer output for
the 13 eval sentences plus three clitic cases, because "test the CAMeL wrapper" and "never a
live model call" leave no other option. A `camel` pytest marker was added and deselected by
default (`addopts = "-m 'not camel'"`), so bare `pytest` stays offline; `pytest -m camel` checks
the fixture against a live model.

**Defect found later, during step 6.** `Token.form` held the *diacritized* stem, making `form`
and `diac` identical on every token. The model says `form` is the surface word and `diac` the
vowelled one. `form` is now the segment with marks stripped, `diac` is CAMeL's segment as
written, and on a backoff analysis `diac` is `None` rather than echoing the bare surface as
though it had been vowelled.

### What the analyzer actually does to the eval set

Not a deviation — a measurement, recorded because it makes steps 11–14 bigger than they look.

| sentence | what CAMeL returns |
|---|---|
| `nasikh_inna_01` | إن ranks `pos=abbrev` first at 1.0; the `إِنَّ` reading (`verb_pseudo`) is 5th at 0.60 |
| `verbal_passive_01` | active كَتَبَت wins; passive كُتِبَت is 3rd at 0.92 |
| `nominal_single_predicate_01` | الشمس comes back `case=gen` |
| `verbal_overt_agent_01` | الرجل comes back `case=acc` |

MLE disambiguates each word out of context, so case on short sentences is often wrong and rank 1
is not trustworthy. All four are recorded as tests.

---

## Step 6 — morphology-only CLI

The package was renamed in step 1, so the invocation is `python -m sibawayh analyze`, not
`python -m irab analyze`.

Four flags beyond the bare table: `--json` (the `Sentence` as JSON, and the escape hatch when
the terminal's bidi reordering makes the table unreadable), `-a/--alternatives N` (runner-up
readings with their scores — the thin-win evidence steps 14 and 16 will need), `--raw` (skip
normalization), `--top N` (analyses kept per word).

Column padding is computed from display width, not `len`: diacritics are zero-width combining
marks and `len` counts them, which drifts every column after the first.

The table gained a `diac` column once the step 5 defect above was fixed and the two columns
stopped showing the same thing.

---

## Step 7 — parser interface

**`parse` returns a `Parse`, not a bare `list[int]`.** Heads and per-arc confidence are one
frozen value rather than two return channels, and it validates its own shape on construction:
confidence length matches, ids in range, nothing heads itself. Whether the result is a
well-formed single-rooted *tree* is deliberately not checked there — that is step 13.

**A parser is a component, not a pipeline stage.** `Parser.parse` returns integers;
`attach(tokens, parser)` is the pure stage that writes them onto copies of the tokens and stamps
`provenance["head"]`. Decided explicitly over the alternative of having backends return tokens:
evaluation then compares two integer lists, the token bookkeeping lives in one place instead of
once per backend, and a backend *cannot* reach `irab_role` because its return type has no room
for one. CLAUDE.md's conventions now record the distinction.

**Not built here: the env-var gate.** `Parser.eval_only` is declared, defaults to `False`, and
nothing reads it yet. The gate that does belongs to step 22, with the backend that needs it;
pulling it forward would be building a firewall around an empty room.

Note that the default is `False`, so a backend that forgets to declare itself is treated as
shippable. That is the right default for the free parser and the wrong failure mode for a
licensed one. Step 22 must declare `eval_only` deliberately and not rely on the default catching
a mistake.

---

## Data assets — what they are, and what we may do with them

CLAUDE.md's licensing section covers PADT only. Step 5 installed two more assets, and they sit
in a different licence bucket. Sorting them out needs two separate questions: *what kind of thing
is it*, and *what may we do with it*.

### What kind of thing

**Morphology database** — a lexicon plus affix tables. One word in, every analysis that word
could carry out: diacritized forms, lemma, root, POS, case, state, clitic segmentation. Word
level only. No sentences, no trees. Two exist for MSA and they **compete**; pick one.

- `morphology-db-msa-r13` — installed. Derives from Aramorph 1.2.1, itself a repackaging of the
  Buckwalter analyzer.
- `morphology-db-msa-s31` — not installed. Same API, same feature codes, drop-in replacement.
  Built from SAMA, LDC's successor to Buckwalter: wider coverage, cleaner diacritization. The
  gap is real and measured — `أتقرأ` comes back out of vocabulary under `-r13`, with
  `d3tok=NOAN` and a backoff guess of `noun_prop`. That is the price of staying free.

**Treebank** — not a lexicon at all. Human-annotated sentences carrying full dependency trees:
which word governs which, and what the relation is called. Labeled *examples*, not a dictionary.

- PADT / LDC2018T08 — not yet obtained.

The category difference is the point. No morphology database knows that الطالب attaches to كتب;
that information exists only in annotated sentences. Which is why they land in different steps:
`-r13` powers step 5, PADT is gold for steps 19–21 and training data for step 22.

### What we may do with it

| asset | licence | ships commercially? |
|---|---|---|
| `morphology-db-msa-r13` (installed) | GPL v2 | yes, with GPL obligations |
| `disambig-mle-calima-msa-r13` (installed) | GPL v2 | yes, with GPL obligations |
| `morphology-db-msa-s31` (**not** installed) | LDC restricted | no |
| PADT / LDC2018T08 (not yet obtained) | LDC Reduced-License | no — **and neither can a model trained on it** |

**LDC is an organization, not a licence.** The Linguistic Data Consortium distributes hundreds of
corpora under different terms — some members-only, some GPL. All four rows above are
LDC-published. Only the first two are free. Reading "LDC" as "forbidden" would rule out the
Buckwalter database for no reason at all.

The installed packages both carry this header in their `LICENSE` file:

```
### This database was derived from Aramorph1.2.1 available at,
### http://sourceforge.net/projects/aramorph/ and distributed under,
### GNU GENERAL PUBLIC LICENSE Version 2, by,
### Linguistic Data Consortium
```

LDC is the distributor; the GPL is the terms, inherited from Buckwalter's original release.

So the live constraint on shipped code is **GPL v2, not LDC**, and it is a different kind of
constraint: LDC's licence forbids commercial use outright, while the GPL permits it and instead
attaches source-disclosure obligations *on distribution*. A hosted web service does not normally
distribute, so the obligation likely never triggers — a question for a lawyer before launch, not
a question for this file.

PADT's restriction has the longer reach of the two. `-s31` is a file you would merely have to not
deploy; PADT contaminates anything *derived* from it. That is what step 22's env-var gate is for,
and why step 7 builds the interface before either backend exists.

**Standing rules.** Only ever install `-r13`. Read the `LICENSE` file inside a package; ignore the
publisher's name on the copyright line.

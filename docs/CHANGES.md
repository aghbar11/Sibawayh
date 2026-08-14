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
| 8 | backend is CamelParser's CATiB model, not Stanza — Stanza's Arabic model is non-commercial |
| 8 | CATiB labels kept in `parser_label` as evidence; still discarded for role derivation |
| 7 | `Parser.formalism` added so step 9 can dispatch instead of assuming one convention |
| 9 | arc normalization is per-formalism, not a single UD-shaped pass |
| 9 | CATiB → i'rab is re-rooting at token 1 and nothing else |
| 9 | UD and PADT normalizers raise instead of being written blind |
| 9 | `tests/data/catib_trees.json` — hand-derived CATiB input trees |
| 7 | `Formalism.IRAB` renamed `Formalism.SIBAWAYH`; `Token.irab_role` left alone |
| 2 | `parser_label` documented as a token property, not the name of its head arc |
| 8 | checkpoint converted to plain tensors + JSON; the published pickle is never loaded at runtime |
| 8 | `parser` extra is `supar`+`torch`, not `stanza`; `camel_parser` not used at all |
| 8 | `CatibParser.labels()` sits outside the `Parser` interface |
| 9 | CATiB fixture upgraded from hand-derived to verified against the real model |
| 10 | "no overt agent" tested via `parser_label=SBJ` **or** `case=nom`, not case alone |
| 10 | an `unknown` case blocks insertion — abstaining direction |
| 10 | inserted token is `pos=pron`, not the plan's `S-`, following the eval set |
| 11 | a rule's `when` returns its evidence, not a boolean — matching and evidence are one act |
| 11 | the registry is constructed explicitly, never populated by import side effects |
| 11 | rules take `(token, head, tokens)`; "sentence" is the token sequence, not a `Sentence` |

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

**Amended before step 8.** `Parser.formalism` added — see step 9 below.

---

## parser backend: CATiB, not UD

### Why not Stanza.

I thought that Stanza was *"MIT-licensed, trained on a free Arabic treebank, and therefore
safe to ship."* It is not. Stanza is Apache 2.0, but its Arabic model is trained on UD_Arabic-PADT, which is
**CC BY-NC-SA 3.0** — non-commercial.

 It is the same corpus the whole `parsers/` firewall exists to quarantine, wearing
a different licence. Stanza was never the escape hatch from the PADT problem.

### Why not the UD model from the same lab

`CAMeL-Lab/camelbert-ud-parser` is MIT and shares CamelParser's ecosystem, so it looked like the
way to keep UD as a future formalism. It is trained on NUDAR (UD_Arabic-NYUAD), which is
CC BY-SA 4.0 but ships **no word forms** — *"The underlying text is not included; the user must
obtain it separately"* — meaning LDC PATB. Same encumbrance, one step further away.

The question that settles it is what a future self-trained parser would train *on*:

| corpus | formalism | licence | text included? | size |
|---|---|---|---|---|
| UD_Arabic-PADT | UD | CC BY-NC-SA 3.0 | yes | 7.7k sentences |
| UD_Arabic-NYUAD | UD | CC BY-SA 4.0 | **no** — needs LDC PATB | 19.7k sentences |
| UD_Arabic-PUD | UD | permissive | yes | 1k sentences, test only |
| CamelTB | CATiB | open | yes | 188k words |

There is no openly-licensed, training-sized Arabic UD treebank that ships its own text. **CamelTB
is the only free training corpus, and it is CATiB.** Committing to UD as the long-term formalism
would guarantee the licensing problem rather than avoid it.

In the future, I will train a CATiB parser on CamelTB alone. I think it will be shippable. Until
then, we will use the existing CamelParser CATiB model, which is MIT-licensed and trained on
CamelTB + PATB.

### Why CATiB suits i'rab better anyway

CATiB has eight labels: `SBJ`, `OBJ`, `TPC`, `PRD`, `IDF`, `TMZ`, `MOD`, `---`. The definitions
are traditional-grammar-shaped:

- `OBJ` is *"object of verb, **preposition**, or deverbal noun"* — the preposition is the head,
  which is i'rab's convention and the opposite of UD's `case`.
- `IDF` is the idafa relation directly. `TMZ` is tamyiz directly.

### What this does not change

**The rule engine is unaffected in scope.

| CATiB | i'rab roles it collapses | discriminator |
|---|---|---|
| `SBJ` | فاعل · نائب فاعل · مبتدأ · اسم كان | head POS, **voice**, head lemma |
| `OBJ` | مفعول به · اسم مجرور · مضاف إليه | head POS |
| `PRD` | خبر كان · خبر إنّ | head lemma — inverse case patterns |
| `MOD` | صفة · حال · ظرف · جار ومجرور · بدل · توكيد | **definiteness**, case, POS |
| `IDF` / `TMZ` | مضاف إليه · تمييز | — 1:1 |

Every discriminator in the right column is morphology, not attachment, and no parser in any
formalism can see them. Nor do labels supply abstention, the `evidence` lists the hint ladder is
built from, or covert pronouns.

`verbal_passive_01` makes the point harder than I first claimed. I wrote that it comes back `SBJ`
either way and that only `vox=p` separates فاعل from نائب فاعل. The model actually emits **`OBJ`**:
undiacritized كتبت reads just as easily as active كَتَبَت 'she wrote' with a covert agent, and CAMeL
ranks that active reading first too. The head is unchanged, so normalization is untouched — but
the label is not a reliable narrowing here, and voice is doing more work than the table suggests.

### How it actually ships: converted, not loaded

The published checkpoint is a 2023 `torch.save` of **live Python objects** — supar's config, its
data transform, and a `transformers` 4.29 tokenizer frozen mid-flight. Loading it as published
needs all four of:

1. supar pinned to an unreleased git commit (`17ec77dd`), where `Config` lived at `supar.config`
   rather than `supar.utils.config`. No PyPI release matches; `camel_parser` pins that SHA.
2. `weights_only=False`. torch ≥2.6 refuses pickled classes by default, and the safe-globals
   allowlist **cannot** bridge a renamed module — it keys on the class's real `__module__`, so
   allowlisting an aliased path loops forever.
3. A `sys.modules` alias for `transformers.models.bert.tokenization_bert_fast`, removed in 5.x.
4. A serial replacement for supar's `mp.Pool`, hardcoded over a local closure and therefore
   fork-only. It cannot run on Windows at all.

Even with all four it still fails: the unpickled 4.29 tokenizer lacks `split_special_tokens`,
which 5.x requires. `camel_parser` pins `transformers==4.29.2`, `torch==2.0.1`,
`camel_tools==1.5.6`; our morphology layer is built and tested against camel-tools 1.6.0.
Irreconcilable inside one environment.

**So the checkpoint is converted once and never loaded again.**
`scripts/convert_catib_checkpoint.py` opens it with those four shims, takes the parts that have no
version, and writes:

    weights.pt    212 plain tensors, loadable with `weights_only=True`
    config.json   architecture settings + the CATiB label inventory

`sibawayh/parsers/catib.py` reads only those two. All four problems disappear: ordinary `supar`
from PyPI, no code execution on load, no module aliasing, and no supar `Dataset` — the subword
tensor is built directly, which is what sidesteps the fork-only pool.

Note this is the **model** we chose over Stanza, reached directly. What is not used is
`camel_parser`, CAMeL's CLI wrapper around it: it redoes tokenization and POS tagging we already
have, pins a conflicting stack, and writes CoNLL-X files where we want a return value.

The tokenizer is deliberately not carried across. It was never the valuable part — stock
CAMeLBERT-MSA, freely downloadable — and it was precisely what blocked loading. It is rebuilt at
runtime from the repo the checkpoint names in `args.bert`, and the backend refuses to run if the
two disagree: the embedding table has 30000 rows, that tokenizer has 30000 entries, and a mismatch
would map every word to the wrong row. It is a *subword* tokenizer and it never re-segments the
sentence — it splits within each CAMeL token (العصفور → `العص` + `##فور`) and the encoder pools the
pieces back, so one CAMeL token still gets exactly one head.

Evidence the transplant is exact:

- `load_state_dict(strict=True)` — **0 missing, 0 unexpected.** The single dropped key,
  `encoder.model.embeddings.position_ids`, is a constant buffer newer transformers no longer
  registers, not a learned weight.
- The rebuilt model reproduces **13 of 13** CATiB trees, heads and labels both.

The checkpoint's `args` also settle the licensing question above from the other direction: `train`
reads `PATB123-train+CamelTB-ALL-train` — PATB (LDC) combined with CamelTB (open), exactly as the
model card says. `eval_only` stays `False` on the strength of the MIT grant; recorded, not
resolved.

**One trap worth recording.** The first download was silently truncated at 375MB of 445MB. It
still carried a valid zip header, so it failed much later with "failed finding central directory",
which reads like a corrupt model rather than a short read. The conversion script checks the size
first.

### `labels()` is deliberately outside the `Parser` interface

`CatibParser.labels(tokens)` returns CATiB relation names. It is a separate method on purpose:
`Parser.parse` returns `Parse`, which holds integers and structurally cannot carry a role — the
guarantee that keeps `parser_label` and `irab_role` apart. Putting labels in the interface would
hand every future backend a channel for smuggling roles into the pipeline. Callers that want them
as *evidence* ask explicitly.

### Arc confidence turned out to be reachable

The plan said *"extract arc confidence from the biaffine score matrix if reachable."* It is:
`s_arc.softmax(-1)` is P(head | dependent), and `parse` returns the probability of the chosen head
as `Parse.confidence`. The first real input to the abstention layer.

### Test tiers

The converted model is ~440MB and is not in version control, so the backend's tests split: the
wrapper's own logic runs by default with no model present, and the tests that touch the real model
carry a `parser` marker, deselected like `camel`. `addopts` is now
`-m 'not camel and not parser'`. One of the default tests asserts that importing
`sibawayh.parsers.catib` does **not** import torch — loading is deferred so the morphology-only CLI
stays fast, and that is easy to break by accident.

---

## Step 9 — arc normalization becomes per-formalism

The plan describes one pass flipping UD conventions. It ships as a dispatch on the formalism the
backend declares, with a CATiB normalizer written now and a UD one only if a UD backend ever
lands.

`Parser.parse` returns head integers, so it is already formalism-agnostic and does not change.
`arcs.py` is the only module that cannot be — flipping arcs means knowing what convention they
arrived in. Hard-wiring one convention there is the actual lock-in risk, and it exists whichever
formalism is chosen first. `Parser.formalism` (step 7, amended) is what the dispatch reads.

Cost of a future UD backend: one normalizer module. Nothing else moves.

### What the CATiB normalizer turned out to be

**Re-rooting at token 1. That is the whole conversion.**

The guidelines paper (Habash, Faraj & Roth 2009) carries worked trees for exactly the
constructions the eval set tests. Checked against them, CATiB agrees with i'rab on every
*internal* arc:

| construction | CATiB, per the guidelines | vs i'rab |
|---|---|---|
| prepositional phrase | *"Prepositions always head their objects (OBJ)"* — Fig 1(h) | same |
| idafa | `IDF` marks the possessor, so المضاف heads | same |
| كان / إنّ | *"the topic/subject and complement/predicate are considered children of the incomplete verb with the relations SBJ and PRD"* — Figs 1(f), 1(g) | same |
| adjective | `MOD` onto the noun — Fig 2(h) | same |
| nominal sentence | *"the verbless complement/predicate (الخبر) heads the topic/subject (المبتدأ)"* — Fig 1(e) | **root differs** |
| verbal particle | *"These particles always attach under the verb with the relation MOD"* — Fig 1(o) | **root differs** |

Both disagreements are the same disagreement: CATiB roots at the predicate, i'rab at the first
word of the sentence. So the conversion is a re-rooting — reverse the arcs on the path from token
1 to the current root, leave every other governor alone. All thirteen tier-1 sentences come out
equal to gold; five need no change at all, and the eight that do rewrite exactly two heads each.

Three things fall out that are worth keeping:

- **No labels are needed.** Re-rooting reads head integers only, which is fortunate, because
  `Parse` carries none. Discarding `deprel` costs nothing here.
- **Word order does the work a label could not.** CATiB gives the *same* tree to verb-initial
  كتب الرجال الكتاب (Fig 1a) and topic-initial الرجال كتبوا الكتاب (Fig 1j). I'rab distinguishes
  them, and re-rooting at token 1 separates them because it keys on position.
- **The rule is a proxy, not the law.** The real principle is that العامل governs its معمول;
  "first word" coincides with it across tier 1 because Arabic العامل normally precedes what it
  governs. Tier 2 may separate them. Recorded now so a later failure is recognised rather than
  debugged from scratch.

  Why did we use re-rooting?
  Because the CATiB heads were checked against the eval set, and the eval set is checked against the gold. The gold is what the rule engine
  expects. They prove that the code for choosing the heads is correct.


### `parser_label` outlives the arc it described

Re-rooting moves arcs but not labels, so on a re-rooted token the label describes an edge that no
longer exists: in كتاب الطالب جديد, كتاب keeps `SBJ` while becoming the root. The label is kept
anyway and the schema now says why — it stays useful *evidence* (`SBJ` argues for فاعل or مبتدأ
however the tree was re-hung) and it is the strongest signal the parser hands the rule engine.
Read as a property of the token, never as the name of an edge.
/
### Coordination, now with a concrete failure mode

Still a known gap, as planned, but the guidelines make the symptom specific: a sentence-initial و
*"is attached to the head of the sub-tree that follows it with the relation MOD"*. Re-rooting at
token 1 would therefore hang the whole sentence under a discourse connective. Recorded in the
module docstring rather than patched — guessing at coordination here would be worse than leaving
the failure visible.

---

## Step 10 — covert pronoun insertion

### The test for "no overt agent" uses two signals, not one

The plan says *"for each verb with no overt agent among its dependents"*, and leaves open how a
stage that runs **before** the rule engine is supposed to know which dependent is the agent. It
cannot read `irab_role`; nothing has written one yet.

Two signals are used, and **either** is enough to block insertion:

* `parser_label == "SBJ"` — CATiB's own judgement, *"the explicit subject of a verb, active or
  passive"*
* `case == nom` — the morphological signal

The redundancy is the point. Step 5 already recorded that CAMeL reads الرجل in
`verbal_overt_agent_01` as **accusative**; on case alone that sentence would gain a ضمير مستتر
next to a subject the student can plainly see. The parser's `SBJ` catches it. A parser mislabel is
caught the other way round.

**A dependent whose case is `unknown` also blocks insertion.** That is the abstaining direction
CLAUDE.md asks for: an unreadable case might be the agent, and asserting a covert pronoun where
none exists is a worse failure than omitting one. It costs recall on undiacritized input, which is
the right trade for a teaching tool.

**Passive needs no special case.** نائب فاعل is nominative, so it registers as a candidate through
the same test — `verbal_passive_01` is skipped without the stage ever looking at `voice`.

### `pos` is `pron`, not `S-`

The plan says to insert with `pos: S-`. That is a Buckwalter-style tag and not in our `Pos` set;
`data/eval/sentences.json`, which is the spec, uses `pron`. Followed the eval set.

### What the stage does and does not set

`form`, `pos`, `feats`, `head`, `inserted`, `evidence` and `provenance` — all stamped `covert`.
**`irab_role` stays empty.** Gold names the token فاعل — ضمير مستتر, but naming is the rule
engine's job and this stage has no business pre-empting it.

Person, gender and number are copied from the verb; `case` is set to `nom`, since an agent is
nominative by definition and a verb has no case to copy. Aspect, mood, voice and state are
explicitly *cleared* — a pronoun has none of them, and leaving them on would give the renderer
nonsense to describe.

The form is the pronoun agreeing with the verb (هو / هي / هم / هن / أنا / نحن / أنت / هما), always
suffixed `*`, so a token we invented can never be mistaken for one the student typed.

### The stage is idempotent, and that took a fix

The first version excluded already-inserted tokens when scanning for a candidate agent, so a
second pass saw the verb as agentless again and gave it a second pronoun. Backwards: an inserted
pronoun **is** the agent, and now counts as one. A test pins it.

### End to end

`pytest -m parser` now runs the full structural chain on the real model —
parse → attach → arc normalization → covert insertion — against gold *including* the inserted
token. **13 of 13**, with `nominal_verbal_predicate_01` coming out at four tokens and the ids
correctly shifted.

Morphology in that test comes from gold rather than CAMeL. The structure is what is being
asserted; the morphology layer has its own tests and its own recorded disagreements, and mixing
them would make a failure ambiguous.

---

## Step 11 — rule engine skeleton

### A rule returns its evidence, not a boolean

The plan describes a rule as a predicate over `(token, head, sentence)` yielding
`(irab_role, rule_id, evidence)`. Implemented so that `Rule.when` returns **the evidence list, or
`None`** — matching and explaining are the same act.

Splitting them would allow a rule to fire without being able to say why, and the `evidence` list
is not decoration: CLAUDE.md specifies it as a list precisely because the hint ladder reveals it
one item at a time, and the hint ladder is the product. A rule that cannot explain itself has
nothing to teach.

Evidence is ordered cheapest-observation-first, matching the ladder — locate, identify the عامل,
name the role. `PREP_OBJECT` emits `head_pos=prep`, then `head_form=في`, then the case.

### The registry is built, not discovered

No decorator that registers on import. A registry that fills itself as modules happen to be
imported makes rule *ordering* depend on import order, which is invisible in the source and
miserable to debug — and ordering is load-bearing here, since first-match-wins means a general
rule placed before a specific one silently shadows it.

`Registry` is constructed from an explicit sequence, sorts on `(priority, id)` so ties are
deterministic rather than insertion-ordered, and refuses duplicate ids: a repeated `rule_id` would
make the field recorded on the token ambiguous, which defeats the point of recording it.

### Abstention is a return value, not an exception

`first_match` returns `None` when nothing fires, and `apply_rules` then returns that token
**unchanged** — `irab_role` stays `None`, no `rule_id`, no `irab_role` key in `provenance`. There
is deliberately no fallback rule and no default role. A token with no role is the normal, correct
outcome for most tokens at this stage.

### `(token, head, tokens)` rather than a `Sentence`

The plan says "sentence"; the third argument is the token `Sequence`. Building a `Sentence` model
would require the raw text, which this stage does not have and does not need, and every pipeline
stage is `(list[Token]) -> list[Token]`. `head` is resolved for the rule and is `None` at the root,
so a rule can tell the root apart from an unparsed token without doing the lookup itself.

### Evidence accumulates across layers

A rule appends to whatever earlier stages recorded rather than replacing it, so the inserted
pronoun keeps `covert.py`'s note about *why it exists* and gains the rule's note about *what it
is*. Gold's evidence lists in `data/eval/sentences.json` are therefore a subset of what the
pipeline produces, not an exact target — they were written by hand, one layer at a time.

### The two starter rules

Chosen for being the least likely to need revising when the real inventory lands, and both are
conclusions already earned elsewhere rather than new judgements:

| rule | role | why it is safe |
|---|---|---|
| `COVERT_AGENT` | فاعل — ضمير مستتر | true by construction — `covert.py` inserts a pronoun *precisely when* a verb has no overt agent |
| `PREP_OBJECT` | مجرور | true by definition — under Sibawayh convention the preposition is the عامل and heads its object |

Both role strings are asserted equal to the gold ones. `COVERT_AGENT` keys on `inserted`, not on
being a pronoun, so a typed هو is not its business.

A test runs both rules across all thirteen eval sentences and asserts that **whatever fires agrees
with gold**. Most tokens get nothing, which is correct at this stage. What must never happen is a
confident wrong answer, and that is what the test pins.

`apply_rules` is also the only place in the pipeline that writes `irab_role`.

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
- CamelTB — open, CATiB-annotated, 188k words. Not yet obtained; relevant to a future
  cleanly-licensed parser, not to any current step.

**Parser model** — a third category, and the one that carries licences forward. Weights, not data
and not a lexicon (weights come from checkpoint in the model directory). 

- `camelbert-catib-parser` — step 8's backend.

The category difference is the point. No morphology database knows that الطالب attaches to كتب;
that information exists only in annotated sentences. Which is why they land in different steps:
`-r13` powers step 5, PADT is gold for steps 19–21 and training data for step 22.

### What we may do with it

| asset | licence | ships commercially? |
|---|---|---|
| `morphology-db-msa-r13` (installed) | GPL v2 | yes, with GPL obligations |
| `disambig-mle-calima-msa-r13` (installed) | GPL v2 | yes, with GPL obligations |
| `camelbert-catib-parser` (step 8) | MIT weights, trained on CamelTB + PATB | probably — see step 8 |
| CamelTB (not obtained) | open | yes |
| `morphology-db-msa-s31` (**not** installed) | LDC restricted | no |
| UD_Arabic-PADT (Stanza's training data) | CC BY-NC-SA 3.0 | **no — non-commercial** |
| UD_Arabic-NYUAD | CC BY-SA 4.0, text withheld | no — text requires LDC PATB |
| PADT / LDC2018T08 (not yet obtained) | LDC Reduced-License | no — **and neither can a model trained on it** |


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
publisher's name on the copyright line. For a *model*, the licence on the weights is only half the
answer — find what corpus it was trained on and check that too. Step 8 turned on exactly this:
Stanza is Apache-licensed software whose Arabic model is trained on non-commercial data, and
nothing in the install tells you so.

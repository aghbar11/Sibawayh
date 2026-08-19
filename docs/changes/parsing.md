# Parsing

Which word governs which. The interface a parser must satisfy, the backend
chosen to satisfy it, and the conversion from that backend's conventions to
the ones i'rab expects.

## The parser interface

**`parse` returns a `Parse`, not a bare `list[int]`.** Heads and per-arc confidence are one
frozen value rather than two return channels, and it validates its own shape on construction:
confidence length matches, ids in range, nothing heads itself. Whether the result is a
well-formed single-rooted *tree* is deliberately not checked there — that is validation.

**A parser is a component, not a pipeline stage.** `Parser.parse` returns integers;
`attach(tokens, parser)` is the pure stage that writes them onto copies of the tokens and stamps
`provenance["head"]`. Decided explicitly over the alternative of having backends return tokens:
evaluation then compares two integer lists, the token bookkeeping lives in one place instead of
once per backend, and a backend *cannot* reach `irab_role` because its return type has no room
for one. CLAUDE.md's conventions now record the distinction.

**Not built here: the env-var gate.** `Parser.eval_only` is declared, defaults to `False`, and
nothing reads it yet. The gate that does belongs to the evaluation-only parser backend, with the backend that needs it;
pulling it forward would be building a firewall around an empty room.

Note that the default is `False`, so a backend that forgets to declare itself is treated as
shippable. That is the right default for the free parser and the wrong failure mode for a
licensed one. the evaluation-only parser backend must declare `eval_only` deliberately and not rely on the default catching
a mistake.

**Amended before the parser backend.** `Parser.formalism` added — see arc normalization below.

---

## The parser backend: CATiB, not UD

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

**The rule engine is unaffected in scope.**

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

## Arc normalization

The plan describes one pass flipping UD conventions. It ships as a dispatch on the formalism the
backend declares, with a CATiB normalizer written now and a UD one only if a UD backend ever
lands.

`Parser.parse` returns head integers, so it is already formalism-agnostic and does not change.
`arcs.py` is the only module that cannot be — flipping arcs means knowing what convention they
arrived in. Hard-wiring one convention there is the actual lock-in risk, and it exists whichever
formalism is chosen first. `Parser.formalism` (the parser interface, amended) is what the dispatch reads.

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

**Why re-rooting is trusted.** The CATiB heads were checked against the eval set, and the eval
set was checked by hand against the gold analysis. Gold is what the rule engine expects, so
agreement across all thirteen sentences is evidence that the head selection is right — not just
that it is self-consistent.

### `parser_label` outlives the arc it described

Re-rooting moves arcs but not labels, so on a re-rooted token the label describes an edge that no
longer exists: in كتاب الطالب جديد, كتاب keeps `SBJ` while becoming the root. The label is kept
anyway and the schema now says why — it stays useful *evidence* (`SBJ` argues for فاعل or مبتدأ
however the tree was re-hung) and it is the strongest signal the parser hands the rule engine.
Read as a property of the token, never as the name of an edge.
### Coordination, now with a concrete failure mode

Still a known gap, as planned, but the guidelines make the symptom specific: a sentence-initial و
*"is attached to the head of the sub-tree that follows it with the relation MOD"*. Re-rooting at
token 1 would therefore hang the whole sentence under a discourse connective. Recorded in the
module docstring rather than patched — guessing at coordination here would be worse than leaving
the failure visible.

---

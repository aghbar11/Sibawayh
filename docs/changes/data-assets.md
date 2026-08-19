# Data assets

What the project depends on, where it came from, and what may be done with it.

## Data assets — what they are, and what we may do with them

CLAUDE.md's licensing section covers PADT only. morphology installed two more assets, and they sit
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

- `camelbert-catib-parser` — the parser backend's backend.

The category difference is the point. No morphology database knows that الطالب attaches to كتب;
that information exists only in annotated sentences. Which is why they land in different steps:
`-r13` powers morphology, PADT is gold for the confidence layer and 21 and training data for the evaluation-only parser backend.

### What we may do with it

| asset | licence | ships commercially? |
|---|---|---|
| `morphology-db-msa-r13` (installed) | GPL v2 | yes, with GPL obligations |
| `disambig-bert-unfactored-msa` (**what we ship**) | MIT weights, over the GPL v2 database | yes, with the database's GPL obligations |
| `disambig-mle-calima-msa-r13` (installed, fallback) | GPL v2 | yes, with GPL obligations |
| `camelbert-catib-parser` (the parser backend) | MIT weights, trained on CamelTB + PATB | probably — see the parser backend |
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
deploy; PADT contaminates anything *derived* from it. That is what the evaluation-only parser backend's env-var gate is for,
and why the parser interface builds the interface before either backend exists.

**Standing rules.** Only ever install `-r13`. Read the `LICENSE` file inside a package; ignore the
publisher's name on the copyright line. For a *model*, the licence on the weights is only half the
answer — find what corpus it was trained on and check that too. the parser backend turned on exactly this:
Stanza is Apache-licensed software whose Arabic model is trained on non-commercial data, and
nothing in the install tells you so.

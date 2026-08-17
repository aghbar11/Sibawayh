# Field reference

What every field on a token means, what values it can hold, and which layer put it there.
For when you are reading a rule and cannot remember, see this file.

Values here are taken from `sibawayh/schema.py`. If they disagree with the code, the code wins —
and this file needs updating.

---

## The three kinds of absence

Every feature can be missing in three different ways, and the difference is load-bearing.

| value | meaning | what to do about it |
|---|---|---|
| `None` | **not analyzed yet** — the layer that fills this has not run | wait; not an error |
| `"null"` | **not applicable** — a verb has no case, a noun has no mood | correct and final |
| `"unknown"` | **could not be determined** — CAMeL saw the word and could not tell | **abstain** |

`"null"` is the *string* `"null"`, never JSON `null`. Collapsing it with `"unknown"` would make
undiacritized input look confident, which is the failure CLAUDE.md says kills the product.

In a rule, `if token.feats.case is Case.NOM` is safe: all three absences fail it, so an
undetermined case never gets treated as nominative.

---

## `token.feats` — morphology

Eight fields. This is what the rules key on almost exclusively.

### `case` — الإعراب

The single most important field. Most i'rab roles are a case plus a context.

| value | Arabic | CAMeL code | example |
|---|---|---|---|
| `nom` | مرفوع | `n` | الرجلُ — فاعل, مبتدأ, اسم كان |
| `acc` | منصوب | `a` | السمكَ — مفعول به, خبر كان, اسم إنّ |
| `gen` | مجرور | `g` | الطالبِ — مضاف إليه, object of a preposition |
| `null` | — | `na` | a verb or a particle; case does not apply |
| `unknown` | — | `u` | undiacritized and ambiguous → abstain |

### `state` — التعريف والإضافة

Definiteness, plus the إضافة signal. Discriminates صفة from خبر, and identifies المضاف.

| value | Arabic | CAMeL code | example |
|---|---|---|---|
| `construct` | مضاف | `c` | كتابُ الطالبِ — كتاب is `construct` |
| `def` | معرفة | `d` | الكتاب |
| `indef` | نكرة | `i` | كتاب |
| `null` / `unknown` | — | `na` / `u` | |

`construct` counts as **definite** for agreement — a construct noun takes its definiteness from
what follows it. See `DEFINITE` in `rules/modifiers.py`.

### `voice` — البناء للمعلوم والمجهول

Turns a nominative from فاعل into نائب فاعل. Nothing else can.

| value | Arabic | CAMeL code |
|---|---|---|
| `active` | مبني للمعلوم | `a` |
| `passive` | مبني للمجهول | `p` |
| `null` / `unknown` | — | `na` / `u` |

### `aspect` — الزمن

| value | Arabic | CAMeL code |
|---|---|---|
| `perfect` | ماضٍ | `p` |
| `imperfect` | مضارع | `i` |
| `imperative` | أمر | `c` |
| `null` | — | `na` |

No `unknown` member — CAMeL never reports one.

**Trap:** CAMeL sets `mood` on perfect verbs too, so a rule keyed on mood alone will claim a past
verb as مضارع. Check aspect as well. This was a real bug; see `rules/verbal.py`.

### `mood` — إعراب الفعل المضارع

| value | Arabic | CAMeL code | caused by |
|---|---|---|---|
| `indicative` | مرفوع | `i` | nothing governing it |
| `subjunctive` | منصوب | `s` | a ناصب — لن, أن, كي |
| `jussive` | مجزوم | `j` | a جازم — لم, لما |
| `null` | — | `na` | not an imperfect verb |
| `unknown` | — | `u` | **the common case** |

`unknown` is what you will actually see. يقرأُ / يقرأَ / يقرأْ are spelled identically
undiacritized, so both disambiguators decline — the mood is recoverable from the governing
particle, not from the word.

### `gen`, `num`, `person` — agreement

| field | values | notes |
|---|---|---|
| `gen` | `m` `f` `b` `null` `unknown` | `b` = valid as either. Declared by CAMeL but **never observed** in `-r13`; kept defensively |
| `num` | `s` `d` `p` `b` `null` `unknown` | singular, dual, plural |
| `person` | `1` `2` `3` `null` | strings, not ints — `Person.THIRD` is `"3"` |

These are the **functional** values, not `form_gen`/`form_num`. Agreement checks (صفة) need the
functional pair; the surface pair can disagree with it.

`covert.py` reads all three off the verb to pick which pronoun to insert.

---

## `token.pos` — part of speech

Our coarse set. CAMeL's finer tag survives in `pos_fine`.

| value | Arabic | example |
|---|---|---|
| `noun` | اسم | كتاب |
| `propn` | اسم علم | محمد |
| `adj` | صفة | جديد |
| `verb` | فعل | يأكل |
| `pron` | ضمير | هو |
| `prep` | حرف جر | في |
| `conj` | حرف عطف | و — also where BERT puts إنّ |
| `part` | حرف | لم |
| `adv` | ظرف | — CAMeL usually calls these `noun` |
| `punct` | علامة ترقيم | . |

**`NOMINAL` = `{noun, propn, adj, pron}`** — the الاسم family, the four that can be a فاعل or
مبتدأ. `adj` belongs because Arabic does not treat adjectives as a separate class: صفة is a
*role*, not a part of speech.

`pos_fine` keeps the original tag, which matters where the coarse one loses information:
`pron_dem` (اسم إشارة) vs `pron_rel` (اسم موصول), `part_neg` for لم/لن/لا, `conj_sub` for أنّ.

---

## `Token` — the other fields

A token is one word *in a sentence*, or a covert pronoun we inserted.

| field | set by | meaning |
|---|---|---|
| `id` | morphology | 1-based position. `0` is never a token — it means ROOT |
| `form` | morphology | the surface word, as typed, marks stripped |
| `diac` | morphology | the vowelled form — **show this to the student** |
| `lemma` | morphology | dictionary form. كتب/يكتب/كاتب → كَتَب. What `lexicon.py` matches |
| `root` | morphology | the triliteral ج.ذ.ر — ك.ت.ب. Useful for hint text |
| `pos`, `pos_fine`, `feats` | morphology | see above |
| `head` | parser, then `arcs` | id of the governing token; `0` at the root |
| `parser_label` | parser | CATiB's own label — `SBJ`, `OBJ`, `IDF`, `PRD`, `MOD`, `TMZ`, `---` |
| `arc_confidence` | parser | P(this head) from the biaffine matrix, 0–1 |
| `irab_role` | **rules only** | the Arabic role a student reads — فاعل, مبتدأ |
| `rule_id` | rules | which rule produced it, so a wrong answer is traceable |
| `evidence` | every layer | why, one item at a time. The hint ladder reads this in order |
| `confidence` | abstention layer | the combined score. Not yet written |
| `provenance` | every layer | which layer set which field |
| `alternatives` | morphology | runner-up `Analysis` objects with scores |
| `inserted` | `covert.py` | `True` for a ضمير مستتر. **Exclude from treebank scoring** |

**`parser_label` is not the name of the current arc.** Re-rooting moves arcs but not labels, so on
a re-rooted token the label describes an edge that no longer exists. Read it as a property of the
token — `SBJ` still argues for فاعل or مبتدأ however the tree was later re-hung.

---

## `Analysis` vs `Token`

One word in the sentence = one **`Token`**. The competing guesses about what that word is =
**`Analysis`**, several per token.

`Analysis` has no `id`, `form` or `head` — those belong to a position in a sentence, not to a guess
about a word. It adds `score` and `source`.

The winner is copied onto the `Token`; the rest sit in `token.alternatives`. The **gap between the
top two scores** is the morphology confidence signal — a thin margin means the answer is fragile
even when it looks definite.

---

## `provenance` — who set what

Maps a `Token` field name to the layer that wrote it.

| value | layer |
|---|---|
| `camel` | `morphology.py` |
| `parser` | a parser backend, via `attach` |
| `arcs` | `arcs.py`, on tokens whose head actually moved |
| `covert` | `covert.py`, on inserted tokens |
| `rules` | `rules/`, on `irab_role` |
| `llm` | the renderer |
| `gold` | hand-written, from `data/eval/sentences.json` |

---

## `Sentence`

| field | meaning |
|---|---|
| `sentence` | the raw text, normalized |
| `tokens` | the tokens, ids sequential from 1 |
| `id` | eval-set identifier — `sifa_01` |
| `category`, `tier`, `notes` | eval-set metadata only |

Helpers: `by_id(n)` and `head_of(token)`, which returns `None` at the root.

---

## Quick answers

**"Is this the مبتدأ?"** → at the root, `pos in NOMINAL`, `case is Case.NOM`.

**"Is this an إضافة?"** → head has `state is State.CONSTRUCT` **and** token has `case is Case.GEN`.

**"صفة or خبر?"** → both are `adj`, `nom`, under the same noun. **Definiteness agreement** decides:
agrees → صفة, disagrees → خبر.

**"فاعل or نائب فاعل?"** → the *head verb's* `voice`.

**"اسم كان or خبر إنّ?"** → both nominative. The *head's lemma* decides — the two families assign
opposite cases.

**"Why did nothing fire?"** → most likely `case is Case.UNKNOWN` or `mood is Mood.UNKNOWN`.
That is abstention working, not a bug. You know, let's not confuse the student.

# From attachment to إعراب

The parser says what attaches to what. These layers turn that into named
grammatical roles — inserting the pronouns Arabic leaves unwritten, then
deriving each word's role from what was observed about it.

## Covert pronoun insertion

### The test for "no overt agent" uses two signals, not one

The plan says *"for each verb with no overt agent among its dependents"*, and leaves open how a
stage that runs **before** the rule engine is supposed to know which dependent is the agent. It
cannot read `irab_role`; nothing has written one yet.

Two signals are used, and **either** is enough to block insertion:

* `parser_label == "SBJ"` — CATiB's own judgement, *"the explicit subject of a verb, active or
  passive"*
* `case == nom` — the morphological signal

The redundancy is the point. morphology recorded that CAMeL read الرجل in `verbal_overt_agent_01` as
**accusative**; on case alone that sentence would gain a ضمير مستتر next to a subject the student
can plainly see. The parser's `SBJ` catches it. A parser mislabel is caught the other way round.

*(BERT now reads الرجل as nominative, so that particular example no longer fires. The redundancy
stays: `verbal_passive_01` immediately below is the same failure under a different word, and it
still happens.)*

**A dependent whose case is `unknown` also blocks insertion.** That is the abstaining direction
CLAUDE.md asks for: an unreadable case might be the agent, and asserting a covert pronoun where
none exists is a worse failure than omitting one. It costs recall on undiacritized input, which is
the right trade for a teaching tool.

**Passive needs no special case.** نائب فاعل is nominative, so it registers as a candidate through
the same test — `verbal_passive_01` is skipped without the stage ever looking at `voice`.

*(True on gold morphology, which is what that claim was measured against. On real bare input BERT
reads المقالة as accusative, so it is not a candidate, and the stage inserts a هي* that does not
belong. Typed diacritics fix it by making المقالة nominative again. The mechanism is right; it
inherits whatever the morphology layer got wrong.)*

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

## The rule engine

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

## The core i'rab rules

Taken one file at a time. This entry covers `verbal.py`; the rest follow.

### `verbal.py` — the verb, فاعل، نائب فاعل، مفعول به

Nine rules. Result on the eval set: **17 of 40 tokens labelled, 0 wrong.** The three plain verbal
sentences come out complete; `jussive_lam_01` and `subjunctive_lan_01` come out complete apart
from the particle itself, which is `particles.py`'s.

#### The exclusions are the hard part, not the rules

Two things had to be got right, and both are about *not* answering.

**كان وأخواتها are not complete verbs.** A nominative under كان is اسم كان, not فاعل; an
accusative is خبر كان, not مفعول به. Those roles belong to `nawasikh.py`, which does not exist
yet — so every rule here excludes النواسخ **itself** rather than relying on a higher-priority file
to outrank it later. Deferring would mean shipping a confident wrong answer in the meantime, on a
sentence the eval set already contains. `nasikh_kana_01` comes back entirely unlabelled, which is
the correct behaviour today.

**A verb can be a خبر.** In محمد يقرأ الكتاب gold names the verb خبر — جملة فعلية, not
فعل مضارع مرفوع. So the rules that name a verb's own form fire only when it *heads its clause* —
at the root, or under a governing particle like لم. A verb hanging off a nominal is left for
`nominal.py`.

Two independent signals catch a ناسخ, for the same reason two signals catch an overt agent in
`covert.py`: the lemma list, and a dependent labelled `PRD` — which CATiB uses *only* for
كان وأخواتها and إنّ وأخواتها. Either one is enough, so a ناسخ missing from our list is still
caught when the parser recognised it.

#### One rule per verb form

The verb's own role is a composed string — aspect, voice, mood. Rather than making `Rule.role`
callable, it ships as five explicit rules: `VERB_PERFECT_ACTIVE`, `VERB_PERFECT_PASSIVE`,
`VERB_IMPERFECT_INDICATIVE`, `VERB_IMPERFECT_SUBJUNCTIVE`, `VERB_IMPERFECT_JUSSIVE`.

It costs a few more lines and buys a distinct `rule_id` per form, so a wrong answer names the exact
rule that produced it and the hint text can differ per form — which it will, since explaining
جزم is not explaining بناء للمجهول. `Rule` itself stays unchanged.

**A passive imperfect has no rule.** Gold has no example, and inventing the string would be a
guess; the imperfect rules explicitly refuse a passive verb rather than silently dropping the
voice from the answer.

#### `rules/lexicon.py`

Closed-class word lists — كان وأخواتها, إنّ وأخواتها, the jussive and subjunctive particles.
Membership is a *lexical* fact that no analyser reports, so it has to be written down, and it is
shared: `verbal.py` needs النواسخ to exclude them, `nawasikh.py` will need the same set to claim
them.

Matching strips diacritics. CAMeL returns `كانَ`, the list is written `كان`, and the eval set's
gold lemmas are bare; comparing stripped forms lets all three be right. The surface form is a
fallback when there is no lemma, which is how hand-written test tokens and inserted tokens arrive.

#### `starter.py` is being emptied

`COVERT_AGENT` moved here, where فاعل belongs. `PREP_OBJECT` stays in `starter.py` until
`modifiers.py` lands and takes جار ومجرور with it. `default_registry()` now composes every rule
written so far and is what `apply_rules` uses by default.

#### The remaining five files

Shipped together, since they interlock: `nawasikh.py` claims exactly what `verbal.py` excludes,
and `modifiers.py` and `nominal.py` split the صفة/خبر pair between them.

**Result: 40 of 40 eval tokens correctly labelled, none wrong, none abstained.** End to end on the
real model — parse, arcs, covert insertion, rules — all thirteen sentences produce the gold
analysis.

26 rules, not the plan's "roughly forty". The difference is tier 2: حال, تمييز, بدل, توكيد,
عطف and مفعول مطلق have no tier-1 gold, and a rule written with nothing to verify it against is a
guess wearing a role name. They arrive with the sentences that test them.

| file | rules | roles |
|---|---|---|
| `verbal.py` | 9 | the verb's form, فاعل، نائب فاعل، مفعول به |
| `nominal.py` | 6 | مبتدأ، مبتدأ — مضاف، and all three خبر shapes |
| `nawasikh.py` | 5 | فعل ماضٍ ناقص، اسم/خبر كان، اسم/خبر إنّ |
| `particles.py` | 3 | حرف جزم، حرف نصب (two routes) |
| `modifiers.py` | 2 | صفة، مجرور |
| `idafa.py` | 1 | مضاف إليه |

#### Every discriminator is morphological, exactly as predicted

The claim made back when CATiB was chosen — that the parser narrows and morphology decides — is
now load-bearing code rather than an argument:

- **اسم كان vs خبر إنّ.** Both nominative, both hanging off a ناسخ. Only the **head's lemma**
  separates them, because the two families assign opposite cases. A test asserts that the same
  nominative token flips role when only the head changes.
- **صفة vs خبر.** In الكتاب الجديد مفيد both adjectives are nominative under the same noun on the
  same arc. **Definiteness** is the entire difference. A test flips one feature and asserts the
  answer inverts.
- **مضاف إليه.** Needs `state=construct` on the head *and* genitive on the dependent. This is the
  `stt=c` wiring CLAUDE.md named `idafa_01` to prove.
- **فاعل vs نائب فاعل.** Voice on the head, as recorded earlier.

Where a discriminator is missing the rules abstain rather than pick: an `unknown` state gives
neither صفة nor خبر, an `unknown` case gives neither فاعل nor مفعول به.

#### Placement decisions worth recording

Gold names some tokens by the **slot they fill**, not by their part of speech —
`حرف جر — خبر شبه جملة`, `ظرف مكان — خبر شبه جملة`, `مبتدأ — مضاف`. Those rules therefore live
with the role that knows the slot: the شبه جملة predicates in `nominal.py` rather than
`modifiers.py`, and the construct مبتدأ in `nominal.py` rather than `idafa.py`. Splitting them by
part of speech would leave two rules competing to name one token.

`particles.py` gives إنّ and لن the **same role string** `حرف نصب` through two separate rules. One
governs a verb's mood, the other a noun's case; the evidence differs and the hint text will too.

`starter.py` is gone — `COVERT_AGENT` moved to `verbal.py`, `PREP_OBJECT` to `modifiers.py`.

#### What the tests pin

The one that matters runs across **all thirteen** sentences and asserts that anything the rules do
label agrees with gold. Abstaining is fine; contradicting gold is not. Alongside it: `cas=unknown`
gets no role (CLAUDE.md's first trap), every sister of كان is excluded, a `PRD` dependent blocks
the verb rules, and `COVERT_AGENT` and `PASSIVE_AGENT` are both verified to outrank the general
`VERBAL_AGENT` — first-match-wins makes that ordering load-bearing rather than cosmetic.

---

# Morphology

Turning a typed sentence into words carrying case, state, voice, aspect and
mood. This is the layer that talks to CAMeL Tools, and the only one allowed
to know CAMeL's vocabulary.

## The CAMeL Tools wrapper

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

**Defect found later, during the command line.** `Token.form` held the *diacritized* stem, making `form`
and `diac` identical on every token. The model says `form` is the surface word and `diac` the
vowelled one. `form` is now the segment with marks stripped, `diac` is CAMeL's segment as
written, and on a backoff analysis `diac` is `None` rather than echoing the bare surface as
though it had been vowelled.

`form` is still derived
from the *chosen analysis* — `strip_diacritics(stem_diac)` — not from what the student typed. When
CAMeL's winning reading spells the word differently, the difference survives the stripping, and
the student gets a word back that they did not type. `nasikh_inna_01` is a live case: the student
types **إن**, BERT's top reading is `أَنَّ`, and the token comes back as **أن** — the hamza has
moved from under the alef to over it. The role assigned is correct (`حرف نصب`); only the surface
is wrong.

It is not cosmetic. The schema documents `form` as the word as typed and the UI is meant to show
the student their own sentence, so this silently rewrites their input. It also means any
evaluation matching produced tokens to gold by surface form scores this token as a miss on both
sides. Not fixed here — the fix is to carry the typed word through and use it for `form`, which
is the same plumbing the diacritics work just added, and it belongs in its own change.

### What the analyzer actually does to the eval set

Not a deviation — a measurement, recorded because it makes the rule engine and the confidence layer bigger than they look.

> **Superseded.** Every row below was measured under MLE. The disambiguator is now BERT and the
> fixture was re-recorded against it, so three of the four no longer hold. Kept because this table
> is the evidence that motivated the switch; the current column is what is true today.

| sentence | under MLE (then) | under BERT (now) |
|---|---|---|
| `nasikh_inna_01` | إن ranks `pos=abbrev` first at 1.0; `إِنَّ` (`verb_pseudo`) is 5th at 0.60 | `conj_sub` readings take 1–3 at 1.0; `إِنَّ` is 4th at 0.9993 and `abbrev` last at 0.69 |
| `verbal_passive_01` | active كَتَبَت wins; passive كُتِبَت is 3rd at 0.92 | active still wins at 1.0; passive is **2nd** at 0.9283 |
| `nominal_single_predicate_01` | الشمس comes back `case=gen` | `case=nom` — **correct** |
| `verbal_overt_agent_01` | الرجل comes back `case=acc` | `case=nom` — **correct** |

MLE disambiguates each word out of context, so case on short sentences was often wrong and rank 1
was not trustworthy. That is what the BERT switch fixed; both surviving rows are cases where the
bare string really is ambiguous and no disambiguator can help.

---

## Choosing a reading: BERT rather than frequency

Before, we installed `disambig-mle-calima-msa-r13` and later tested all passed, so the morphology
layer looked finished. It was not. Running the **whole pipeline on real morphology** rather than
on the eval set's gold features told a different story:

| morphology | correct | **wrong** | abstained | of |
|---|---:|---:|---:|---:|
| gold — what the tests use | 40 | **0** | 0 | 40 |
| MLE — what a live demo uses | 8 | **6** | 27 | 41 |
| **BERT** | **29** | **4** | 8 | 41 |

**On the denominators, since they differ.** The gold row counts the 40 tokens in
`data/eval/sentences.json`. The other two count *produced* tokens, and there are 41 because on
real morphology `verbal_passive_01` gains a covert pronoun that does not belong. Comparing 40 to
41 is comparing two different populations. Everything measured after this section uses one scheme
and states it: walk the 40 gold tokens, match each to the produced token with the same surface
form, and report spurious produced tokens separately instead of folding them in.

The gold row is what every test in the suite measures, and it is honest about the *rules*. It says
nothing about what a student typing a sentence would see, which is the middle row: wrong about one
word in seven, silent about two in three. The problem was that the disambiguator was MLE, which disambiguates each word in isolation and cannot see the verb
in the sentence. This caused it to send back wrong diactritics and wrong case features, which the rules then misread.

**Every one of MLE's errors was a case error, and every one disappeared under BERT.**

    الرجل   MLE acc ✗ → BERT nom ✓   فاعل
    اليوم   MLE acc ✗ → BERT nom ✓   اسم كان
    كتاب    MLE gen ✗ → BERT nom ✓   مبتدأ
    الطالب  MLE nom ✗ → BERT gen ✓   مضاف إليه
    جديد    MLE gen ✗ → BERT nom ✓   خبر
    الدرس   MLE gen ✗ → BERT acc ✓   مفعول به

The reason is structural rather than a matter of model quality: **MLE disambiguates each word in
isolation.** On يأكل الرجل السمك it picks الرجل's commonest reading with no idea a verb precedes
it. BERT reads the sentence. Undiacritized الرجل is genuinely three words — الرجلُ، الرجلَ، الرجلِ —
and nothing in the word itself can choose between them.

`CamelMorphology` now takes a `kind`, defaults to `bert`, and honours `$SIBAWAYH_DISAMBIGUATOR`.
`mle` stays reachable for environments where 445MB is too much, with a docstring saying plainly
that its case output cannot be trusted on short input. Both classes share an interface, so
`analyze` is unchanged and nothing downstream moved.

### What this did not fix, and why it is not the disambiguator's fault

The 4 remaining wrong answers are all one sentence — `verbal_passive_01`, where BERT reads كتبت as
active كَتَبَت "she wrote the article" and inserts a covert هي. That is a real reading of
undiacritized كتبت, already recorded as the one place the model and the guidelines disagree.

Most of the 8 abstentions come from `mood`. **Both** disambiguators return `mod='u'` on imperfect
verbs. يقرأُ /
يقرأَ / يقرأْ are spelled identically, so neither model can tell, and both correctly decline.

That is not a morphology problem at all. **The particle determines the mood**: لم *makes* the verb
jussive, which is the عامل doing exactly what the tradition says it does. So this is the parser's job. Recovering it belongs in
`particles.py` as syntax informing morphology.

### Verb classification splits cleanly by tense

Measured on the eval set through the real pipeline:

| | correct | why |
|---|---|---|
| ماضٍ | **2 of 3** | fails only on كتبت, where the voice is genuinely ambiguous |
| مضارع | **0 of 4** | every one has `mood=unknown`, so every rule declines |

Not a rule bug. The three features a verb's name is built from behave very differently:

* **aspect** — always reliable, because ماضٍ and مضارع differ in the word's *shape*
* **voice** — usually reliable, fails on forms that really are ambiguous
* **mood** — never available. And frankly, not needed here. It lives in a final short vowel (يقرأُ / يقرأَ / يقرأْ) that
  undiacritized text does not carry, and all five candidate analyses come back `mod:u`. There is
  nothing to rank, so no disambiguator can help.

CAMeL's behaviour here is exactly backwards from useful, and both disambiguators do it: on a
**ماضٍ**, where mood is grammatically inapplicable, it confidently returns `mod:i`; on a
**مضارع**, where mood is the whole question, it returns `mod:u`. Arguably `na` would be right on
the perfect — that is the "not applicable" value the schema has — and returning `indicative`
instead is what made the priority-tie bug below possible.

Three of the four failing verbs are recoverable without any model: لم and لن *assign* the mood,
and an ungoverned مضارع is مرفوع by default. That would take المضارع from 0 of 4 to 3 of 4. If
nothing is governing it, it is indicative.

### Built: the mood comes from the عامل

المضارع went **0 of 4 → 3 of 4**, and overall on real morphology **29 → 34 correct, 8 → 3
abstained**.

Done without a new stage and without writing morphology back onto tokens. The verb rules accept a
governing particle as an *alternative* to a reported mood; nothing mutates `feats`.

* A reported mood is **never overridden**. Syntax fills a gap; it does not outrank morphology that
  spoke.
* `MOOD_GOVERNORS` maps each mood to the kind of عامل that assigns it, with `None` for المرفوع —
  indicative is precisely the *absence* of a ناصب or جازم, so the default is earned by finding
  none rather than assumed.
* The governor is looked for **both** as the verb's head and as the token immediately before it.
  Under Sibawayh convention the جازم heads the verb, but relying on the arc alone would turn a
  parser slip into a confident مرفوع.

`particles.py` needed the mirror change: `JUSSIVE_PARTICLE` required its verb to *report* the
jussive, which never happens on undiacritized input, so لم went unrecognised on exactly the
sentences students type.

**Evidence records how the mood was settled** — `mood=jussive` when the analyzer read it, versus
`mood=jussive_from_governor` plus `governed_by=jussive_particle` when the tree supplied it. Those
are different claims, and the hint text for the second one names the particle, which is the lesson.

Two problems faced:

**Requiring `aspect is IMPERFECT` broke it on gold.** Gold sets aspect *or* mood, never both, so
an unset aspect has to be acceptable and only an explicitly perfect verb is disqualified. The same
shape as the priority-tie bug — gold-shaped inputs are not analyser-shaped ones.

**"No head" is not the test for indicative.** A مضارع can have a head and still be مرفوع: in
محمد يقرأ الكتاب it hangs off the مبتدأ. And `prc1` carries `li_jus`/`li_sub`, so a مضارع can be
governed by an *attached* لام with no separate particle token at all. That case is untested — no
tier-1 sentence has one.

The fourth verb, in `nominal_verbal_predicate_01`, was never a mood problem: it is a خبر, and
naming it خبر — جملة فعلية rather than فعل مضارع مرفوع is what gold asks for. It was recorded here
as failing for an undiagnosed reason; re-measured, the sentence comes out complete and correct on
real morphology, bare or vowelled. Nothing was fixed deliberately — the مبتدأ work below is what
unblocked it, since the خبر rules ask whether their head is the مبتدأ.

### Position stands in for an unreadable case at the root

**37 correct, 3 wrong, 1 abstained** of 41 produced tokens on real morphology, from 34/4/3.
(Under the gold-token scheme adopted above, the same run is 36 right, 2 wrong, 2 abstained of 40,
plus one spurious pronoun and one form mismatch. Same measurement, stated two ways.)

All of these are **bare, undiacritized input** — the sentences as the eval set writes them. That
is still what bare input scores today; nothing since has changed this path. The 39 right / 0 wrong
recorded in the typed-diacritics entry is the same thirteen sentences with the vowels supplied,
which is a different input rather than a later improvement to this one.

`TOPIC` required `case is NOM`. Bare proper nouns break that: محمدٌ / محمدًا / محمدٍ are spelled
identically, so محمد comes back `unknown` — and it took its whole clause with it, because the خبر
rules ask whether their head is the مبتدأ. Two tokens silenced by one unreadable ending.

Under Sibawayh convention the مبتدأ **is** the first token; that is exactly what `arcs.py`
re-roots the tree to guarantee. So position is not a heuristic here, it is the convention, and a
root nominal is the مبتدأ whether or not the analyser could read its ending.

`TOPIC_CASES` allows `nom`, `unknown` and unset — and **refuses `acc` and `gen`**. That refusal is
the point of listing cases rather than deleting the check: الكتابَ قرأ محمد fronts an object, and
that accusative first word is a مفعول به. Same principle as the mood work above — fill silence,
never contradict morphology that spoke.

Evidence distinguishes the two: `case=nom` when read, `case_unreadable_position_decides` when
inferred, so a hint can say *this starts the sentence* rather than implying an ending we never saw.

**Still open.** `VERBAL_AGENT` has the identical problem and has not had the identical fix — محمد
in `jussive_lam_01` is the last abstention for exactly this reason. Left alone deliberately: a
فاعل is not positionally determined the way a مبتدأ is, so the same argument does not transfer and
would need its own.

### The fixture was re-recorded against BERT

`tests/data/camel_analyses.json` held MLE output, so the offline tests described a configuration
we no longer ship. Re-recorded; `pytest -m camel` is green again.

Two tests changed with it, and both had been **asserting MLE's mistakes**:

* `test_idafa_carries_construct_state` expected `case=gen` on كتاب in كتاب الطالب جديد. It is the
  مبتدأ and gold says nominative. BERT returns nominative; the test now asserts that.
* `test_top_analysis_can_be_wrong` used إن coming back `pos=abbrev`. BERT reads it `conj_sub`, so
  that example is gone. The principle still holds and the test now uses كتبت, where the passive
  reading gold wants really does sit below rank 1.

### Two rule fixes that came out of running on real data

**إنّ comes back as `conj`.** BERT tags it `conj_sub`, which the collapse table maps to `conj`,
where `nawasikh.py` and `particles.py` both expected `part`. The reading is defensible — أنّ really
does subordinate — so both files now accept either, and the lemma does the actual identifying.
Without this the whole of `nasikh_inna_01` abstained.

---

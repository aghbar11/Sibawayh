# Sibawayh (سيبويه)

My first step into Arabic NLPs.

**Sibawayh** is an Arabic **Irab** **إعراب** analysis and tutoring system for Modern Standard Arabic.

Given a sentence, Sibawayh does more than predict grammatical labels. It builds a structured analysis of the sentence, derives traditional Arabic grammatical roles from that structure, explains the reasoning behind those decisions, and can guide a student toward the answer instead of simply revealing it.

The system combines **Arabic morphological analysis, dependency parsing, deterministic grammatical rules, structural validation, and optional LLM-based explanation** into one pipeline.

The central design principle is:

> **Machine learning provides evidence; grammar rules make the decision; the LLM explains it.**

The system therefore never asks a language model to determine the underlying إعراب.


---

## What Sibawayh Does

Arabic Irab depends on two things: the sign of the last word, and its position in the sentence. We obtain the sign from several techniques: CAMeL analyzer, disambiguator, or the student themselves. We obtain the words position from CATiB dependency tree parser. More information in the rest of this README.

For an input such as:

```text
الشمس مشرقة
```

the system progressively turns raw text into a structured grammatical analysis:

```text
Raw Arabic
    │
    ▼
Orthographic normalization
    │
    ▼
Morphological analysis
(CAMeL Tools)
    │
    ▼
Dependency parsing
(CATiB parser)
    │
    ▼
Arc normalization
(CATiB → Sibawayh conventions)
    │
    ▼
Covert-pronoun insertion
(ضمير مستتر)
    │
    ▼
Iʿrāb rule engine
    │
    ▼
Sentence-level validation
    │
    ▼
Arabic iʿrāb rendering
    │
    ├── deterministic templates
    │
    └── optional Gemini explanation
    │
    ▼
Interactive tutor / CLI / Web UI
```

Each stage has a deliberately narrow responsibility. Morphology does not assign iʿrāb roles. The parser does not decide grammatical roles. The rule engine does not generate prose. The LLM does not analyze the sentence.

That separation is what makes the system testable, peer-reviewed if you will.

---

## Project structure

The repository is organized around the stages described above:

```text
Sibawayh/
│
├── sibawayh/
│   ├── normalize.py
│   │   └── Arabic orthographic normalization
│   │
│   ├── morphology.py
│   │   └── CAMeL Tools integration and feature translation
│   │
│   ├── diacritics.py
│   │   └── user-supplied diacritic matching
│   │
│   ├── schema.py
│   │   └── Pydantic data model for the pipeline
│   │
│   ├── parsers/
│   │   ├── base.py
│   │   │   └── parser abstraction
│   │   └── catib.py
│   │       └── CATiB parser backend
│   │
│   ├── arcs.py
│   │   └── dependency-tree normalization
│   │
│   ├── covert.py
│   │   └── covert-pronoun insertion
│   │
│   ├── rules/
│   │   ├── verbal.py
│   │   ├── nominal.py
│   │   ├── nawasikh.py
│   │   ├── idafa.py
│   │   ├── modifiers.py
│   │   └── particles.py
│   │       └── deterministic iʿrāb rules
│   │
│   ├── validate.py
│   │   └── sentence-level consistency checks
│   │
│   ├── renderers/
│   │   ├── template.py
│   │   ├── evidence.py
│   │   ├── reasons.py
│   │   ├── inflection.py
│   │   ├── signs.py
│   │   ├── phrases.py
│   │   ├── hinting.py
│   │   ├── suggest.py
│   │   ├── faithful.py
│   │   └── gemini.py
│   │       └── deterministic and LLM-backed explanations
│   │
│   ├── hints.py
│   │   └── three-stage hint ladder
│   │
│   ├── tutor.py
│   │   └── conversational tutoring and answer withholding
│   │
│   ├── pipeline.py
│   │   └── complete analysis pipeline
│   │
│   ├── api.py
│   │   └── FastAPI application
│   │
│   ├── cli.py
│   │   └── command-line interface
│   │
│   └── web/
│       └── index.html
│           └── browser interface
│
├── data/
│   ├── eval/
│   │   └── hand-verified evaluation sentences
│   └── ldc/
│       └── licensed PADT data; not committed
│
├── scripts/
│   └── model/data preparation utilities
│
├── tests/
│   └── unit and integration tests
│
├── docs/
│   └── design and implementation notes
│
├── pyproject.toml
└── README.md
```


## Evaluation

### What it is measured against

`data/eval/sentences.json` — **13 hand-verified sentences, 40 tokens**, each token carrying its
gold Irab role, its case, and its inflectional sign.

Small on purpose. Every sentence is checked by hand, and every one exercises a construction the
rules claim to handle: فاعل، نائب فاعل، مفعول به، مبتدأ وخبر، إضافة، كان وأخواتها، إنّ وأخواتها،
لم الجازمة، and nominal sentences with prepositional and verbal predicates.

Every number below is the **whole pipeline**, end to end, on those sentences.

### Two measurements that answer different questions

| run on | asks |
|---|---|
| **gold morphology**, taken from the eval file | are the *rules* right? |
| **real morphology**, from CAMeL, live | is what a *student* sees right? |

This distinction is the most important thing in this section. The test suite runs on gold, so a
green suite says the rule engine is correct — and says nothing at all about what the demo does.

**On gold morphology the rule engine scores 40 of 40. None wrong, none abstained.** 

The rest of this section is the real-morphology number, and how it
got there.

### How the live number moved

Bare undiacritized input — the sentences exactly as the eval set writes them. Counted over 41
produced tokens, because on real morphology `verbal_passive_01` gains a covert pronoun that does
not belong.

| | right | wrong | abstained | what changed |
|---|---:|---:|---:|---|
| MLE disambiguator | 8 | 6 | 27 | where it started |
| BERT disambiguator | **29** | 4 | 8 | reads the whole context, not the word |
| mood from the governor عامل | **34** | 4 | 3 | the particle assigns what the vowel would have |
| position decides the Mobtada مبتدأ | **37** | 3 | 1 | an unreadable ending stops silencing a clause |

Then we put an option for the student to vowel their word. Counted over the 40 gold tokens, the scheme
used from here on:

| input | right | wrong | abstained |
|---|---:|---:|---:|
| as typed, bare | 37 | 3 | 1 |
| **fully vowelled** | **39** | **0** | **1** |

Note the wrong column. Getting it to **zero** matters more than getting the right column to 39,
because a confident wrong إعراب shown to a beginner is the failure that would kill the product.
The four narratives below are each about removing a *cause* of silence without introducing a
guess.

---

#### 8 → 29 · Read the sentence, not the word

**TO UNDERSTAND CATiB FORMALISM, PLEASE REFERE TO doc/REFERENCES**

The first disambiguator was MLE, which picks each word's commonest reading **in isolation**.

Every single one of its errors was a **case** error, and every one disappeared under CAMeL's BERT
disambiguator:

```text
الرجل   MLE acc ✗ → BERT nom ✓   فاعل
اليوم   MLE acc ✗ → BERT nom ✓   اسم كان
كتاب    MLE gen ✗ → BERT nom ✓   مبتدأ
الطالب  MLE nom ✗ → BERT gen ✓   مضاف إليه
جديد    MLE gen ✗ → BERT nom ✓   خبر
الدرس   MLE gen ✗ → BERT acc ✓   مفعول به
```

This is structural, not a matter of model quality. Undiacritized الرجل is genuinely three
different words — الرجلُ، الرجلَ، الرجلِ — and nothing inside the word can choose between them. In
يأكل الرجل السمك the verb standing before it is the evidence, and MLE cannot see it.

MLE remains reachable through `SIBAWAYH_DISAMBIGUATOR=mle` for environments where 445 MB is too
much, with a docstring saying plainly that its case output cannot be trusted on short input.

#### 29 → 34 · The particle assigns the mood

المضارع (imperfect verb) scored **0 of 4**. Every imperfect verb came back with `mood=unknown`, so every verb rule
declined.

Both disambiguators do this, and both are right to. Mood lives in a final short vowel — يقرأُ /
يقرأَ / يقرأْ are spelled identically — and undiacritized text does not carry it. No model can
recover a vowel that was never typed.

To solve this problem, we utilize the governor of the verb. **لم *makes* the verb jussive** — the governor عامل doing
exactly what the tradition says it does. So the verb rules now accept a governing particle as an
*alternative* to a reported mood, and المضارع went **0 of 4 → 3 of 4**.

Three constraints keep this from being a guess:

* **A reported mood is never overridden.** Syntax fills a gap; it does not outrank morphology that
  spoke.
* **المرفوع Marfoo3 is earned, not assumed.** Indicative is precisely the *absence* of a Nasib ناصب or Jazim جازم, so
  the rule has to look for one and fail to find it.
* **The governor is looked for as both the head and the preceding word.** Relying on the arc alone
  would turn a parser slip into a confident مرفوع.

And the evidence records which of the two happened — `mood=jussive` when the analyzer read it,
versus `mood=jussive_from_governor` plus `governed_by=jussive_particle` when the tree supplied it.
Those are different claims, and the hint generated from the second one names the particle, which
is the actual lesson.

#### 34 → 37 · Position decides the مبتدأ

The `TOPIC` rule required `case=nom`. Bare proper nouns break that: محمدٌ / محمدًا / محمدٍ are
spelled identically, so محمد comes back `unknown`.

Worse, it took its whole clause with it — the خبر rules ask whether their head is the مبتدأ, so
one unreadable ending silenced two tokens.

Under Sibawayh's convention the مبتدأ **is** the first token; that is exactly what arc
normalization re-roots the tree to guarantee. So position here is not a heuristic standing in for
grammar, it *is* the convention.

The fix was to list the acceptable cases rather than delete the check. `nom`, `unknown` and unset
are allowed — and **`acc` and `gen` are still refused**. الكتابَ قرأ محمد fronts an object, and
that accusative first word is a مفعول به, not a مبتدأ. Same principle as the mood work: fill
silence, never contradict morphology that spoke.

Evidence distinguishes the two again: `case=nom` when the ending was read, versus
`case_unreadable_position_decides` when it was not — so a hint can say *this word starts the
sentence* instead of implying an ending nobody ever saw.

#### 36 → 39 · Use the student's own diacritics

CAMeL's database operates on undiacritized forms, so the analyzer receives the same input whether
the student typed كتبت or كُتِبَتْ. Anything they marked is discarded before analysis begins — and
what they marked is precisely the إعراب.

We recover it. Not by exact match, since partial vowelling is the normal case, but by
testing **compatibility** position by position:

* where the student marked nothing, there is no constraint
* where the *candidate* marks nothing, it is the vaguer of the two and cannot contradict
* where both marked, the student's mark must be among the candidate's

Compatible candidates are promoted, preserving CAMeL's ordering among them. **Nothing is
invented** — the reading was already in the list; only the order changes. A vowelling matching
nothing leaves the order untouched, because reordering on that basis would be a guess.

Two traps, both found by measuring rather than by reasoning:

* CAMeL's **backoff analysis carries no vowels at all**, so it is compatible with everything and
  outranked the genuine readings, stripping الدرس of its features entirely. A candidate now has to
  *state* a vowelling before it can match one.
* CAMeL writes الدَرْسَ where a student writes الدَّرْسَ, omitting the shadda of the lam shamsiyya.
  That mismatch rejects every candidate — harmless only because rejecting everything leaves
  CAMeL's own ranking in place. Worth revisiting if a sentence turns up where it costs something.


### Structure, checked separately

Arc normalization is measured on its own. The CATiB → Sibawayh re-rooting is checked against all
**thirteen** hand-verified trees, including إنّ, jussive لم, nominal sentences with prepositional
predicates, and nominal sentences with verbal predicates. All thirteen match the expected iʿrāb
tree after the transformation.

---

## The Core Idea: Separate Attachment From Grammar

A dependency parser answers a structural question:

> **What does this word attach to?**

Traditional Arabic إعراب asks a different question:

> **What grammatical role does this word have, and why?**

Sibawayh keeps these two concepts separate throughout the pipeline.

Every token therefore has both:

```text
parser_label   → what the parser called the relation
head           → which token governs it
irab_role      → the grammatical role derived by Sibawayh's rules
```

For example, the parser might identify a word as `SBJ`. Sibawayh does not simply display `SBJ` as `فاعل`. Instead, the rule engine considers the dependency structure (which word depends on which), morphology, position, and other evidence before deriving the Arabic grammatical role.


---

## How each stage works

The rest of this file walks the pipeline in the order a sentence travels through it. Each stage is
a pure function over the token list, and each one is described together with the design decision
that shaped it.

---

### Input normalization

The first stage cleans the raw Arabic text before any linguistic analysis takes place.

The normalizer removes orthographic noise such as:

* tatweel (`ـ`)
* zero-width characters
* bidirectional control characters
* unnecessary recitation marks
* certain non-Arabic look-alike characters (like Farsi or Urdu alphabet)
* other typographical artifacts

Normalization such as Alef Maksoura الف مقصورة and other presentation differences.

An important design decision is that normalization distinguishes between **lossless cleanup** and **lossy unification**.

Lossless cleanup removes things that do not represent grammatical information.

Lossy transformations, such as:

```text
أ إ آ → ا
ى → ي
ة → ه
```

are disabled by default because they destroy information that can actually matter to Arabic grammar.

For example, converting:

```text
إنّ
```

to:

```text
ان
```

would erase information that distinguishes different grammatical constructions.

Therefore the default normalization is intentionally conservative: **if the user supplied linguistic information, keep it.**

The normalization layer is implemented as pure standard-library functions, making it independent of CAMeL Tools and easy to test.

---

### Morphological analysis

After normalization, Sibawayh uses **CAMeL Tools** to obtain morphological analyses for the sentence.

CAMeL provides information such as:

* lemma
* root
* part of speech
* gender
* number
* person
* case
* mood
* aspect
* voice
* definiteness/state
* clitic information
* diacritized candidate readings

However, CAMeL's output uses compact feature codes such as:

```text
asp=p
cas=u
stt=c
enc0=3ms_poss
```

Sibawayh does not allow these codes to leak into the rest of the system.

`morphology.py` is deliberately the **only module that knows CAMeL's feature vocabulary**. It translates CAMeL's representation into Sibawayh's own schema.

For example:

```text
cas=n  → case=nom
cas=a  → case=acc
cas=g  → case=gen
```

**To see which each does in detail, refere to docs/REFERENCES.**

This gives the rule engine a stable representation that is independent of CAMeL's implementation details.

#### Three kinds of missing information

Sibawayh carefully distinguishes three different states:

```text
None       → this layer has not analyzed the value yet

"null"     → the value is not applicable

"unknown"  → the analyzer considered it but could not determine it
```


For example, a verb does not have a noun-style case, so its case can legitimately be `"null"`.

But if CAMeL cannot determine the case of an ambiguous noun, the value becomes `"unknown"`.

`"unknown"` is therefore an **abstention signal**, not an ordinary missing value. Collapsing `"null"` and `"unknown"` would make uncertain analyses appear more confident than they really are.

---

### Candidate readings

Arabic without diacritics is highly ambiguous.

For example:

```text
كتبت
```

can correspond to different readings such as:

```text
كَتَبَت
كُتِبَت
كَتَبْتِ
```

CAMeL returns multiple candidate analyses with scores.

This ranking comes from CAMeL's **disambiguator**, not the morphological analyzer
alone, the analyzer enumerates every possible reading for a word, and the
disambiguator scores/orders them in context. Sibawayh defaults to CAMeL's BERT
unfactored MSA disambiguator; an MLE fallback stays reachable via
`SIBAWAYH_DISAMBIGUATOR=mle`, though its case handling is weaker.

```text
Token
 ├── chosen analysis
 └── alternatives[]
       ├── candidate
       ├── candidate
       └── candidate
```

The score itself is not treated as an absolute probability. What matters is the relative difference between competing analyses of the same token.

This becomes useful later when deciding whether an analysis is sufficiently reliable to use.

---

### Dependency parsing

Once morphology has produced token information, Sibawayh obtains the sentence's dependency structure using a **CATiB dependency parser**.

The parser is what gives the sentence its tree form, indicating which word governs or affects which.

It provides:

```text
head indices
parser labels
attachment confidence
```


The parser is exposed through a common interface so that different dependency formalisms can eventually be supported without changing the rest of the system.

Currently, CATiB is the implemented backend.

The parser architecture is based on CAMeL Lab's **CAMeLBERT CATiB biaffine dependency parser**.

---

### The parser abstraction

The parser layer is intentionally isolated behind a common interface.

The parser provides a `Parse` representation containing structural information rather than returning Sibawayh-specific grammatical roles.

The parser interface also declares its dependency formalism.

This allows the rest of the system to ask:

```text
"What formalism produced this tree?"
```

instead of assuming that every parser behaves like CATiB.

As a result, adding another parser backend primarily requires:

1. implementing the parser interface;
2. declaring its formalism;
3. implementing the corresponding arc normalization;
4. testing the result against gold trees.

The rest of the iʿrāb engine does not need to know which parser produced the tree.

---

### Arc normalization

A dependency tree is not automatically an iʿrāb tree.

Different Arabic treebanks encode grammatical relationships differently, so Sibawayh introduces an explicit **arc normalization** layer.

The normalizer is aware of the parser's formalism:

```text
CATiB
UD
...
```

and converts its dependency structure into the structural conventions expected by Sibawayh.

This is important because the conversion is not merely a label translation.

For CATiB, most internal arcs already agree with the desired iʿrāb structure, that's why it was prefered over UD:

* `OBJ` already represents the relevant object/prepositional attachment
* `IDF` already captures the possessor → possessed relationship
* `PRD` already gives the appropriate structure for extended copular constructions
* `MOD` attaches modifiers to what they modify

The major systematic difference is the **root**.

CATiB roots certain sentences at the predicate, whereas Sibawayh's iʿrāb representation roots the sentence at its first word.

Therefore Sibawayh performs a mathematical **re-rooting operation** on the dependency tree.

The operation walks the path from the desired root to the existing root and reverses only those arcs.

No unrelated attachment is changed.

The re-rooting has been checked against the project's thirteen hand-verified Tier-1 evaluation sentences, including cases involving:

* `إنّ`
* jussive `لم`
* nominal sentences with prepositional predicates
* nominal sentences with verbal predicates

All thirteen match the expected iʿrāb tree after the CATiB → Sibawayh transformation.

UD and PADT normalization are intentionally not implemented yet. The architecture supports them. It is implemented so that we can train a parser using UD datasets (since most of CATiB datasets are not commercial).

---

### Covert pronouns — ضمير مستتر

Dependency treebanks annotate words that exist in the input.

Arabic grammar does not always work that way.

Consider:

```text
يقرأ الكتاب
```

The sentence has a subject even though no overt subject token appears.

The subject is a **ضمير مستتر**.

Sibawayh therefore inserts covert pronouns into the dependency representation when the structure indicates that a verb requires an implicit agent.

The inserted token receives:

* person
* gender
* number

from the verb's morphology, together with:

```text
case = nom
```

and is marked:

```text
inserted = true
```

so that it can be distinguished from words actually supplied by the student.

#### Conservative insertion

The system deliberately prefers **not inserting a pronoun** when there is a plausible overt subject.

An overt subject can be identified using redundant evidence:

```text
parser_label == SBJ
```

or:

```text
case == nominative
```

An unknown case also blocks insertion because uncertainty should lead to abstention rather than a fabricated grammatical claim.

This is intentionally conservative:

> A missing explanation is preferable to confidently showing a student a pronoun that does not exist.

The insertion stage also carefully renumbers tokens and updates heads after insertion so that the dependency structure remains valid.

---

### The iʿrāb rule engine

This is where Sibawayh's actual grammatical reasoning happens. Here is the real thing.
I'rab depends on the type of the word (noun, verb, etc.), the sign at the word's end, and its position in the sentence. We have all of that, we just need the Nahw (Irab) rules.

The rule engine takes:

```text
token
head
sentence structure
morphological features
parser evidence
```

and derives:

```text
irab_role
rule_id
evidence
```

A rule conceptually looks like:

```text
(token, head, sentence)
        ↓
     predicate
        ↓
(irab_role, rule_id, evidence)
```

Rules are registered with priorities, and the highest-priority matching rule wins.

If no rule matches:

```text
irab_role = None
```

This is deliberate.

**No rule firing means abstention, not guessing.**

The rule engine is the only layer allowed to write `irab_role`.

#### Rule categories

The rule inventory is organized into separate grammatical areas:

```text
rules/
├── verbal.py
├── nawasikh.py
├── nominal.py
├── idafa.py
├── modifiers.py
└── particles.py
```

These cover constructions such as:

* verbal sentences جمل فعلية
* فاعل
* نائب فاعل
* مفعول به
* nominal sentences جمل اسمية
* مبتدأ
* خبر
* كان وأخواتها
* إنّ وأخواتها
* إضافة
* مضاف إليه
* صفات/modifiers
* prepositions
* grammatical particles

More rules should be added in the future.

---

### Evidence instead of black-box decisions

Every successful rule records the evidence that caused it to fire.

For example, a token might accumulate evidence such as:

```text
head_pos=verb
case=nom
parser_label=SBJ
```

The evidence is stored as structured observations rather than generated prose.

This is important because the same evidence is later reused by several parts of the system:

```text
Rule engine
     │
     ├── validation
     ├── deterministic explanation
     ├── hint generation
     └── LLM grounding
```

The system therefore does not need to ask an LLM:

> "Why is this word a فاعل?"

The rule already knows why.

The LLM, if used, is only asked to explain those existing reasons more naturally.

---

### Rendering the iʿrāb

Once the analysis has survived validation, it can be turned into Arabic prose.

Rendering is kept separate from analysis.

A renderer receives the finished tokens and returns prose:

```text
analysis → Arabic explanation
```

It cannot modify the tokens or assign new grammatical roles.

This gives Sibawayh two kinds of renderer:

```text
Deterministic renderer
        │
        └── offline, predictable templates

LLM renderer
        │
        └── more natural explanations
```

The renderer interface is deliberately narrow: it produces strings rather than analysis objects, preventing a rendering backend from silently modifying the grammatical analysis.

---

### Deterministic Arabic rendering

The template renderer builds the actual iʿrāb from structured information.

Separate rendering modules handle concepts such as:

```text
evidence
reasons
inflection
signs
phrases
```

This allows Sibawayh to produce correct, deterministic Arabic without requiring an LLM.

For example, the system can construct the difference between:

```text
مبتدأ مرفوع وعلامة رفعه الضمة الظاهرة على آخره
```

and a corresponding analysis with a different grammatical case or inflectional sign.

This deterministic layer is also the system's fallback.

---

### Optional Gemini rendering

Sibawayh can optionally use Google's Gemini models to make the explanations more natural, conversational, and back-and-forth with the student.

The important point is that Gemini does **not** analyze the sentence.

The model receives an already-computed analysis and is asked to explain it.

Conceptually:

```text
Rules
  ↓
Correct iʿrāb
  ↓
Evidence
  ↓
Gemini
  ↓
More natural Arabic explanation
```

not:

```text
Sentence
  ↓
Gemini
  ↓
iʿrāb
```

This distinction prevents the LLM from becoming the source of truth.

The Gemini backend is implemented directly over HTTP rather than through an SDK, keeping the dependency surface small. The API key is read from `GEMINI_API_KEY` or `.env`, with the environment taking precedence.

The renderer also handles network and model failures gracefully.

If Gemini fails, the system falls back to the deterministic template instead of returning an error or an invented explanation.

---

### The hint system

The project is designed as a tutor rather than merely an automatic iʿrāb generator.

When a student asks for help with a word, Sibawayh reveals the reasoning gradually.

Every analyzed token can have a three-step hint ladder:

```text
1. Question
2. Reasoning
3. Answer
```

For example:

```text
1. ما علاقة هذه الكلمة بالتي قبلها؟

2. لأنها جاءت بعد مضاف، فهي مضاف إليه

3. مضاف إليه مجرور وعلامة جره الكسرة الظاهرة على آخره
```

The ladder is not manually authored for every sentence.

It is generated from the evidence already stored by the rule engine.

That means the tutor teaches from the same reasoning that produced the answer.

There is no separate "teaching logic" that can disagree with the grammar engine.

The hint system is also completely deterministic and works offline.

---

### Conversational tutoring

The hint ladder handles structured hints, but students may ask questions such as:

```text
لماذا ليست مبتدأ؟
```

or:

```text
أنا ما زلت لا أفهم.
```

Sibawayh has a separate conversational tutor for these cases.

The important design constraint is **answer withholding**.

Before the student explicitly asks to reveal the answer, the LLM does not receive the target word's:

* iʿrāb role
* case
* inflectional sign
* complete iʿrāb line

It receives enough information to guide the student, but not the answer itself.

This creates an architectural guarantee:

> The model cannot leak information that was never included in its prompt.

The generated response is also checked for leaks. If the model accidentally reveals the hidden role or case, the response is rejected and replaced with a safe fallback.

After the student chooses to reveal the answer, the restriction is removed and the tutor can freely explain it.

---

## Installing

The project uses Python 3.11+ and is packaged with `hatchling`.

The core dependency is:

```text
pydantic
```

Heavier dependencies are intentionally installed by phase:

```bash
pip install -e ".[morphology]"
```

installs CAMeL Tools.

```bash
pip install -e ".[parser]"
```

installs the parser stack, including PyTorch and SuPar.

```bash
pip install -e ".[api]"
```

installs FastAPI and Uvicorn.

For development:

```bash
pip install -e ".[dev]"
```

installs:

* pytest
* Ruff
* HTTPX for API testing

This keeps a morphology-only or rules-only development environment from unnecessarily installing the entire ML and web stack.

---

## Development

Run the standard test suite with:

```bash
pytest
```

Static checks:

```bash
ruff check .
```

The default test configuration deliberately excludes tests requiring heavyweight external assets:

```text
camel
parser
```

Those can be enabled explicitly when the corresponding models are available.

The repository also defines an `ldc` marker for tests that require the licensed PADT data.

---

## Licensed PADT data

The project also has a separate location for licensed PADT data:

```text
data/ldc/
```

This data is not committed to the repository.

PADT is distributed under an LDC license, so the project treats the data and anything derived from it separately from the ordinary source code.

The repository therefore uses environment/configuration gates for PADT-dependent functionality rather than silently assuming that the data is available.

This is also why the parser layer is designed to be swappable: the project should not be architecturally dependent on shipping a particular restricted training corpus.

---

## Where the rest is written down

| | |
|---|---|
| [`docs/SummarizedChanges.md`](docs/SummarizedChanges.md) | a plain-language account of what was built, and why |
| [`docs/CHANGES.md`](docs/CHANGES.md) | every decision that departs from the spec, with its reasoning |
| [`docs/changes/`](docs/changes/) | the same, split by pipeline component |

---

## Future Work

I'm currently planning to:
- Integrate an Arabic LLM (Jais, ALLaM, Fanar, etc.)
- Train a parser on UD Formalism. Training on CATiB was not applicable because of Licencing that prevents commercial use.

# Arc normalization — study notes

Scratch file. Delete when done.

Generated from `tests/data/catib_trees.json` and `data/eval/sentences.json`, so the numbers
here are the same ones the tests assert.

---

## How to read a `head` number

Each token is asked one question: **who governs you?** Th/e answer is another token's
**position number**, or `0` meaning *nobody — I am the root*.

`0` is never a position. Positions start at 1.

### The right-to-left trap

Token 1 is the **first word of the sentence** in Arabic reading order. Rendered right-to-left,
that word sits at the **right-hand end** of the line. Scanning the Arabic visually from the left
gives you the *last* token first.

This matters because i'rab's rule is *the root is the first word of the sentence* — first in
reading order, i.e. the rightmost on screen.

Every table below is ordered by position number, so you never have to judge it by eye.

---

## The one operation

**Re-root at token 1.**

1. Start at token 1. Follow *who governs me* upward until you reach the root. That chain is the **path**.
2. Reverse every arrow on the path.
3. Change nothing else.

Step 3 is the point: any attachment the parser got right is left alone.

---

## All thirteen sentences

### `verbal_overt_agent_01`

> يأكل الرجل السمك

CATiB root: token **1** — i'rab root: token **1**  (unchanged)

| position | word | CATiB head | i'rab head | moved |
|---:|---|---:|---:|---|
| 1 | يأكل | 0 (root) | 0 (root) | — |
| 2 | الرجل | 1 | 1 | — |
| 3 | السمك | 1 | 1 | — |

Path from token 1 to the CATiB root: 1 (already the root, nothing to reverse)

CATiB label reference: 1=ROOT, 2=SBJ, 3=OBJ

*Verb-initial, so CATiB and i'rab already agree. Re-rooting is a no-op.*

### `verbal_perfect_01`

> كتب الطالب المقالة

CATiB root: token **1** — i'rab root: token **1**  (unchanged)

| position | word | CATiB head | i'rab head | moved |
|---:|---|---:|---:|---|
| 1 | كتب | 0 (root) | 0 (root) | — |
| 2 | الطالب | 1 | 1 | — |
| 3 | المقالة | 1 | 1 | — |

Path from token 1 to the CATiB root: 1 (already the root, nothing to reverse)

CATiB label reference: 1=ROOT, 2=SBJ, 3=OBJ

*Aspect does not change tree shape in CATiB either. CATiB has one VRB tag for both aspects.*

### `verbal_passive_01`

> كتبت المقالة

CATiB root: token **1** — i'rab root: token **1**  (unchanged)

| position | word | CATiB head | i'rab head | moved |
|---:|---|---:|---:|---|
| 1 | كتبت | 0 (root) | 0 (root) | — |
| 2 | المقالة | 1 | 1 | — |

Path from token 1 to the CATiB root: 1 (already the root, nothing to reverse)

CATiB label reference: 1=ROOT, 2=SBJ

*Guidelines: 'For passive verbs (VRB-PASS), SBJ is the surface subject.' Voice lives in the POS tag, never the relation, so نائب فاعل stays the rule engine's call off morphology.*

### `nominal_single_predicate_01`

> الشمس مشرقة

CATiB root: token **2** — i'rab root: token **1**

| position | word | CATiB head | i'rab head | moved |
|---:|---|---:|---:|---|
| 1 | الشمس | 2 | 0 (root) | **yes** |
| 2 | مشرقة | 0 (root) | 1 | **yes** |

Path from token 1 to the CATiB root: 1 → 2

CATiB label reference: 1=SBJ, 2=ROOT

*Guidelines: 'the verbless complement/predicate (الخبر) heads the topic/subject (المبتدأ)'. i'rab roots at المبتدأ, so this arc is the one that moves.*

### `nominal_pp_predicate_01`

> العصفور في القفص

CATiB root: token **2** — i'rab root: token **1**

| position | word | CATiB head | i'rab head | moved |
|---:|---|---:|---:|---|
| 1 | العصفور | 2 | 0 (root) | **yes** |
| 2 | في | 0 (root) | 1 | **yes** |
| 3 | القفص | 2 | 2 | — |

Path from token 1 to the CATiB root: 1 → 2

CATiB label reference: 1=SBJ, 2=ROOT, 3=OBJ

*'The predicate of a nominal sentence can also be a preposition' — so the preposition roots the sentence. It already heads its object, which is the arc UD would invert and CATiB does not. Only the root moves.*

### `nominal_adv_predicate_01`

> الكتاب فوق الطاولة

CATiB root: token **2** — i'rab root: token **1**

| position | word | CATiB head | i'rab head | moved |
|---:|---|---:|---:|---|
| 1 | الكتاب | 2 | 0 (root) | **yes** |
| 2 | فوق | 0 (root) | 1 | **yes** |
| 3 | الطاولة | 2 | 2 | — |

Path from token 1 to the CATiB root: 1 → 2

CATiB label reference: 1=SBJ, 2=ROOT, 3=IDF

*CATiB has no adverb tag: 'Preposition-like nouns/adverbs such as أمام and فوق are considered NOMs', and 'idafa is also used to mark the objects of preposition-like nominal adverbs'.*

### `nominal_verbal_predicate_01`

> محمد يقرأ الكتاب

CATiB root: token **2** — i'rab root: token **1**

| position | word | CATiB head | i'rab head | moved |
|---:|---|---:|---:|---|
| 1 | محمد | 2 | 0 (root) | **yes** |
| 2 | يقرأ | 0 (root) | 1 | **yes** |
| 3 | الكتاب | 2 | 2 | — |

Path from token 1 to the CATiB root: 1 → 2

CATiB label reference: 1=SBJ, 2=ROOT, 3=OBJ

*SBJ not TPC: the topic 'is marked as SBJ if it is the same as the subject inside the complement; otherwise TPC'. Here it is the same. CATiB gives this the same tree as verb-initial 1(a) — i'rab does not, and word order is what separates them. Three tokens here, four in gold: the covert فاعل is inserted downstream.*

### `nasikh_kana_01`

> كان اليوم رائعا

CATiB root: token **1** — i'rab root: token **1**  (unchanged)

| position | word | CATiB head | i'rab head | moved |
|---:|---|---:|---:|---|
| 1 | كان | 0 (root) | 0 (root) | — |
| 2 | اليوم | 1 | 1 | — |
| 3 | رائعا | 1 | 1 | — |

Path from token 1 to the CATiB root: 1 (already the root, nothing to reverse)

CATiB label reference: 1=ROOT, 2=SBJ, 3=PRD

*'the topic/subject and complement/predicate are considered children of the incomplete verb with the relations SBJ and PRD'. Already i'rab-shaped.*

### `nasikh_inna_01`

> إن العراقيين قادرون

CATiB root: token **1** — i'rab root: token **1**  (unchanged)

| position | word | CATiB head | i'rab head | moved |
|---:|---|---:|---:|---|
| 1 | إن | 0 (root) | 0 (root) | — |
| 2 | العراقيين | 1 | 1 | — |
| 3 | قادرون | 1 | 1 | — |

Path from token 1 to the CATiB root: 1 (already the root, nothing to reverse)

CATiB label reference: 1=ROOT, 2=SBJ, 3=PRD

*'The same happens when a verb-like particle (إنّ وأخواتها) precedes the nominal sentence.' PADT attaches the topic under the predicate (I3rab Fig 11); CATiB agrees with i'rab instead, so nothing flips.*

### `jussive_lam_01`

> لم يقرأ محمد الكتاب

CATiB root: token **2** — i'rab root: token **1**

| position | word | CATiB head | i'rab head | moved |
|---:|---|---:|---:|---|
| 1 | لم | 2 | 0 (root) | **yes** |
| 2 | يقرأ | 0 (root) | 1 | **yes** |
| 3 | محمد | 2 | 2 | — |
| 4 | الكتاب | 2 | 2 | — |

Path from token 1 to the CATiB root: 1 → 2

CATiB label reference: 1=MOD, 2=ROOT, 3=SBJ, 4=OBJ

*'A variety of particles can modify verbs' tense, polarity and aspect. These particles always attach under the verb with the relation MOD.' Same as PADT/UD; i'rab inverts it (I3rab Fig 16), which is exactly what re-rooting does.*

### `subjunctive_lan_01`

> لن يكتب الطالب الدرس

CATiB root: token **2** — i'rab root: token **1**

| position | word | CATiB head | i'rab head | moved |
|---:|---|---:|---:|---|
| 1 | لن | 2 | 0 (root) | **yes** |
| 2 | يكتب | 0 (root) | 1 | **yes** |
| 3 | الطالب | 2 | 2 | — |
| 4 | الدرس | 2 | 2 | — |

Path from token 1 to the CATiB root: 1 → 2

CATiB label reference: 1=MOD, 2=ROOT, 3=SBJ, 4=OBJ

*Same shape as لم — both are negation particles under the guidelines' PRT. The جازم/ناصب distinction is mood, which no arc records.*

### `idafa_01`

> كتاب الطالب جديد

CATiB root: token **3** — i'rab root: token **1**

| position | word | CATiB head | i'rab head | moved |
|---:|---|---:|---:|---|
| 1 | كتاب | 3 | 0 (root) | **yes** |
| 2 | الطالب | 1 | 1 | — |
| 3 | جديد | 0 (root) | 1 | **yes** |

Path from token 1 to the CATiB root: 1 → 3

CATiB label reference: 1=SBJ, 2=IDF, 3=ROOT

*IDF already runs possessor to possessed, so المضاف إليه hangs off المضاف and needs no flip. The root sits two arcs from token 1, so re-rooting reverses a path of length two.*

### `sifa_01`

> الكتاب الجديد مفيد

CATiB root: token **3** — i'rab root: token **1**

| position | word | CATiB head | i'rab head | moved |
|---:|---|---:|---:|---|
| 1 | الكتاب | 3 | 0 (root) | **yes** |
| 2 | الجديد | 1 | 1 | — |
| 3 | مفيد | 0 (root) | 1 | **yes** |

Path from token 1 to the CATiB root: 1 → 3

CATiB label reference: 1=SBJ, 2=MOD, 3=ROOT

*'The most basic use of MOD is to mark adjectival modification.' Both adjectives are NOM, and the صفة/خبر split is definiteness — invisible to the parser, and the rule engine's problem.*

---

## Summary

- 13 sentences, 5 already i'rab-shaped, 8 needed re-rooting.
- Every one matches gold after re-rooting at token 1.
- No labels were used. Only head numbers.

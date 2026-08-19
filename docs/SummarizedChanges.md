# What was built, and how

A plain account of how Sibawayh turns a typed Arabic sentence into إعراب, and why it is
put together the way it is. The blow-by-blow record of decisions lives in
[CHANGES.md](CHANGES.md) and the files it links to.

---

## The problem

**إعراب** is the traditional Arabic analysis of a sentence: naming each word's grammatical
job, its case, and the mark on its ending that shows that case. A student learning it does
not want to be handed the answer — they want to be walked toward it.

So the program has to do two things that pull in opposite directions. It has to be **right**,
because a confident wrong answer taught to a beginner is worse than no answer at all. And it
has to be **able to talk**, because a correct table of grammatical labels teaches nobody.

Everything below follows from keeping those two jobs apart.

---

## The chain

A sentence passes through six stages. Each one adds something and changes nothing that came
before it.

Take **قرأ محمد الكتاب** — *Muhammad read the book*.

### 1. Cleaning the text

Arabic is written several ways that mean the same thing. The letter أ may be typed as ا, ى
may stand in for ي, and ة may be written ه. Decorative letter-stretching (ـــ) is common.
None of it changes the word, and all of it confuses a lookup.

So the text is normalized first — one spelling per word — before anything tries to understand
it.

### 2. Looking up each word

Arabic words carry a great deal inside them. قرأ is not just a verb: it is past tense, active,
third person, masculine, singular. الكتاب is a noun, definite, and — depending on where it sits
in the sentence — in one of three cases.

A **morphological analyzer** is a large dictionary that knows all of this. Given a bare written
word, it returns every reading that word could have. The project uses one called CAMeL Tools.

The catch is that Arabic is normally written **without vowel marks**, and the marks are what
distinguish many readings. Written bare, كتبت could be *she wrote*, *it was written*, *I wrote*,
or *you wrote*. The analyzer returns all four and has no opinion about which was meant.

### 3. Choosing which reading was meant

Something has to pick. The project uses a language model that reads the **whole sentence** and
describes what belongs in each slot — *past tense, passive, third person, feminine* — and then
each candidate reading is scored by how many of its fourteen features match that description.
Highest count wins.

The reason it works is context. In **الرسالةُ كتبت** the word before the verb is *the letter*,
and a letter does not write — it gets written. That neighbour is the evidence.

An older, simpler method picked whichever reading was commonest for that word on its own. Every
case error measured against the test set came from that method, and none survived the switch.

**Two things this cannot do**, and both matter later:

- It **compares**; it never invents. If none of the dictionary's readings state a word's case,
  the winner will not state one either.
- When two readings match equally well, it genuinely cannot separate them.

The second gap is closed by using the student's own typing. If they wrote مُحَمَّدٌ with the vowel
marks, those marks say which reading was meant — so candidates matching what was typed are moved
up the list. Nothing is invented; the reading was in the list all along, and only the order
changes.

### 4. Finding out which word governs which

Grammar is not a flat list. In قرأ محمد الكتاب, both محمد and الكتاب hang off the verb قرأ — one
as the doer, one as the thing done. That structure is a **tree**, and working it out is called
parsing.

The project uses a trained parser and takes **only the tree shape** from it — which word attaches
to which — and throws away the parser's own names for the relationships. Those names come from a
different grammatical tradition and would only be confusing if mixed in.

One adjustment is needed. The parser hangs the sentence from its verb; إعراب hangs it from the
first word. That conversion is arithmetic on the tree, nothing more.

### 5. Adding words that were never written

Arabic often leaves the subject unwritten. In يقرأ الكتاب — *he reads the book* — the *he* is
inside the verb. Traditional grammar treats that hidden pronoun as a real part of the sentence
with a real grammatical role: **ضمير مستتر**.

No parser produces a node for a word that is not there, so the project inserts these itself, and
marks them as inserted so they can be excluded from any comparison against reference data.

### 6. Naming the roles

Now the actual إعراب. A set of hand-written rules looks at each word — its features, its position,
what governs it, which word governs it — and names its role: فاعل، مفعول به، مبتدأ، خبر، مضاف إليه،
نعت, and so on.

Two things make this layer trustworthy:

**Every rule records why it fired.** Not a paragraph — a list of observations, like
`case=nom`, `head_is_verb`, `immediately_follows_particle`. That list is kept on the word. It
turns out to be the single most useful thing in the project, because it is later reused as
teaching material.

**A rule that cannot be sure says nothing.** If the analyzer could not determine a word's case, or
two readings were nearly tied, or no rule matched, the word is left unlabelled and the page says
the syntax is uncertain. Silence is the intended output, not a failure of one.

---

## The two rules everything obeys

### Derived, not guessed

The role comes from rules operating on observations. It never comes from a language model. The
tree comes from the parser, the features come from the dictionary, and the role comes from the
rules — and every word records **which layer produced which fact**, so a wrong answer can be
traced to the layer that caused it.

### Abstain rather than guess

Wrong إعراب delivered confidently is the failure that would kill the product. Every layer is built
to refuse rather than fill in a gap. On the test sentences, fully vowelled, the current result is
39 roles right, 0 wrong, 1 abstained.

That one abstention is محمد, and it is instructive: the dictionary holds exactly one reading of
محمد, and that reading states no case. Adding vowel marks cannot help, because there is no second
candidate to promote. Proper names are simply not given case endings in that dictionary, while
ordinary nouns are.

---

## Writing it in Arabic

The analysis is data. A student needs sentences.

### The reliable half

Four lookup tables turn a role into an إعراب line: one for the words that open and close it, one
for naming the case, one for the mark on the ending, and one for words that do not inflect at all.

This runs offline, costs nothing, and produces the same line every time. It is the floor —
everything else falls back to it.

### The fluent half

A language model (Gemini) rewrites those lines as friendlier prose. It is handed the **finished
answer** and asked only to say it well. It cannot change the analysis, because it is never asked
for one.

And it is checked rather than trusted. Before any reply is shown, it is verified that the role,
the case and the mark all survived the rewrite, and that any reason it gave appears in the rule's
own list of observations. A reply failing any of those is discarded and the reliable line is used
instead.

Every failure ends in the same place: no key, no network, a rate limit, an unreadable reply, a
reply that drifted — all fall back to the table.

---

## Teaching, rather than answering

### Graded hints

The observations recorded by each rule become a ladder of three rungs:

1. **A question** — *what is the letter before it, and what does it do to what follows?*
2. **The reasoning** — *it came after one of إنّ's sisters, which govern what follows.*
3. **The answer** — the full إعراب line.

The student climbs as far as they want. The first two rungs are checked to make sure they do not
accidentally state the answer — a check that caught six of the project's own hint texts naming
the very role they were meant to lead toward.

The model may reword the first two rungs to keep them varied, but never decides what they are
allowed to say, and never sees the third.

### A tutor to argue with

Three fixed rungs are not enough for a student who wants to ask *why isn't it a subject?* So they
can talk to a tutor about any word.

While the answer is hidden, **it is not sent to the model at all** — the payload carries the word,
its features, the observations, and the roles of the *other* words, and nothing else. A model
cannot leak what it was never given.

That is the strong half. The weak half is that a capable model can work the answer out anyway, so
every reply is also checked for the role and the case, refused once, and then replaced with a line
pointing at the **إظهار** button. Once the student presses it, the withholding stops entirely.

### The page

One HTML file, one JSON endpoint, no build step. Words to tap, hints on demand, and a tree diagram
that stays hidden until the whole sentence has been worked through — it is the reward for
finishing, not the map handed out at the start.

---

## The one deliberate exception

Where the rules abstain, the student is shown a word with nothing beside it. That is honest, and
also the least useful thing the page can do, since that is exactly the word they are stuck on.

So the model is allowed to **suggest** a role for abstained words only — clearly marked as a guess,
with a note to check it with a teacher. The exception is kept narrow by the shape of the code
rather than by an instruction: a suggestion is returned in its own field, never becomes the real
role, is never scored, and is only ever asked for about words the rules declined.

---

## How it is checked

- Roughly a thousand automated tests, none of which contact a language model or load a large one.
- Recorded dictionary output, so results are identical on every machine.
- A small set of hand-annotated sentences that every layer is measured against.
- Separate checks that the analysis is internally consistent — a verb cannot have two subjects, a
  case must agree with its role — which catch contradictions, though not every wrong answer.

---

## What is still open

- **Proper names abstain** on case, for the dictionary reason above. Fixing it means reading the
  case off the ending the student typed, which is deriving a fact rather than choosing among
  facts — a different kind of operation, and it would need its own provenance label.
- **Coordination** (و joining two phrases) is not handled.
- **Duals, sound feminine plurals and the five nouns** have no entry in the endings table, so
  their lines stop after the case.
- A **parser trained from scratch** was built and measured separately, and deliberately not wired
  in: it uses a different grammatical convention and a different word-splitting scheme, and
  reconciling either is work that has not been done.

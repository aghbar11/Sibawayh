# Changes

Where the code departs from `CLAUDE.md` or `docs/PLAN.md`, and why.

Those two files stay as written — the spec and the plan of record. Anything that shipped
differently is recorded here instead of being edited into them, so the original intent and the
departure from it stay separately readable.

**The rule.** Flag every deviation, or ask first. Small and obvious: state it in the summary and
log it here. Changes what a component does: ask before doing it. Nothing gets absorbed silently.

`docs/PLAN.md` is gitignored, so anything here that matters to a reader of the repo needs to
stand on its own without it.

For a plain-language account of what was built and why, without the deviation-by-deviation
detail, see **[SummarizedChanges.md](SummarizedChanges.md)**.

---

## Where the detail lives

The reasoning behind each entry below is split by pipeline component:

| file | covers |
|---|---|
| [changes/foundations.md](changes/foundations.md) | the token schema, the evaluation set, text normalization, the command line |
| [changes/morphology.md](changes/morphology.md) | the CAMeL Tools wrapper, choosing among readings, typed diacritics |
| [changes/parsing.md](changes/parsing.md) | the parser interface, the CATiB backend, arc normalization |
| [changes/rules.md](changes/rules.md) | covert pronouns, the rule engine, the i'rab rules |
| [changes/rendering.md](changes/rendering.md) | the renderer interface, the four template tables, the model backend |
| [changes/teaching.md](changes/teaching.md) | the hint ladder, the API and page, suggestions, the tutor |
| [changes/data-assets.md](changes/data-assets.md) | what the project depends on and what may be done with it |

---

## Log

Newest last.


| component | change |
|---|---|
| evaluation set | eval set moved `docs/eval/` → `data/eval/`; test skip replaced with a raise |
| normalization | all three letter unifications opt-in behind `AGGRESSIVE`, not just ة → ه |
| normalization | added NFC composition, zero-width/bidi stripping, Unicode-derived diacritic set |
| token schema | `Gender.BOTH/UNKNOWN`, `Number.BOTH` added — amended during morphology |
| morphology | six extra CAMeL POS tags mapped by function, `pos_fine` keeps the original |
| morphology | ال folded back onto the stem despite d3tok splitting it |
| morphology | undocumented `-` and `NOAN` values handled |
| morphology | `enc0` role recorded as `feats.clitic_role` via `Features(extra="allow")` |
| morphology | `tests/data/camel_analyses.json` fixture + `camel` pytest marker, deselected by default |
| morphology | `Token.form` held the diacritized stem; now bare, `diac` carries the vowelling, `None` on backoff |
| command line | invocation is `python -m sibawayh`, not `python -m irab` — package renamed in the package layout |
| command line | four flags added: `--json`, `-a/--alternatives`, `--raw`, `--top` |
| command line | table gained a `diac` column once `form` and `diac` stopped being identical |
| parser interface | `parse` returns a self-validating `Parse`, not a bare `list[int]` |
| parser interface | parser is a component; `attach` is the stage that applies its result |
| token schema | `Token.arc_confidence` added — the confidence layer's input had nowhere to live |
| parser backend | backend is CamelParser's CATiB model, not Stanza — Stanza's Arabic model is non-commercial |
| parser backend | CATiB labels kept in `parser_label` as evidence; still discarded for role derivation |
| parser interface | `Parser.formalism` added so arc normalization can dispatch instead of assuming one convention |
| arc normalization | arc normalization is per-formalism, not a single UD-shaped pass |
| arc normalization | CATiB → i'rab is re-rooting at token 1 and nothing else |
| arc normalization | UD and PADT normalizers raise instead of being written blind |
| arc normalization | `tests/data/catib_trees.json` — hand-derived CATiB input trees |
| parser interface | `Formalism.IRAB` renamed `Formalism.SIBAWAYH`; `Token.irab_role` left alone |
| token schema | `parser_label` documented as a token property, not the name of its head arc |
| parser backend | checkpoint converted to plain tensors + JSON; the published pickle is never loaded at runtime |
| parser backend | `parser` extra is `supar`+`torch`, not `stanza`; `camel_parser` not used at all |
| parser backend | `CatibParser.labels()` sits outside the `Parser` interface |
| arc normalization | CATiB fixture upgraded from hand-derived to verified against the real model |
| covert pronouns | "no overt agent" tested via `parser_label=SBJ` **or** `case=nom`, not case alone |
| covert pronouns | an `unknown` case blocks insertion — abstaining direction |
| covert pronouns | inserted token is `pos=pron`, not the plan's `S-`, following the eval set |
| rule engine | a rule's `when` returns its evidence, not a boolean — matching and evidence are one act |
| rule engine | the registry is constructed explicitly, never populated by import side effects |
| rule engine | rules take `(token, head, tokens)`; "sentence" is the token sequence, not a `Sentence` |
| morphology | default disambiguator is BERT, not MLE — MLE's case output is unusable on short input |
| i'rab rules | perfect verbs were being named مضارع; the imperfect rules now assert aspect too |
| morphology | مضارع is never classified — `mood` is unavailable from morphology, fix is syntactic |
| i'rab rules | verb rules take the mood from the governing particle when morphology cannot supply it |
| i'rab rules | a root nominal is the مبتدأ even with an unreadable case; `acc`/`gen` still refused |
| morphology | `camel_analyses.json` re-recorded against BERT; two tests had asserted MLE's errors |
| i'rab rules | `nawasikh.py` and `particles.py` accept `conj` as well as `part` for إنّ |
| token schema | `gen: b` / `num: b` are declared by CAMeL but never observed — correction |
| — | `docs/REFERENCE.md` added — every field and value, generated from `schema.py` |
| i'rab rules | `rules/lexicon.py` added — closed-class word lists, matched diacritic-insensitively |
| i'rab rules | one rule per verb form rather than one rule with a computed role string |
| i'rab rules | verbal rules exclude النواسخ themselves rather than deferring to a file that does not exist |
| i'rab rules | 26 rules, not "roughly forty" — tier-2 roles have no gold and get none |
| i'rab rules | compound-role tokens live with the rule that knows the slot, not the part of speech |
| i'rab rules | `starter.py` removed; its two rules moved to `verbal.py` and `modifiers.py` |
| validation | the label inventory is 25 roles written out by hand, not the paper's 34 |
| validation | "exactly one agent per verb" softened — two is always an error, zero only sometimes |
| validation | a downgrade keeps heads and evidence; only the role, its rule and its provenance go |
| validation | mood/role agreement not checked; the plan asks for case only |
| morphology | `diacritics.py` added — the student's own vowelling picks among CAMeL's readings |
| morphology | `analyze` tokenizes twice, once as typed and once normalized, to keep the marks |
| — | audit of this file: four stale measurements corrected, three formatting defects fixed |
| morphology | **open defect** — `form` comes from the chosen analysis, so إن is shown back as أن |
| rendering | `render.py` becomes a `renderers/` package, shaped like `parsers/` |
| rendering | rendering is a component with **no** stage — `describe` returns lines, writes nothing |
| rendering | a token the rules abstained on renders to `None`; a whitespace line is refused |
| rendering | role phrasing, case naming, signs and المبني are four tables, one module each |
| rendering | `صفة` is phrased نعت and `مجرور` اسم مجرور — agreement and repetition, respectively |
| rendering | a مبني word's محل comes from the role alone, never from a read case or mood |
| rendering | signs are named for two declension classes only; the rest stop after the case |
| rendering | `python -m sibawayh irab` runs the whole pipeline and prints the إعراب |
| rendering | `GeminiRenderer` — the model rephrases the template's lines and does nothing else |
| rendering | every reply is checked for the role, the case and the sign before it is shown |
| rendering | `config.py` added — the key lives in `.env`, and nothing is written to `os.environ` |
| rendering | no SDK; one POST over `urllib`, transport injected so the tests never spend quota |
| rendering | the default is three lite models swept in order, not `gemini-flash-latest` |
| — | `Sign` carries `mark` as its own field, for the check to compare against |
| hint ladder | `reasons.py` — every evidence key gets a question, a reason and an anchor word |
| hint ladder | `hints.py` — three rungs, built from evidence, needing no model |
| rendering | a fourth check: the model's reason must come from the rule's own evidence |
| hint ladder | feature restatements get no entry; a hint made of `case=nom` gives the answer away |
| hint ladder | `python -m sibawayh irab --hints N` shows the first N rungs instead of the answer |
| API and page | `pipeline.py` — the chain in one place; the CLI stopped spelling it out |
| API and page | `api.py` + `web/index.html` — one JSON endpoint and one page, no build step |
| API and page | **the model may now suggest a role, but only where the rules declined** |
| API and page | a suggestion lives in its own field and never in `irab_role` |
| API and page | the tree is hidden until every word has been reached |
| morphology | `form` comes from the input again, not from the chosen analysis — إن stays إن |
| API and page | the model words the two teaching rungs; the ladder still decides what they may say |
| API and page | `faithful.leaks` — a rung that names the role or the case is thrown away |
| hint ladder | six reasons reworded: they stated the very role they were meant to lead to |
| hint ladder | **fixed** — لم was told a jussive particle preceded it; لم *is* the جازم |
| tutor | `tutor.py` + `POST /ask` — a conversation about one word |
| tutor | while the answer is hidden it is **not sent**; the reply is leak-checked as well |
| tutor | two refusals and the reply is replaced with a line pointing at «إظهار» |
| tutor | the conversation lives on the page; the server keeps no session |
| API and page | the tree draws its own words instead of measuring the row above it |


---

## Notes on the log

**Why the inventory is 25 and not 34.** The plan says every label must be in the 34-label set of
the I3rab paper. Nine of those have no rule producing them — حال، تمييز، بدل، توكيد، عطف، مفعول
مطلق and the rest of tier 2 — and a label sitting in the inventory with nothing emitting it can
only mask the next typo. `ROLES` is written out by hand rather than collected from the registry,
which is the whole point: an inventory derived from the rules could never disagree with the rules.
A test asserts it has nothing spare in it, so the two grow together.

**Why a verb may have no agent.** Taken literally, "every verb has exactly one agent" fails almost
every real sentence: undiacritized input abstains constantly, and an abstaining dependent may well
*be* the agent. Two agents is always a contradiction and always fires. Zero fires only when every
dependent of the verb was successfully labelled something else — at that point nothing is left to
be the agent, and Arabic has no such verb. Abstention is never an error.

**What a downgrade leaves behind.** Roles, `rule_id`, `confidence` and the `irab_role` provenance
entry go. Heads stay, because an arc is the parser's claim rather than ours and the UI still needs
somewhere to hang the words. `evidence` stays too: every item in it is an observation (`case=acc`,
`verb_has_no_overt_agent`), and an observation does not become false because the conclusion drawn
from it was thrown away.

**What the validators cannot catch.** They find contradictions, not wrong answers. On real
morphology `verbal_passive_01` read كتبت as active and passed every check, because an active
reading of that sentence is internally coherent — the agent count works out, the cases agree, the
tree is fine. Validation guarantees that what we assert holds together, nothing more.

**Typed diacritics are now used, and they close that gap.** The analyzer dediacritizes its input
before looking anything up, so كُتِبَتْ and كتبت produced byte-identical output and a student who
vowelled their sentence got nothing for it. Measured directly, not assumed: three spellings of one
sentence, one output.

But the reading was in CAMeL's list all along — كُتِبَت (passive) scored 0.9283 against the chosen
كَتَبَت (active) at 1.0. So `diacritics.py` does the comparison CAMeL will not, matching what was typed
against each candidate's own `diac` and letting the matches outrank the rest. Nothing is invented;
the analyses, the scores and the provenance are all still CAMeL's, and only the order changes.

Partial vowelling is the normal case, so the test is compatibility rather than equality, position
by position: where the student marked nothing there is no constraint, where the *candidate* marks
nothing it is the vaguer of the two and cannot contradict, and where both marked it the student's
mark must be among the candidate's. That last-but-one clause is what lets a typed final sukun
match CAMeL's كُتِبَت, which has none. A vowelling matching nothing leaves the order untouched —
we do not recognise it, and reordering on that basis would be a guess.

On the eval set, with real recorded morphology, counting against the 40 gold roles:

| input | right | wrong | abstained |
|---|---|---|---|
| as typed, bare | 36 | 2 | 2 |
| fully vowelled | 39 | 0 | 1 |

The one abstention left is محمد as a فاعل, and diacritics cannot reach it: CAMeL offers only two
readings of محمد, `مُحَمَّد` and a bare backoff, neither carrying a case ending at all. That is
`VERBAL_AGENT`'s `case=nom` requirement, still open.

**Two traps found while building it, both by measurement.** An unvowelled candidate is CAMeL's
backoff analysis, and being unvowelled it is compatible with everything — so it outranked the real
readings and stripped الدرس of its features entirely. Only a candidate that states a vowelling can
match one. And CAMeL writes الدَرْسَ where the student writes الدَّرْسَ, omitting the shadda of the
lam shamsiyya; that mismatch rejects every candidate, which is harmless only because rejecting
everything leaves CAMeL's own ranking in place. Worth revisiting if a sentence turns up where it
costs something.

---

### From the analysis to something a student can use

Up to here the project turned a sentence into data. Everything below turns that data into
something a student reads, argues with, and learns from. It arrived in this order, and each piece
only makes sense after the one before it:

1. **A renderer interface.** Prose is produced by a swappable backend, so the model is optional
   rather than load-bearing.
2. **A template backend.** Four lookup tables build a correct إعراب line offline, for free, the same
   every time. Everything after this degrades to it.
3. **A model backend.** Gemini rewrites those lines as teaching prose. It is handed the finished
   answer, and every reply is checked against it before anyone sees it.
4. **The hint ladder.** `Token.evidence` becomes three rungs: a question, the reasoning, then the
   answer.
5. **An API and a page.** One endpoint, one HTML file, no build step. Words, a tree, hints.
6. **Suggestions.** Where the rules abstain, the model may offer a guess — labelled as a guess.
7. **The model wording the hints**, still forbidden from deciding what they may say.
8. **A tutor to argue with**, which will not name the answer until the student asks for it.

The rule underneath all of it is unchanged: **the analysis is derived, and the model only says it
out loud.** Where that rule is bent — exactly once, in point 6 — it is written down below and
contained by the shape of the code rather than by an instruction.

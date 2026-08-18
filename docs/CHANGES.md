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
| 5 | default disambiguator is BERT, not MLE — MLE's case output is unusable on short input |
| 12 | perfect verbs were being named مضارع; the imperfect rules now assert aspect too |
| 5 | مضارع is never classified — `mood` is unavailable from morphology, fix is syntactic |
| 12 | verb rules take the mood from the governing particle when morphology cannot supply it |
| 12 | a root nominal is the مبتدأ even with an unreadable case; `acc`/`gen` still refused |
| 5 | `camel_analyses.json` re-recorded against BERT; two tests had asserted MLE's errors |
| 12 | `nawasikh.py` and `particles.py` accept `conj` as well as `part` for إنّ |
| 2 | `gen: b` / `num: b` are declared by CAMeL but never observed — correction |
| — | `docs/REFERENCE.md` added — every field and value, generated from `schema.py` |
| 12 | `rules/lexicon.py` added — closed-class word lists, matched diacritic-insensitively |
| 12 | one rule per verb form rather than one rule with a computed role string |
| 12 | verbal rules exclude النواسخ themselves rather than deferring to a file that does not exist |
| 12 | 26 rules, not "roughly forty" — tier-2 roles have no gold and get none |
| 12 | compound-role tokens live with the rule that knows the slot, not the part of speech |
| 12 | `starter.py` removed; its two rules moved to `verbal.py` and `modifiers.py` |
| 13 | the label inventory is 25 roles written out by hand, not the paper's 34 |
| 13 | "exactly one agent per verb" softened — two is always an error, zero only sometimes |
| 13 | a downgrade keeps heads and evidence; only the role, its rule and its provenance go |
| 13 | mood/role agreement not checked; the plan asks for case only |
| 5 | `diacritics.py` added — the student's own vowelling picks among CAMeL's readings |
| 5 | `analyze` tokenizes twice, once as typed and once normalized, to keep the marks |
| — | audit of this file: four stale measurements corrected, three formatting defects fixed |
| 5 | **open defect** — `form` comes from the chosen analysis, so إن is shown back as أن |
| 15 | `render.py` becomes a `renderers/` package, shaped like `parsers/` |
| 15 | rendering is a component with **no** stage — `describe` returns lines, writes nothing |
| 15 | a token the rules abstained on renders to `None`; a whitespace line is refused |
| 15 | role phrasing, case naming, signs and المبني are four tables, one module each |
| 15 | `صفة` is phrased نعت and `مجرور` اسم مجرور — agreement and repetition, respectively |
| 15 | a مبني word's محل comes from the role alone, never from a read case or mood |
| 15 | signs are named for two declension classes only; the rest stop after the case |
| 15 | `python -m sibawayh irab` runs the whole pipeline and prints the إعراب |
| 15 | `GeminiRenderer` — the model rephrases the template's lines and does nothing else |
| 15 | every reply is checked for the role, the case and the sign before it is shown |
| 15 | `config.py` added — the key lives in `.env`, and nothing is written to `os.environ` |
| 15 | no SDK; one POST over `urllib`, transport injected so the tests never spend quota |
| 15 | the default is three lite models swept in order, not `gemini-flash-latest` |
| — | `Sign` carries `mark` as its own field, for the check to compare against |
| 16 | `reasons.py` — every evidence key gets a question, a reason and an anchor word |
| 16 | `hints.py` — three rungs, built from evidence, needing no model |
| 15 | a fourth check: the model's reason must come from the rule's own evidence |
| 16 | feature restatements get no entry; a hint made of `case=nom` gives the answer away |
| 16 | `python -m sibawayh irab --hints N` shows the first N rungs instead of the answer |
| 17 | `pipeline.py` — the chain in one place; the CLI stopped spelling it out |
| 17 | `api.py` + `web/index.html` — one JSON endpoint and one page, no build step |
| 17 | **the model may now suggest a role, but only where the rules declined** |
| 17 | a suggestion lives in its own field and never in `irab_role` |
| 17 | the tree is hidden until every word has been reached |
| 5 | `form` comes from the input again, not from the chosen analysis — إن stays إن |

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

**Rendering is a component with no stage behind it.** Every other swappable piece of machinery in
this project comes in two halves: the component returns a narrow result, and a thin stage function
writes that result onto the tokens. `Parser.parse` returns head integers and `attach` puts them on
`Token.head`. The renderer has only the first half. `describe` runs a backend, checks it returned
one line per token, and hands the lines back to the caller.

There is nowhere for them to go. `Token` sets `extra="forbid"`, so prose could only be stored by
adding a field for it — and that is exactly the wrong thing to add. The renderer's entire
restriction is that it describes the analysis and does not participate in it; giving it a field on
the token it is describing hands it a way in. The restriction is currently enforced by the type
system, since a backend can return nothing but strings, and a display-text field would replace that
guarantee with a convention.

This is a real departure from the convention in `CLAUDE.md`, which says a component's result is
applied to the tokens by a stage. It is stated here rather than edited into the spec, because the
spec's rule is right for every component that produces *analysis* — and rendering is the one that
produces output.

**Declining has its own spelling.** `Rendering.lines[i]` is `None` where the backend had nothing to
say, which is what a token the rules abstained on gets. An empty string is refused outright: the
UI would show a word with a blank إعراب beside it, which reads as a page that failed to load rather
than as honest uncertainty, and abstention is only useful if it is legible as abstention.

**Backends are generative unless they declare otherwise.** `Renderer.deterministic` defaults to
`False`. Only a backend that depends on nothing but its tokens — no network, no sampling — may set
it, and only where it holds may a test compare against a fixed string or a caller cache a result.
The cautious value is the default because the model-backed backend is the one that will be written
without thinking about this.

**The template renderer, and why it comes before the model.** إعراب prose is
formulaic — the tradition teaches it as a formula precisely so a student can produce it
mechanically — so the first backend builds every line from lookup tables and never calls anything:

    الكِتابُ:      مبتدأ مرفوع وعلامة رفعه الضمة الظاهرة على آخره
    العِراقِيِّينَ: اسم إنّ منصوب وعلامة نصبه الياء لأنه جمع مذكر سالم
    في:            حرف جر مبني على السكون لا محل له من الإعراب، والجار والمجرور في محل رفع خبر

It runs offline, costs nothing, and is identical every run, which is what lets all thirteen eval
sentences be asserted against fixed strings. The prose a student reads now has a pass or a fail
instead of being eyeballed. It is also what the model backend degrades *to*, which is the part the
plan's "one retry then degrade" needed and did not have.

**Four tables, one module each.** `phrases.py` turns a role into the words that open and close a
line, `inflection.py` names the case, `signs.py` names the mark or letter carrying it, `built.py`
handles words with no case at all. `template.py` puts them in order. The split is not decorative:
each was written and measured on its own, and three of the four turned up something that would
have been wrong if the whole thing had been written at once.

**The em-dash in a compound role cannot be split on.** Five roles carry two claims, and the two
halves relate differently in each: `حرف جر — خبر شبه جملة` names the word then its phrase, while
`فاعل — ضمير مستتر` names the job then the word. A split would print ضمير مستتر where فاعل belongs.
So the table is written out by hand, 25 entries, held to `validate.ROLES` in both directions.

Two heads are deliberately not the role string. `مجرور` becomes *اسم مجرور* — the role names a
property and a line has to name a thing — and it is marked as already stating its case, or the line
reads اسم مجرور مجرور. `صفة` becomes *نعت*: صفة is feminine and would need مرفوعة where every other
role needs مرفوع, and نعت is the same term in the masculine, so the agreement problem disappears
rather than being handled.

**The sign is not decided by the case.** العراقيين is منصوب and takes الياء, so a template printing
الفتحة for every accusative would be confidently wrong about a word the eval set contains. Two
declension classes are implemented because two are what the gold has: 38 of the 40 tokens decline
with visible harakat and 2 are جمع مذكر سالم. المثنى، جمع المؤنث السالم، المقصور، المنقوص and
الأسماء الخمسة return nothing, and the line stops after the case — `الكِتابانِ: مبتدأ مرفوع` is thin
and true where `وعلامة رفعه الضمة` would be false.

Recognising جمع مذكر سالم needs the lemma rather than the ending: مَساكين ends in ـين and is
`num=p, gen=m` and is جمع تكسير. A sound plural is its own singular plus the suffix, and
مَسْكين + ين is not مَساكين. And the alef of tanween is not a final alef — رائِعاً would otherwise
look مقصور and lose its sign, which is a token of the eval set and not a hypothesis.

**Three defects that only appeared on real input**, which is the argument for wiring the CLI in the
same step rather than after:

* A perfect verb came out as *كُتِبَت: فعل ماضٍ مبني للمجهول مبني على الفتح في محل رفع فعل ماضٍ مبني
  للمجهول*. Live morphology reports a mood on perfect verbs — already recorded above under the
  disambiguator — and the محل clause was taking it. A مبني word cannot show a case, so any case on
  it belongs to the slot it occupies, and only a role that names a slot may supply one. The محل now
  comes from the role alone.
* `القَفَص` came out *اسم مجرور مجرور*, which is the `states_inflection` flag above.
* The covert pronoun rendered as *ضمير مستتر تقديره هو\**. The asterisk is bookkeeping that says the
  token was never typed, and it has no business in an Arabic line.

**Two gaps left open, both above this layer.** يقرأ in محمد يقرأ الكتاب renders as *فعل مضارع* with
no mood, because the role `خبر — جملة فعلية` claims the token for the nominal-predicate rule and
that rule states nothing about the verb, while morphology reports `mood=unknown` as it does for
every undiacritized مضارع. The renderer is right to stop; the mood is missing before it arrives.
And إن still displays as أَنَّ, which is the open `form` defect recorded earlier.

**The model says the answer out loud, and has no other power.** The interface allowed two safe
ones — rephrasing, and vetoing an analysis it disbelieved — and only the first was built, because
that was the decision. So the model is never asked what a word is. It receives the finished
analysis and is asked to say it again for a student:

    كَتَبَ:   يا بني كلمة كتب فعل ماض مبني على الفتح لأنه يدل على حدث انتهى في الزمن الماضي
    الطالِبُ: وكلمة الطالب فاعل مرفوع وعلامة رفعه الضمة الظاهرة على آخره لأنه هو من قام بكتابة المقالة

The facts in those lines are the template's, unchanged. The second half of each sentence is what
the model added, and it is the whole reason for asking one.

**The payload is the finished analysis, including the template's own line.** `evidence.py` sends
the role, the case, the sign, the observations the rule fired on, the head word, and the line the
template already built. Including the correct answer is deliberate: it turns the task from *analyze
this word* into *rewrite this sentence*, and the second is the one a model is reliable at. Nothing
in the payload is prose, so the same structure can be checked against the reply afterwards.

**Three facts have to survive the rewrite** — the role, the case, the sign. Everything else may
change, since a friendlier register is the point. Comparison is on bare letters, so منصوبٌ is not
read as disagreeing with منصوب.

A fact of several words is matched word by word, each after the last, rather than as one phrase.
Asked about إنّ the model wrote **حرف توكيد ونصب**, which is more complete than our own حرف نصب and
which a contiguous match rejected. A word inside a longer one counts, because ونصب contains نصب and
failing a reply for having a conjunction in it would be absurd. This is a check for drift and not a
parser: it catches مرفوع where the analysis said منصوب, which is what a careless rewrite actually
does.

**Every failure ends at the template line.** No key, no network, a rate limit, an unreadable reply,
a line that changed the case — each falls back, and only the affected line does. The worst outcome
is prose that reads like a textbook instead of a teacher, and a wrong answer is not among the
outcomes.

**What the free tier actually returns, measured against the real endpoint.** The quota is per model
per day, and the 429 body names it exactly — `GenerateRequestsPerDayPerProjectPerModel-FreeTier`,
`quotaValue: 20`, `model: gemini-3.7-flash`. That is what `gemini-flash-latest` resolves to: an
alias onto the newest model, with the smallest allowance of any of them. It is a poor default for
a job that is rephrasing rather than reasoning.

So the default is three lite models tried in order. The buckets are separate, so a model that has
spent its day is skipped instantly rather than waited for — pausing would only make a student wait
to be refused again — and the pause is kept for the congestion case, where `503 UNAVAILABLE` clears
in a moment. Also observed: `gemini-2.5-flash` and `gemini-2.5-flash-lite` now answer *this model
is no longer available*, so pinning an old name is not a way to avoid this.

**Two defects that only a real call could find**, which is why the key went in before the commit
rather than after:

* The faithfulness check rejected حرف توكيد ونصب, as above.
* A 503 on the *retry* was discarding the first reply wholesale, including two lines that had
  already passed. The retry is an improvement, not a prerequisite, and losing it may not also lose
  what was already good.

**The key lives in `.env`.** `config.py` reads the real environment first and the file second, so
exporting a key for one command overrides the file without editing it; the file is searched for
upwards from the working directory; and nothing is ever written back to `os.environ`, because a
library that edits the environment of the program that imported it surprises someone eventually.
`.gitignore` has covered `.env` since the repository was set up, and a test asserts it still does —
that line is the only thing standing between a key and a public commit.

**No SDK.** One POST to one endpoint over `urllib`, so no dependency and no licence question is
added to a project that tracks both carefully. The transport is injected, which is why every test
runs offline and none of them spend quota.

**The evidence list finally does the job it was added for.** `Token.evidence` has recorded why
every analysis came out the way it did since the rule engine was built, and nothing read it. Two
things now do, and they share one table in `reasons.py`: each key gets a question, the reason stated
plainly, and an anchor word.

**The hint ladder is the first.** Three rungs — a question, then the reasoning, then the إعراب:

    الطالِبِ   1. ما علاقة هذه الكلمة بالتي قبلها؟
               2. لأنها جاءت بعد مضاف، فهي مضاف إليه
               3. مضاف إليه مجرور وعلامة جره الكسرة الظاهرة على آخره

Always three, never a variable number: a student has to be able to tell how close they are to the
answer, and an interface where *one more hint* sometimes means the answer is one they stop
trusting. No model is involved — the ladder is offline, free and identical every run — and a word
the rules abstained on has no ladder at all, because a hint towards an analysis we do not have is a
guess dressed as teaching.

**A fourth check on the model's prose is the second.** Keeping the role, the case and the sign was
not enough. A reply can keep all three and still teach something false — *نعت مرفوع وعلامة رفعه
الضمة، لأنه جمع مذكر سالم* passes the first three — and the reason is the part that teaches. So the
reasons now travel to the model in Arabic rather than as keys, the instruction says to explain from
those and from nothing else, and a reply containing none of their anchors is refused. So is one
that gives no reason at all: the template line says exactly as much and is not a guess.

Measured live afterwards, every explanation traced to a key. المقالة came back as *نائب فاعل مرفوع
… لأنها جاءت بعد فعل ولأن الفعل مبني للمجهول، فالمرفوع بعده نائب فاعل لا فاعل* — which is
`head_pos=verb` and `head_voice=passive` reworded, not recalled.

**Restatement keys are deliberately absent from the table.** `case=nom` repeats the مرفوع the line
already states, so a hint built from one would give the answer away while pretending not to. Of the
39 keys the eval set produces, exactly 8 are restatements and have no entry; all 40 tokens still
have at least one reason, so no ladder has an empty middle rung.

**A test caught our own wording failing our own check.** The anchor for `head_voice=passive` was
written المجهول, which is not a substring of للمجهول — the two spell the ل differently — so the
reason we supply would have been rejected by the check we apply. Anchors are bare stems now.

**Still open, and agreed as the next piece.** The ladder's wording is the table's, so hints are
correct and a little stiff, and `--hints` ignores `--llm` entirely. The model should phrase the
rungs, but the ladder must keep deciding *what* each rung may contain — a model asked to hint at
اسم إنّ will give the answer on the first rung, because being helpful is its default. That needs the
inverse of the check above: rungs one and two must **not** contain the role or the case.

**The one place the model is allowed to decide something.** CLAUDE.md says the LLM renders and does
not decide, and everything until now enforced that with types: a renderer can return nothing but
strings. `renderers/suggest.py` is an exception, made deliberately and on request.

The reason is what a student sees when the rules abstain: their word, and nothing beside it. That is
honest and it is also the least useful thing the page can do, since the word they are stuck on is
precisely the one we declined. A guess that is labelled a guess, with a note to check it with a
teacher, is more use than silence and is not the failure mode abstention exists to prevent — that
failure mode is a *confident* wrong answer.

The containment is structural rather than promised:

* A suggestion never becomes `irab_role`. It comes back in its own map and lives in its own field,
  `Word.suggestion`, so nothing downstream can confuse the two.
* Only tokens the rules declined are asked about, and a suggestion that lands on any other token is
  dropped — a model asked about one word will sometimes answer about another.
* Nothing is scored with it. Evaluation reads `irab_role`, which this cannot reach.
* The page must draw it differently. That is the one part `suggest.py` cannot enforce from where it
  sits, so it is asserted in the API tests instead.

Measured: محمد in لم يقرأ محمد الكتاب comes back as *فاعل مرفوع وعلامة رفعه الضمة الظاهرة على آخره
لأنه من قام بالفعل*, which is right, and which our rules still decline to say.

**The tree is the reward for finishing, not the starting point.** It is the shape of the whole
answer, so a student who sees it early has been handed every remaining word at once. It stays hidden
until each word has been reached, with a count of how many are left. A word the rules declined
counts as reached — there is no answer to work towards, so nothing is being skipped past.

**`form` comes from the input again.** It was built from CAMeL's chosen analysis, so a student who
typed إن was shown أن — their own sentence rewritten in front of them, which was cosmetic in a
terminal and is not on a page. The reading still travels in `diac`, which is where a claim about
vowelling belongs. Where a word was split into clitics the analysis is still the source, because
the stem is then a part of the word and only the analysis knows where that part begins.

The test that had asserted the old behaviour asserted it for a good reason — that the two fields
must not drift apart — and the reason was inverted: the drift was the analyzer disagreeing with the
student, and showing the analyzer's spelling was the bug rather than the safeguard.

**Why محمد still abstains, even fully vowelled.** Measured: CAMeL returns two readings of محمد,
`مُحَمَّد` and a bare backoff, and *neither carries a case*. Typed diacritics choose among the
readings CAMeL offers; they cannot add a feature to a reading. So a student typing مُحَمَّدٌ changes
nothing, `VERBAL_AGENT` still sees `case=unknown`, and the rule declines. Closing this means reading
the case off the typed ending rather than picking a reading — deriving a feature instead of
selecting one — which is a different capability and would need a provenance value that is neither
`camel` nor `rules`. Not built.

**`GeminiClient` was split out of `GeminiRenderer`** when the second caller arrived. Suggesting a
role is a different task with a different prompt, and it has no business reimplementing quota
handling to get one.

Two edits were made directly to `CLAUDE.md`, both requested: the `prc0` bullet now records that
`d3tok` splits ال and that folding it back is the rule, and the conventions section now
distinguishes a component from a pipeline stage. They are corrections to the spec rather than
departures from it, which is why they live there and not only here.

---

## Step 2 — token schema

**Amended during step 5.** `Gender` gained `BOTH` and `UNKNOWN`; `Number` gained `BOTH`.

CAMeL's `db.defines` declares `gen: b f m na u` and `num: b d na p s u`. Without those members
`b` and `u` had nowhere to go, and folding them into `null` would have destroyed the `na` vs `u`
distinction CLAUDE.md calls load-bearing. Additive only — no existing value changed, the eval
set was unaffected.

**Corrected later.** The wording above originally said these were CAMeL's "real inventories",
implying `b` had been encountered. It had not. Scanning **all 74,014 entries** in
`morphology-db-msa-r13` — stem, prefix and suffix tables — finds:

    gen  {'-': 64639, 'm': 4474, 'f': 3582, None: 1280, 'u': 39}
    num  {'-': 65984, 'p': 6617, None: 1280, 's': 91, 'd': 26, 'u': 14, ...}

Zero occurrences of `b` in either. So `Gender.BOTH` and `Number.BOTH` are justified
**defensively** — the schema declares the value legal and `morphology-db-msa-s31` may use it —
not by observation. `UNKNOWN` on both is earned: `u` really does occur.

Two things the scan turned up incidentally. `num` contains one entry valued `'؛'` (an Arabic
semicolon) and one valued `'pf'`; neither is a legal value, and either would raise
`MorphologyError` out of `_lookup` if it ever surfaced — a latent crash rather than a wrong
answer, unhandled. And `-` is not the oddity step 5 treats it as: at 64,639 of 74,014 it is the
commonest value in the database by a factor of fourteen. The handling is right; the framing
understates it.

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

Not a deviation — a measurement, recorded because it makes steps 11–14 bigger than they look.

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

## Step 10 — covert pronoun insertion

### The test for "no overt agent" uses two signals, not one

The plan says *"for each verb with no overt agent among its dependents"*, and leaves open how a
stage that runs **before** the rule engine is supposed to know which dependent is the agent. It
cannot read `irab_role`; nothing has written one yet.

Two signals are used, and **either** is enough to block insertion:

* `parser_label == "SBJ"` — CATiB's own judgement, *"the explicit subject of a verb, active or
  passive"*
* `case == nom` — the morphological signal

The redundancy is the point. Step 5 recorded that CAMeL read الرجل in `verbal_overt_agent_01` as
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

## Step 12 — core i'rab rules

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

## Amendment to the disambiguator. Disambiguator is now BERT, not MLE

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
| `disambig-bert-unfactored-msa` (**what we ship**) | MIT weights, over the GPL v2 database | yes, with the database's GPL obligations |
| `disambig-mle-calima-msa-r13` (installed, fallback) | GPL v2 | yes, with GPL obligations |
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

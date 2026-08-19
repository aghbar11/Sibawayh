# Rendering

Turning the finished analysis into Arabic a student can read. A table-driven
renderer that is always right and always identical, and a model that rephrases
its output without being allowed to change it.

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

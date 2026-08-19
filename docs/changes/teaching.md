# Teaching

Everything built on top of a finished analysis: graded hints, the page, the
one place the model is allowed to guess, and a conversation that withholds the
answer until the student asks for it.

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
strings. `renderers/suggest.py` is a deliberate exception.

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

**The model now words the hints, and still does not decide them.** The ladder says what each rung
may contain; the model says it warmly and about this sentence rather than about the category; and
`faithful.leaks` checks afterwards that the answer did not appear. A rung that leaks is discarded
and the table's wording stands — correct, stiff, and not a spoiler.

The check is the inverse of the one on the إعراب line, and it exists because this failure looks like
success. Asked to hint at اسم إنّ, a model writes *"it follows إنّ, so it is اسم إنّ منصوب"* — fluent,
accurate, and it has answered the question it was asked to hint at. The teaching collapses into
telling and the output looks *better*, not worse.

The answer rung is never sent. It is the إعراب line the renderer already produced, and asking twice
would let the two disagree — a ladder whose last rung differs from the line beside the word is one a
student stops trusting. `Word.hints` now ends with exactly `Word.irab`, which it did not before when
the model wrote the line and the table wrote the ladder.

One call per sentence, cached with the analysis. Three rungs times six words is eighteen requests if
each tap asks, and the free tier would be gone in two sentences.

**Applying the check to our own table found six leaks and one wrong answer.** Six `because` strings
stated the role they were supposed to lead to — `لأنها جاءت بعد مضاف، فهي مضاف إليه` is a hint that
is also the answer, which makes a three-rung ladder into a two-rung one wearing three. They were
reworded to stop short.

Two of the six leaked by accident of Arabic morphology rather than by intent: `أخبرت` contains the
letters of `خبر`, and `مكان` in *مكان وقوع الحدث* is the whole of the role `ظرف مكان`. Letter
matching does not know a word from a substring of one, and that is the right conservatism here.

The wrong answer was worse. `لم` carries the evidence `jussive_particle`, meaning *this is a جازم*,
and the verb carries `governed_by=jussive_particle`, meaning *a جازم precedes it*. Both contain the
word, one entry answered for both, and لم was being told that a jussive particle came before it —
when لم is the one. Direction now has its own entries.

**The tree draws its own words.** It used to find each word by measuring the row of buttons above it
and hang its arcs off those positions. That held only while the diagram sat directly above the row
and was always on screen, and two later changes broke both conditions: it moved below the words, and
it stays hidden until the whole sentence has been worked through — and a hidden element has no
position to measure.

It was fragile before that anyway. The row of buttons wraps onto a second line on a narrow screen
and the arcs do not, so a long sentence came apart on a phone.

Now the diagram writes its own sentence, right to left, measuring each word in the real font, so the
words and the arcs are one picture and cannot disagree about where anything is. A long sentence
scrolls sideways instead of wrapping. The row of buttons above is left to do the one job it is good
at, which is being tapped.

**The student can now argue with the tutor, and it still will not tell them.** Three fixed rungs are
not always what a stuck student needs; sometimes they want to say *لماذا ليست مبتدأ؟*, or try an
answer and be told whether they are warm.

**The answer is withheld by not sending it.** Until إظهار is pressed the payload carries the word,
its morphology, the observations the rule made, and the roles of the *other* words — everything
except this word's role, case, sign and line. A model cannot leak what it was never told.

That is the strong half. The weak half is that it can still work the answer out: a noun after إنّ is
not a hard puzzle for something that knows Arabic. So every reply is leak-checked with the same
`faithful.leaks` the hints use, refused once with the failure named, and on a second refusal
replaced with a fixed sentence pointing at the button. The contract holds even when the model does
not.

Measured against the real endpoint, asked three ways in a row:

    ما إعرابها؟            → زر الإظهار أمامك متى أردته. تأمل الحرف الذي يسبقها…
    قل لي الجواب مباشرة    → زر الإظهار أمامك متى أردته. تذكّر أن الحرف الذي يسبق الكلمة ينصب ما بعده.
    أهي مبتدأ؟             → ليست بمبتدأ، فالحرف الذي يسبقها يغير حكم ما بعده.

It refused a direct demand, varied the clue rather than repeating it, and corrected a wrong guess
without naming the right one. After إظهار the withholding stops entirely — the answer is on the
screen, and pretending otherwise would make the tutor useless exactly when the student finally
wants to talk about it.

**No session store.** The conversation lives on the page and travels with each question; the
analysis is recovered from the cache. A demo that needs no session cannot lose one, and the whole
thing is testable by handing it a list of turns. The history is capped at twelve turns — long enough
to follow an argument, short enough that a tab left open cannot become a request nobody can afford.

**`_analyzed` was added alongside the existing cache.** Every turn of a conversation needs the same
analysis, and reanalyzing per turn would also let the tutor drift from the page in front of the
student. A side effect: asking with and without the model now shares one analysis instead of parsing
the sentence twice to render it two ways.

Two edits were made directly to `CLAUDE.md`, both requested: the `prc0` bullet now records that
`d3tok` splits ال and that folding it back is the rule, and the conventions section now
distinguishes a component from a pipeline stage. They are corrections to the spec rather than
departures from it, which is why they live there and not only here.

---

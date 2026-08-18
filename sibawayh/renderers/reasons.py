"""What each piece of evidence means, in Arabic a student can read.

`Token.evidence` is a list of short keys the rule recorded as it fired —
`head_lemma_in_inna_sisters`, `verb_has_no_overt_agent`, `case=nom`. They are the
only record of *why* an analysis came out the way it did, and until now nothing
turned them into words. Two things need that, and they need the same table:

* **the hint ladder**, which reveals the reasoning one step at a time
* **the check on the model's prose**, which has to know what a grounded
  explanation would look like before it can tell one from an invented one

Each entry says three things. `hint` is a question that points at the evidence
without answering it. `because` is the reason stated plainly. `anchor` is the one
word that has to survive if the model explains itself, which is what makes the
explanation checkable at all.

**Two kinds of key, and only one of them teaches.** `case=nom` and `pos=noun`
restate a feature already named in the line — the line says مرفوع, so a reason
saying "because its case is nominative" is a circle. Those are deliberately
absent here. What is present is the observations that add something: the word
before it was إنّ, the verb is passive, no agent was written, the word is مضاف.
Those are what a student cannot see for themselves.

**Some keys are built at runtime**, like `head_lemma_in_kana_sisters` and
`mood=jussive_from_governor`, so a few families are matched by shape after the
exact table misses. Anything still unrecognised returns `None`: an evidence key
with no entry is one this table has not been taught, and inventing an explanation
for it is precisely what the whole design exists to prevent.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Reason:
    """One observation, in three registers."""

    hint: str
    """A question pointing at the evidence, giving nothing away."""

    because: str
    """The observation stated plainly, ready to follow a role."""

    anchor: str
    """The word an explanation of this must contain.

    Chosen to be the thing being pointed at — إنّ, مضاف, مجهول — rather than a
    grammatical term the model might reasonably swap. It is a test for
    groundedness, not for phrasing.

    Written as a bare stem, without ال. Matching is on letters, and المجهول is
    not a substring of للمجهول — the two spell the ل differently, so an anchor
    carrying the article would fail against our own wording of the same reason.
    """


NAMED_REASONS: dict[str, Reason] = {
    # موقع الكلمة من الجملة
    "sentence_initial": Reason(
        hint="بأي كلمة بدأت الجملة؟",
        because="لأنها أول كلمة في الجملة",
        anchor="أول",
    ),
    "is_root": Reason(
        hint="ما الكلمة التي تقوم عليها الجملة كلها؟",
        because="لأنها الكلمة التي تُبنى عليها الجملة",
        anchor="الجملة",
    ),
    "head_is_topic": Reason(
        hint="عمّن تتحدث الجملة؟ وما الذي قيل عنه؟",
        because="لأنها جاءت بعد المبتدأ وأتمّت معناه",
        anchor="المبتدأ",
    ),
    "predicate_position": Reason(
        hint="أين وقعت هذه الكلمة من الجملة؟",
        because="لأنها وقعت في الموضع الذي يُتمّ به معنى الجملة",
        anchor="الموضع",
    ),
    "no_verb_in_sentence": Reason(
        hint="هل في الجملة فعل؟",
        because="لأن الجملة اسمية لا فعل فيها",
        anchor="اسمية",
    ),
    "verbal_sentence_as_predicate": Reason(
        hint="هل الخبر كلمة واحدة أم جملة؟",
        because="لأن ما أتمّ المعنى هنا جملة فعلية لا كلمة مفردة",
        anchor="جملة",
    ),
    "heads_the_clause": Reason(
        hint="ما الكلمة التي تقوم عليها هذه الجملة الصغرى؟",
        because="لأنها رأس الجملة الصغرى داخل الجملة الكبرى",
        anchor="الجملة",
    ),
    "adverbial": Reason(
        hint="هل تدل الكلمة على زمان أو مكان؟",
        because="لأنها تدل على موضع وقوع الحدث",
        anchor="موضع",
    ),
    "case_unreadable_position_decides": Reason(
        hint="هل تظهر الحركة على آخر الكلمة؟",
        because="لأن الحركة لا تظهر، فموقع الكلمة هو الذي دلّ على إعرابها",
        anchor="موقع",
    ),
    # النواسخ
    "lemma_in_inna_sisters": Reason(
        hint="إلى أي مجموعة من الحروف ينتمي هذا الحرف؟",
        because="لأنه من إنّ وأخواتها",
        anchor="إنّ",
    ),
    "head_lemma_in_inna_sisters": Reason(
        hint="ما الحرف الذي قبلها، وماذا يفعل بما بعده؟",
        because="لأنها جاءت بعد إنّ أو إحدى أخواتها، وهي تنصب الاسم وترفع الخبر",
        anchor="إنّ",
    ),
    "lemma_in_kana_sisters": Reason(
        hint="إلى أي مجموعة من الأفعال ينتمي هذا الفعل؟",
        because="لأنه من كان وأخواتها",
        anchor="كان",
    ),
    "head_lemma_in_kana_sisters": Reason(
        hint="ما الفعل الذي قبلها، وماذا يفعل بما بعده؟",
        because="لأنها جاءت بعد كان أو إحدى أخواتها، وهي ترفع الاسم وتنصب الخبر",
        anchor="كان",
    ),
    # الفعل وفاعله
    "head_pos=verb": Reason(
        hint="ما نوع الكلمة التي قبلها؟",
        because="لأنها جاءت بعد فعل",
        anchor="فعل",
    ),
    "follows_verb": Reason(
        hint="ما الذي جاء قبل هذه الكلمة؟",
        because="لأنها جاءت بعد الفعل",
        anchor="الفعل",
    ),
    "head_voice=passive": Reason(
        hint="هل ذُكر من قام بالفعل، أم حُذف؟",
        because="لأن الفعل مبني للمجهول، فمن قام به غير مذكور",
        anchor="مجهول",
    ),
    "head_voice=active": Reason(
        hint="هل ذُكر من قام بالفعل؟",
        because="لأن الفعل مبني للمعلوم",
        anchor="معلوم",
    ),
    "verb_has_no_overt_agent": Reason(
        hint="من الذي قام بهذا الفعل؟ وهل تراه مكتوبًا في الجملة؟",
        because="لأن الفعل لم يُذكر معه من قام به، فهو ضمير مستتر",
        anchor="مستتر",
    ),
    "features_copied_from_verb": Reason(
        hint="من الذي قام بالفعل؟ وكيف عرفت؟",
        because="لأن صيغة الفعل هي التي دلّت على الضمير المستتر",
        anchor="الفعل",
    ),
    "inserted_by_us": Reason(
        hint="هل كل كلمة في الإعراب مكتوبة في الجملة؟",
        because="لأن الضمير مستتر لم يُكتب في الجملة",
        anchor="مستتر",
    ),
    # الإضافة والجر
    "state=construct": Reason(
        hint="هل الكلمة مضافة إلى ما بعدها؟",
        because="لأنها مضاف، والمضاف لا يُنوَّن ولا تدخله ال",
        anchor="مضاف",
    ),
    "head_state=construct": Reason(
        hint="ما علاقة هذه الكلمة بالتي قبلها؟",
        because="لأنها جاءت بعد مضاف",
        anchor="مضاف",
    ),
    "head_pos=prep": Reason(
        hint="ما الذي جاء قبلها مباشرة؟",
        because="لأنها جاءت بعد حرف جر",
        anchor="حرف جر",
    ),
    "governs_a_genitive": Reason(
        hint="ماذا فعل هذا الحرف بالكلمة التي بعده؟",
        because="لأنه يجر الاسم الذي بعده",
        anchor="يجر",
    ),
    # العوامل في الفعل المضارع
    "heads_an_imperfect_verb": Reason(
        hint="على أي نوع من الأفعال دخل هذا الحرف؟",
        because="لأنه يدخل على الفعل المضارع فيؤثر في آخره",
        anchor="المضارع",
    ),
    "governs_case=acc": Reason(
        hint="ماذا يفعل هذا الحرف بما بعده؟",
        because="لأنه ينصب ما بعده",
        anchor="ينصب",
    ),
    "no_governing_particle": Reason(
        hint="هل سبق الفعلَ حرفٌ يؤثر في آخره؟",
        because="لأنه لم يسبقه ناصب ولا جازم",
        anchor="ناصب",
    ),
    # التوابع
    "agrees_case": Reason(
        hint="قارن حركة الكلمتين. هل تتفقان؟",
        because="لأنها تتبع ما قبلها في الإعراب",
        anchor="تتبع",
    ),
    "agrees_gender": Reason(
        hint="قارن الكلمتين في التذكير والتأنيث.",
        because="لأنها تتبع ما قبلها في التذكير والتأنيث",
        anchor="تتبع",
    ),
    "agrees_number": Reason(
        hint="قارن الكلمتين في الإفراد والجمع.",
        because="لأنها تتبع ما قبلها في الإفراد والتثنية والجمع",
        anchor="تتبع",
    ),
    "agrees_definiteness": Reason(
        hint="هل الكلمتان معًا معرفتان أم نكرتان؟",
        because="لأنها تتبع ما قبلها في التعريف والتنكير",
        anchor="التعريف",
    ),
    "definiteness_agrees": Reason(
        hint="هل الكلمتان معًا معرفتان أم نكرتان؟",
        because="لأنها توافق ما قبلها في التعريف والتنكير",
        anchor="التعريف",
    ),
    "definiteness_disagrees": Reason(
        hint="إحداهما معرفة والأخرى نكرة. ماذا يعني ذلك؟",
        because="لأنها تخالف ما قبلها في التعريف، فليست تابعة له",
        anchor="التعريف",
    ),
    "definiteness_mismatch_with_head": Reason(
        hint="إحداهما معرفة والأخرى نكرة. ماذا يعني ذلك؟",
        because="لأنها تخالف ما قبلها في التعريف، فليست تابعة له",
        anchor="التعريف",
    ),
    # الترتيب
    "immediately_follows_head": Reason(
        hint="أين وقعت الكلمة من التي تتعلق بها؟",
        because="لأنها جاءت مباشرة بعد الكلمة التي تتعلق بها",
        anchor="بعد",
    ),
    "immediately_follows_particle": Reason(
        hint="أين وقعت الكلمة من الحرف؟",
        because="لأنها جاءت مباشرة بعد الحرف",
        anchor="بعد",
    ),
}

IS_JUSSIVE = Reason(
    hint="ما نوع هذا الحرف؟ وماذا يفعل بالفعل الذي بعده؟",
    because="لأنه من الحروف التي تجزم الفعل المضارع",
    anchor="تجزم",
)
IS_SUBJUNCTIVE = Reason(
    hint="ما نوع هذا الحرف؟ وماذا يفعل بالفعل الذي بعده؟",
    because="لأنه من الحروف التي تنصب الفعل المضارع",
    anchor="تنصب",
)
JUSSIVE = Reason(
    hint="ما الحرف الذي سبق الفعل؟ وماذا فعل بآخره؟",
    because="لأن قبله حرف جزم، والجازم يجزم الفعل المضارع",
    anchor="جزم",
)
SUBJUNCTIVE = Reason(
    hint="ما الحرف الذي سبق الفعل؟ وماذا فعل بآخره؟",
    because="لأن قبله حرف نصب، والناصب ينصب الفعل المضارع",
    anchor="نصب",
)
FROM_GOVERNOR = Reason(
    hint="ما الذي جعل آخر الفعل على هذه الحال؟",
    because="لأن الحرف الذي قبله هو الذي أثّر في آخره",
    anchor="الحرف",
)
BY_DEFAULT = Reason(
    hint="هل سبق الفعلَ حرفٌ يؤثر في آخره؟",
    because="لأنه لم يسبقه ناصب ولا جازم، فبقي على أصله",
    anchor="ناصب",
)

PATTERNS: tuple[tuple[str, Reason], ...] = (
    ("governed_by=jussive", JUSSIVE),
    ("governed_by=subjunctive", SUBJUNCTIVE),
    ("governs_mood=jussive", IS_JUSSIVE),
    ("governs_mood=subjunctive", IS_SUBJUNCTIVE),
    ("_from_governor", FROM_GOVERNOR),
    ("_by_default", BY_DEFAULT),
    ("jussive", IS_JUSSIVE),
    ("subjunctive", IS_SUBJUNCTIVE),
)
"""Keys the rules assemble at runtime, matched by the part that carries meaning.

`governed_by=jussive_particle` and `mood=jussive` are built from a variable, so
there is no fixed string to look up.

**Direction is the whole difficulty, and it was wrong.** `jussive_particle` sits
on لم and says *this is a جازم*; `governed_by=jussive_particle` sits on the verb
and says *a جازم precedes it*. Both contain the word, and the bare entry used to
answer for both — so لم was told that a jussive particle came before it, when لم
**is** the one. The specific keys are matched first, and the bare ones now mean
the particle rather than what it governs.
"""


def reason_for(key: str) -> Reason | None:
    """What `key` means, or `None` if this table has not been taught it.

    `None` is also the right answer for the restatement keys — `case=nom`,
    `pos=noun` — which have no entry on purpose. They repeat what the line
    already says, and a hint made of one would be a circle.
    """
    exact = NAMED_REASONS.get(key)
    if exact is not None:
        return exact
    for fragment, reason in PATTERNS:
        if fragment in key:
            return reason
    return None


def reasons_in(evidence: list[str]) -> tuple[Reason, ...]:
    """Every reason `evidence` supplies, in order, without repeating one.

    Two keys often mean the same thing to a student — `head_lemma_in_kana_sisters`
    and `head_pos=verb` on the same token — and saying it twice reads as padding.
    """
    found: list[Reason] = []
    for key in evidence:
        reason = reason_for(key)
        if reason is not None and reason not in found:
            found.append(reason)
    return tuple(found)

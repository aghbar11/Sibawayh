"""How each i'rab role is put into words.

Every إعراب line opens by naming what the word is — مبتدأ، اسم إنّ، حرف جر —
and most roles supply that phrase by simply being it. Five do not. Those carry a
second claim after an em-dash, and the em-dash means something different every
time:

| role | first half | second half |
|---|---|---|
| `حرف جر — خبر شبه جملة` | what the word is | what the phrase it heads is |
| `ظرف مكان — خبر شبه جملة` | what the word is | what the phrase it heads is |
| `خبر — جملة فعلية` | what the *clause* is | what kind of clause |
| `فاعل — ضمير مستتر` | what the word does | what the word is |
| `مبتدأ — مضاف` | what the word is | a further property of it |

There is no rule that reads all five. `فاعل — ضمير مستتر` puts the role first and
the description second; `حرف جر — خبر شبه جملة` does the opposite. Splitting on
the em-dash and hoping would produce ضمير مستتر where فاعل belongs. So this is a
table with an entry per role, written out by hand, and a test holds it to the
same inventory `validate.ROLES` publishes.

Two fields do the work of the two halves. `head` names the token and opens the
line. `tail` is a clause about the larger unit the token belongs to, appended
after everything else has been said about the word itself.

`head` is `None` for `خبر — جملة فعلية`, and that is the honest value: the token
there is a verb, and the role names its clause rather than the verb. What the
word is comes from its morphology, and the role contributes only the closing
clause.

Verb roles state their own inflection — `فعل مضارع مرفوع` is one phrase, not a
noun plus a case. `states_inflection` marks them so nothing appends مرفوع a
second time. The role is also the better authority than `feats` here: an
imperfect verb's mood is usually unreadable on undiacritized input, and the rule
that assigned the role is what recovered it from the governing particle.
"""

from __future__ import annotations

from dataclasses import dataclass

from sibawayh.renderers.base import RenderError


@dataclass(frozen=True)
class Phrase:
    """The words a role contributes to an إعراب line."""

    head: str | None
    """Names the token and opens the line, or `None` where the role does not
    describe the word at all and morphology has to."""

    tail: str = ""
    """A clause about the phrase or clause the token belongs to, said last."""

    states_inflection: bool = False
    """True where `head` already contains مرفوع/منصوب/مجزوم, so no case clause
    should be added after it."""


ROLE_PHRASE: dict[str, Phrase] = {
    # الفعل — each names its own inflection, so nothing may add another.
    "فعل ماضٍ": Phrase("فعل ماضٍ"),
    "فعل ماضٍ مبني للمجهول": Phrase("فعل ماضٍ مبني للمجهول"),
    "فعل ماضٍ ناقص": Phrase("فعل ماضٍ ناقص"),
    "فعل مضارع مرفوع": Phrase("فعل مضارع مرفوع", states_inflection=True),
    "فعل مضارع منصوب": Phrase("فعل مضارع منصوب", states_inflection=True),
    "فعل مضارع مجزوم": Phrase("فعل مضارع مجزوم", states_inflection=True),
    # عمدتا الجملة الفعلية وما يتعلق بهما
    "فاعل": Phrase("فاعل"),
    "فاعل — ضمير مستتر": Phrase("فاعل"),
    "نائب فاعل": Phrase("نائب فاعل"),
    "مفعول به": Phrase("مفعول به"),
    # الجملة الاسمية
    "مبتدأ": Phrase("مبتدأ"),
    "مبتدأ — مضاف": Phrase("مبتدأ", tail="وهو مضاف"),
    "خبر": Phrase("خبر"),
    "خبر — جملة فعلية": Phrase(None, tail="والجملة الفعلية في محل رفع خبر"),
    "حرف جر — خبر شبه جملة": Phrase("حرف جر", tail="والجار والمجرور في محل رفع خبر"),
    "ظرف مكان — خبر شبه جملة": Phrase("ظرف مكان", tail="والظرف في محل رفع خبر"),
    # النواسخ
    "اسم كان": Phrase("اسم كان"),
    "خبر كان": Phrase("خبر كان"),
    "اسم إنّ": Phrase("اسم إنّ"),
    "خبر إنّ": Phrase("خبر إنّ"),
    # التوابع والمجرورات
    "صفة": Phrase("صفة"),
    "مضاف إليه": Phrase("مضاف إليه"),
    "مجرور": Phrase("اسم مجرور"),
    # الحروف
    "حرف جزم": Phrase("حرف جزم"),
    "حرف نصب": Phrase("حرف نصب"),
}
"""Every role in `validate.ROLES`, and the words it contributes.

`مجرور` is the one role whose head is not the role string: the role names a
property, and the line has to name a thing — *اسم مجرور*, not *مجرور مجرور*.

`فاعل — ضمير مستتر` gets the same head as a plain `فاعل`. What makes the line
different is that the token is a covert pronoun, and that is on the token, not
in the role.
"""


def phrase_for(role: str) -> Phrase:
    """The `Phrase` for `role`.

    Raises rather than falling back to the role string. A role with no entry is
    a role this table has not been taught, and echoing it back would put an
    unreviewed grammatical term in front of a student — the one failure mode
    CLAUDE.md says kills the product.
    """
    try:
        return ROLE_PHRASE[role]
    except KeyError:
        raise RenderError(f"no phrasing for role {role!r}") from None

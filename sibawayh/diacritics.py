"""Using the diacritics the student typed, which CAMeL throws away.

The morphology database is keyed on undiacritized forms, so the analyzer
dediacritizes whatever it is handed before it looks anything up. Feeding it
كُتِبَتْ and كتبت produces byte-identical output — the vowels are not a weak
signal that loses a ranking, they are discarded before any ranking happens.

That is a real loss, because the analyzer already knows the reading the student
meant. For كتبت it returns both:

    كَتَبَت   active   1.0      ← chosen
    كُتِبَت   passive  0.9283
    كَتَبْتِ  active   0.9283

Note the shape of that, because it is not the shape you would guess. The winner
is a clear seven points ahead — nothing here looks like a tie, and a confidence
rule that abstains on a narrow first-to-second margin would sail straight past
this sentence. What is tied is the *field behind* the winner: the correct
reading and the one after it are three hundred-thousandths apart, and the
analyzer cannot tell them from each other at all.

So the vowels are not breaking a tie at the top. They are reaching into a
cluster the disambiguator has already given up on. A student who typed كُتِبَتْ
has told us which member of that cluster was meant, and their diacritics are the
only ground truth anywhere in this pipeline.

So we do the comparison CAMeL will not: match what was typed against each
candidate's own vowelling, and let the matches outrank the rest. Nothing is
invented — the reading was in CAMeL's list all along.

Partial vowelling is the normal case. Students mark the ending, or the one
letter they are unsure of, and leave the rest bare. So the test is
*compatibility*, not equality, position by position:

* the student marked nothing here — no constraint
* the candidate marks nothing here — the candidate is the vaguer of the two,
  and does not contradict anything (this is what lets a typed final sukun match
  CAMeL's كُتِبَت, which has none)
* both marked it — what the student typed must be among the candidate's marks

Nothing here knows CAMeL's field names. It compares strings, and `morphology.py`
is what pulls `diac` out of an analysis and applies the order.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sibawayh.normalize import DIACRITICS, NormalizationOptions, normalize

KEEP_DIACRITICS = NormalizationOptions(strip_diacritics=False)
"""`SAFE` in every respect except that the marks survive.

The typed word has to be compared against CAMeL's `diac`, which is composed,
tatweel-free and hamza-preserving. Running the same normalization minus the
one step that would defeat the purpose is what puts the two on equal terms.
"""

Marked = tuple[tuple[str, frozenset[str]], ...]
"""A word as (base letter, the marks sitting on it), in order."""


def split_marks(text: str) -> Marked:
    """Pair every base letter with the combining marks that follow it.

    A mark before any letter — a stray harakat, malformed input — is dropped
    rather than raising. There is nothing for it to sit on.
    """
    marked: list[tuple[str, set[str]]] = []
    for char in normalize(text, KEEP_DIACRITICS):
        if char in DIACRITICS:
            if marked:
                marked[-1][1].add(char)
        else:
            marked.append((char, set()))
    return tuple((base, frozenset(marks)) for base, marks in marked)


def has_diacritics(text: str) -> bool:
    """Whether the student marked anything at all. If not, there is no signal."""
    return any(char in DIACRITICS for char in text)


def compatible(typed: str, candidate: str) -> bool:
    """Whether `candidate` could be the vowelling of what the student typed.

    Both are read as base letters plus marks. Different letters mean different
    words and settle it immediately. Otherwise every position the student marked
    must be a position the candidate either left open or marked the same way.

    Deliberately asymmetric: an unvowelled `typed` is compatible with
    everything, which is exactly right — a student who marked nothing has told
    us nothing, and must not narrow the field.
    """
    left, right = split_marks(typed), split_marks(candidate)
    if len(left) != len(right):
        return False
    for (typed_base, typed_marks), (candidate_base, candidate_marks) in zip(
        left, right, strict=True
    ):
        if typed_base != candidate_base:
            return False
        if typed_marks and candidate_marks and not typed_marks <= candidate_marks:
            return False
    return True


@dataclass(frozen=True)
class Ranking:
    """How the typed diacritics reorder a ranked list of candidates.

    `order` is the candidate indices, matches first and everything else after,
    each group keeping the order the disambiguator gave it. Nothing is thrown
    away: a rejected reading is still a reading, and the confidence layer wants
    to see how close the field was.
    """

    order: tuple[int, ...]
    matched: tuple[int, ...]

    @property
    def decided(self) -> bool:
        """Whether the typed diacritics actually ruled anything out.

        False when the student marked nothing, when every candidate is
        compatible, and when none is — that last case being a typed vowelling
        we do not recognise, where the honest response is to change nothing.
        """
        return 0 < len(self.matched) < len(self.order)


def rank(typed: str, candidates: Sequence[str]) -> Ranking:
    """Reorder `candidates` — each one a diacritized form — by what was typed.

    Pure, and total: an empty candidate (CAMeL's backoff analyses have no
    diacritization) simply never matches, and a typed vowelling that matches
    nothing leaves the order untouched.
    """
    everything = tuple(range(len(candidates)))
    if not has_diacritics(typed):
        return Ranking(order=everything, matched=everything)

    # An unvowelled candidate is CAMeL's backoff analysis: it failed to
    # recognise the word and echoed the surface back. It carries no vowelling to
    # agree with, so under the rule above it would be compatible with anything
    # and could outrank the real readings. Only a candidate that actually states
    # a vowelling can be said to match one.
    matched = tuple(
        i for i, form in enumerate(candidates) if has_diacritics(form) and compatible(typed, form)
    )
    if not matched or len(matched) == len(candidates):
        return Ranking(order=everything, matched=matched)

    rejected = tuple(i for i in everything if i not in set(matched))
    return Ranking(order=matched + rejected, matched=matched)

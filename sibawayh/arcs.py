"""Arc normalization: rewrite a backend's arcs into i'rab convention.

The three schemes CLAUDE.md tabulates disagree structurally, not just in
vocabulary, so this cannot be one pass. A backend declares its `Formalism` and
normalization dispatches on it. Adding a backend costs one more function here
and nothing anywhere else — that, rather than the choice of any one formalism,
is what keeps the parser swappable.

Heads only. This stage never reads a label, never writes a role, and never adds
or removes a token. Covert pronouns come later, from `covert.py`.

CATiB
-----
CATiB already agrees with i'rab on every *internal* arc.

* `OBJ` is "object of verb, **preposition**, or deverbal noun" — the preposition
  heads its object, as عامل. UD is the odd one out here, not CATiB.
* `IDF` runs possessor → possessed, so المضاف إليه already hangs off المضاف.
* `PRD` marks "the complement of the extended copular constructions" for
  كان وأخواتها and إنّ وأخواتها — so الناسخ heads both its اسم and its خبر,
  which is what i'rab wants and what PADT does *not* do.
* `MOD` attaches a modifier to what it modifies. They will be differentiated by
  position in the tree and rule engines.

That leaves exactly one systematic disagreement: **where the sentence roots.**
CATiB roots at the predicate; i'rab roots at the first word of the sentence
(CLAUDE.md's scheme table, first row). So the entire CATiB → i'rab conversion is
a re-rooting, and re-rooting is a pure operation on head indices — no label
needed, which is fortunate, because `Parse` carries none.

Verified against all thirteen tier-1 eval sentences: re-rooting at token 1 turns
the CATiB tree into the gold i'rab tree in every one, including the four the
notes flag as places other schemes diverge (`nasikh_inna_01`, `jussive_lam_01`,
`nominal_pp_predicate_01`, `nominal_verbal_predicate_01`).

UD and PADT
-----------
Not implemented. No backend speaks either yet, so there is nothing to test a
normalizer against, and a UD flip written blind would be untested code claiming
to work. They raise. The dispatch is the point; filling it in is cheap once a
backend exists.

Known gaps
----------
Coordination is untouched under every formalism, as planned. A sentence opening
with a conjunction would re-root onto the conjunction, which is very likely
wrong — but coordination is deferred, and guessing at it here would be worse
than leaving it visible.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from sibawayh.parsers.base import Formalism
from sibawayh.schema import ROOT_HEAD, Source, Token

SIBAWAYH_ROOT_POSITION = 1
"""i'rab roots a sentence at its first word. CLAUDE.md, scheme table, row 1."""


class ArcError(RuntimeError):
    """Arcs could not be normalized into i'rab convention."""


def reroot(heads: Sequence[int], at: int = SIBAWAYH_ROOT_POSITION) -> tuple[int, ...]:
    """Re-root a dependency tree at the 1-based position `at`.

    Reverses every arc on the path from `at` up to the current root, which is
    the minimal edit that moves the root: no other token changes governor, so
    every relation the parser got right survives intact.

    Operates on integers rather than tokens so that a normalizer can be tested
    the way a parser is — by comparing two lists of numbers.
    """
    if not heads:
        return ()
    count = len(heads)
    if not 1 <= at <= count:
        raise ArcError(f"cannot root at {at}: there are {count} tokens")

    path: list[int] = []
    seen: set[int] = set()
    node = at
    while node != ROOT_HEAD:
        if node in seen:
            raise ArcError(f"cycle through token {node}; cannot reach the root from {at}")
        if not ROOT_HEAD <= node <= count:
            raise ArcError(f"head {node} does not name a token")
        seen.add(node)
        path.append(node)
        node = heads[node - 1]

    normalized = list(heads)
    normalized[at - 1] = ROOT_HEAD
    for child, parent in zip(path, path[1:], strict=False):
        normalized[parent - 1] = child
    return tuple(normalized)


def _from_catib(heads: Sequence[int]) -> tuple[int, ...]:
    """CATiB → i'rab. Re-rooting is the whole job; see the module docstring."""
    return reroot(heads)


def _identity(heads: Sequence[int]) -> tuple[int, ...]:
    """Already in i'rab convention — a gold tree, or a backend that emits one."""
    return tuple(heads)


def _unimplemented(formalism: Formalism) -> Callable[[Sequence[int]], tuple[int, ...]]:
    def raise_it(_heads: Sequence[int]) -> tuple[int, ...]:
        raise ArcError(
            f"no {formalism} normalizer: no backend emits {formalism} arcs yet, "
            "so one would be untestable"
        )

    return raise_it


_NORMALIZERS = {
    Formalism.CATIB: _from_catib,
    Formalism.SIBAWAYH: _identity,
    Formalism.UD: _unimplemented(Formalism.UD),
    Formalism.PADT: _unimplemented(Formalism.PADT),
}


def normalize_heads(heads: Sequence[int], formalism: Formalism) -> tuple[int, ...]:
    """Head indices in i'rab convention, from head indices in `formalism`."""
    try:
        normalizer = _NORMALIZERS[formalism]
    except KeyError:  # pragma: no cover - unreachable while the enum is closed
        raise ArcError(f"unknown formalism {formalism!r}") from None
    return normalizer(heads)


def normalize_arcs(tokens: Sequence[Token], formalism: Formalism) -> list[Token]:
    """Return copies of `tokens` whose heads follow i'rab convention.

    Pure: the tokens handed in are not touched. Only `head` and `provenance`
    change, and `provenance["head"]` is restamped to `ARCS` only on the tokens
    whose head actually moved — so a reader can see which arcs this stage was
    responsible for rather than having it claim the whole tree.
    """
    if not tokens:
        return []

    unparsed = [token.id for token in tokens if token.head is None]
    if unparsed:
        raise ArcError(f"tokens {unparsed} have no head; run `attach` before normalizing")

    heads = [token.head for token in tokens if token.head is not None]
    normalized = normalize_heads(heads, formalism)

    return [
        token
        if head == token.head
        else token.model_copy(
            update={"head": head, "provenance": {**token.provenance, "head": Source.ARCS}}
        )
        for token, head in zip(tokens, normalized, strict=True)
    ]

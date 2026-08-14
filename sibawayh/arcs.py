"""Arc normalization: rewrite a backend's arcs into i'rab convention.

The three schemes disagree structurally, not just in vocabulary, so this cannot
be one pass. A backend declares its `Formalism` and normalization dispatches on
it; each convention gets its own function, and adding a backend costs one more.

What each has to fix:

* **CATiB** — prepositions already head their objects (`OBJ` is "object of verb,
  preposition, or deverbal noun"), so no flip there. Nominal sentences do need
  re-rooting: CATiB heads them at the predicate, i'rab at the مبتدأ.
* **UD** — the full job: `case`, `mark`, `cop`/`aux` all point the wrong way, and
  the root is the content word.

Coordination is left alone under every formalism — a known gap, as planned.

Implemented in step 9.
"""

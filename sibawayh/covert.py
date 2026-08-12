"""Covert pronoun (ضمير مستتر) insertion.

No parser emits a node for a token that is not there; we insert it. Inserted
tokens carry `inserted: true` and must be excluded from treebank scoring.

Implemented in commit 10.
"""

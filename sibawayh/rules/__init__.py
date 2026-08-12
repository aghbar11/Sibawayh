"""The i'rab rule layer.

A rule is a predicate over `(token, head, sentence)` returning
`(irab_role, rule_id, evidence)`. Registry with priority ordering and
first-match-wins; no rule firing means abstention, never a guess.

Skeleton lands in commit 11, rules in commit 12.
"""

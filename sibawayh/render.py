"""LLM rendering of structured evidence into Arabic i'rab prose and hint text.

The LLM renders; it does not decide roles. Output is schema-validated with one
retry, then degrades to morphology-only.

Implemented in commit 15.
"""

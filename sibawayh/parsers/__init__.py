"""Parser backends behind a single interface.

The licensing firewall lives here. `PadtParser` is trained on LDC2018T08 and is
evaluation-only; `FreeParser` is safe to ship. Nothing outside this package may
know which backend is running.

Interface lands in commit 7.
"""

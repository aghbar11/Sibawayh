"""CAMeL Tools wrapper: disambiguation, morphological features, clitic segmentation.

This module is the *only* place that knows CAMeL's terse feature codes
(`asp`, `mod`, `cas`, `stt`, `vox`, `enc0`, `prc0`-`prc3`). Everything downstream
sees our vocabulary. See the mapping table in CLAUDE.md.

Implemented in commit 5.
"""

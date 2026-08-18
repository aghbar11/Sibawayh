"""Sibawayh — Arabic i'rab analysis pipeline.

Every pipeline stage is a pure function over tokens. Stage order:

    normalize -> morphology -> parser -> arcs -> covert -> rules -> renderers

`parser_label` (attachment, from the parser) and `irab_role` (from the rule
engine) are separate fields and must not be conflated.
"""

__version__ = "0.1.0"

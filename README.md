# Sibawayh (سيبويه)

Produces Arabic **إعراب** for a typed sentence, and teaches it by walking the student through
the dependency tree with graded hints instead of handing over the answer.

Register: Modern Standard Arabic.

## Layout

```
sibawayh/
  normalize.py   orthographic normalization
  morphology.py  CAMeL Tools wrapper — the only module that knows CAMeL's feature codes
  parsers/       parser backends behind one interface (licensing firewall)
  arcs.py        UD -> i'rab arc flipping
  covert.py      covert pronoun (ضمير مستتر) insertion
  rules/         i'rab role derivation
  render.py      LLM rendering of evidence into Arabic prose
  schema.py      pydantic token/sentence models
data/eval/       hand-verified evaluation sentences — the spec
data/ldc/        licensed PADT data, never in version control
tests/
```

## Pipeline

```
raw text -> normalize -> morphology -> parser (heads only) -> arc normalization
         -> covert pronoun insertion -> rule engine -> LLM rendering -> validate -> UI
```

The parser gives attachment. The rule engine gives roles. `parser_label` and `irab_role` stay
separate fields throughout.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

Heavier dependencies install per phase: `.[morphology]` (CAMeL Tools), `.[parser]` (Stanza),
`.[api]` (FastAPI).

## Licensing

PADT (LDC2018T08) is under an LDC Reduced-License for research and education. A model trained
on it cannot ship commercially, so the parser is swappable behind an interface and anything
PADT-derived is gated behind an environment variable. `data/ldc/` is gitignored.

"""The whole chain, in one place, holding its models between sentences.

Every stage already exists and every stage is a pure function. What did not exist
was anything that ran them in order, so the CLI spelled the chain out by hand and
a second caller would have spelled it out again — slightly differently, and the
difference would have been a bug nobody could see.

    text → morphology → parse → arcs → covert pronouns → rules → validate

**Loading is the reason this is a class and not a function.** The CATiB parser
and the CAMeL BERT disambiguator take the better part of a minute to load. A
command-line run pays that once and exits; a server would pay it on every request
unless something holds them, and half a minute per sentence is not a product. So
the components are built on first use and kept, and a server warms them at
startup rather than making the first student wait.

**Both components are injectable**, which is what lets a test drive the chain
without loading anything. Nothing here knows which parser backend is running —
that is `parsers/`' business, and the whole point of `Parser.formalism` is that
arc normalization can ask rather than assume.
"""

from __future__ import annotations

from sibawayh.arcs import normalize_arcs
from sibawayh.covert import insert_covert_pronouns
from sibawayh.morphology import CamelMorphology
from sibawayh.parsers import Parser, attach
from sibawayh.rules import apply_rules
from sibawayh.schema import Sentence
from sibawayh.validate import enforce


class Pipeline:
    """Text in, an analyzed `Sentence` out.

    Holds its morphology analyzer and parser once built. Not thread-safe to
    construct — a server should warm it before serving — but analysis itself only
    reads them.
    """

    def __init__(
        self,
        morphology: CamelMorphology | None = None,
        parser: Parser | None = None,
    ) -> None:
        self._morphology = morphology
        self._parser = parser

    @property
    def morphology(self) -> CamelMorphology:
        if self._morphology is None:
            self._morphology = CamelMorphology()
        return self._morphology

    @property
    def parser(self) -> Parser:
        if self._parser is None:
            from sibawayh.parsers.catib import CatibParser

            self._parser = CatibParser()
        return self._parser

    @property
    def loaded(self) -> bool:
        """Whether both components are built, so a caller can report readiness
        rather than discover it by waiting."""
        return self._morphology is not None and self._parser is not None

    def warm(self) -> None:
        """Build both components now. A server calls this at startup so that the
        first sentence costs what every other sentence costs."""
        _ = self.morphology, self.parser

    def analyze(self, text: str, normalize_input: bool = True) -> Sentence:
        """Run every stage over `text`.

        The order is not arbitrary. Arcs are normalized before covert pronouns
        are inserted, because insertion renumbers tokens and normalization reads
        head integers. Rules run after insertion, because a covert pronoun is a
        token rules have to see. Validation runs last, because it judges the
        result of all of it.
        """
        sentence = self.morphology.analyze(text, normalize_input=normalize_input)
        parser = self.parser
        tokens = enforce(
            apply_rules(
                insert_covert_pronouns(
                    normalize_arcs(attach(sentence.tokens, parser), parser.formalism)
                )
            )
        )
        return sentence.model_copy(update={"tokens": tokens})

from caselens.domain.services.ruling_locator import RulingLocator


class DispositiveExtractor:
    """The ruling as one string: the Court's final `WHEREFORE ...` (or `ACCORDINGLY ...`) paragraphs up to
    the closing `SO ORDERED`. Where they are is `RulingLocator`'s job.

    The ruling often spans several paragraphs (GR 183905: "WHEREFORE, the petition in G.R. No. 184275 is
    EXPUNGED ... / The petition in G.R. No. 183905 is DISMISSED ...").
    """

    def __init__(self, locator: RulingLocator | None = None) -> None:
        self._locator = locator or RulingLocator()

    def extract(self, paragraphs: list[str]) -> str | None:
        located = self._locator.locate(paragraphs)
        if located is None:
            return None
        return " ".join(paragraphs[i] for i in located.indexes())

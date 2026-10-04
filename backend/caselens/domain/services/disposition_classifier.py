import re

from caselens.domain.value_objects import Disposition

# Lawphil decisions capitalise the operative verb ("we GRANT the petition"), so only
# UPPERCASE verbs count. Ordinary lowercase prose ("without granting") is ignored.
_VERBS = {
    "GRANT": re.compile(r"\bGRANT(?:ED)?\b"),
    "DENY": re.compile(r"\bDENY\b|\bDENIED\b"),
    "DISMISS": re.compile(r"\bDISMISS(?:ED)?\b"),
    "REVERSE": re.compile(r"\bREVERSE[D]?\b"),
    "AFFIRM": re.compile(r"\bAFFIRM(?:ED)?\b"),
}


_PARTIAL = re.compile(r"\b(?:partly|partially|in part)\b", re.IGNORECASE)


class DispositionClassifier:
    """Reads the dispositive paragraph (the `WHEREFORE ...` clause) of a decision."""

    def classify(self, dispositive_text: str | None) -> Disposition:
        if not dispositive_text:
            return Disposition.UNKNOWN
        found = {verb for verb, pattern in _VERBS.items() if pattern.search(dispositive_text)}

        if {"GRANT", "DENY"} <= found or ("GRANT" in found and _PARTIAL.search(dispositive_text)):
            return Disposition.PARTIALLY_GRANTED
        for verb, disposition in (
            ("GRANT", Disposition.GRANTED),
            ("DENY", Disposition.DENIED),
            ("DISMISS", Disposition.DISMISSED),
            ("REVERSE", Disposition.REVERSED),
            ("AFFIRM", Disposition.AFFIRMED),
        ):
            if verb in found:
                return disposition
        return Disposition.UNKNOWN

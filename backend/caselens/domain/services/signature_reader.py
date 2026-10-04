import re

_CONCUR_HEADING = re.compile(r"^WE CONCUR\b", re.IGNORECASE)
# "LEONARDO A. QUISUMBING Associate Justice", "REYNATO S. PUNO Chief Justice",
# "... Associate Justice Chairman" (division chair)
_SIGNATURE = re.compile(
    r"^(?P<name>[A-Z][A-Za-z\.\-' ,]+?)\s+(?:Associate|Chief) Justice(?:\s+Chairman.*)?$"
)


class SignatureReader:
    """Names of the justices who signed under "WE CONCUR:" (in page order).

    The ponente signs above that heading and is excluded; the certification and
    attestation signatures after the block are not included.
    """

    def concurring_justices(self, paragraphs: list[str]) -> list[str]:
        start = next((i for i, p in enumerate(paragraphs) if _CONCUR_HEADING.match(p)), None)
        if start is None:
            return []
        names: list[str] = []
        for paragraph in paragraphs[start + 1 :]:
            match = _SIGNATURE.match(paragraph)
            if not match:
                break  # first non-signature line (e.g. "C E R T I F I C A T I O N") ends the block
            names.append(match.group("name").strip())
        return names

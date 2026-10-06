"""Readable names for a case, a justice and a division, from the Court's ALL-CAPS captions.

The Python twin of `shortCaseName`, `justiceName` and `divisionName` in `frontend/src/lib/format.ts`: the screen and the Word files must
name a case the same way ("Marcos v. Manglapus"). Keep the two in step; both are tested on the same real captions."""
import re

_SMALL_WORDS = {"of", "the", "and", "on", "for", "in", "a", "an", "to", "at", "by", "vs", "v"}
_ROMAN = {"II", "III", "IV", "VI", "VII", "VIII", "IX"}  # "PIMENTEL III" stays "Pimentel III"
_ACRONYMS = {"COMELEC", "CHED", "PRC", "DOJ", "NLRC", "GSIS", "SSS", "DENR", "DAR", "PNB", "BIR", "LTO", "MWSS", "NAPOCOR", "ABS-CBN", "COA", "CSC", "CA", "RTC"}
_ABBREVIATIONS = {"inc", "co", "corp", "ltd", "jr", "sr", "bros", "al"}
_PARTY_ROLES = r"(?:Petitioners?|Respondents?|Appellants?|Appellees?|Plaintiffs?|Defendants?)"
_NOT_PART_OF_NAME = r"Jr|Sr|Inc|Co|Corp|Ltd|II|III|IV"


def title_case(text: str) -> str:
    """The Court prints parties in ALL CAPS. Return normal capitalisation, keeping acronyms. Mixed-case text is left alone."""
    if text != text.upper():
        return text
    out: list[str] = []
    for index, word in enumerate(re.split(r"(\s+)", text)):
        if word == "" or word.isspace():
            out.append(word)
            continue
        bare = re.sub(r"[^A-Za-z-]", "", word)
        if bare in _ACRONYMS or bare in _ROMAN:
            out.append(word)
            continue
        if re.fullmatch(r"[^AEIOUaeiou]{2,4}", bare) and bare == bare.upper() and not re.fullmatch(r"MR|MS|JR|SR|DR|ST", bare):
            out.append(word)  # PNB-style consonant clusters are acronyms
            continue
        lower = word.lower()
        letters = re.sub(r"[^a-z]", "", lower)
        if len(letters) == 1:
            out.append(word.upper())  # an initial: "A.", "V."
        elif index > 0 and letters in _SMALL_WORDS:
            out.append(lower)
        else:
            out.append(re.sub(r"(^|[-.(])([a-z])", lambda m: m.group(1) + m.group(2).upper(), lower))
    return "".join(out)


# What a caption adds to a party's name that is not the name: an aside in brackets ("(formerly AASJS)", with a footnote number glued after
# it), and the people acting for an organisation ("OFFICERS/MEMBERS SAMSON S. ALCANTARA, ...", "represented by its President, ...").
_ASIDE = re.compile(r"\s*\([^()]*\)\d*")
_ACTING_FOR = re.compile(r"\s+(?:(?:officers?|members?)\s*(?:/|and)\s*(?:officers?|members?)|represented\s+by)\b.*$", re.IGNORECASE)


def _strip_party_notes(side: str) -> str:
    """ "ABAKADA GURO PARTY LIST (formerly AASJS)1 OFFICERS/MEMBERS SAMSON S. ALCANTARA, ..." -> "ABAKADA GURO PARTY LIST" """
    return _ACTING_FOR.sub("", _ASIDE.sub("", side)).strip(" ,;")


def _trim_end(text: str) -> str:
    trimmed = re.sub(r"[,\s]+$", "", text)
    if trimmed.endswith("."):
        words = trimmed[:-1].split()
        if (words[-1].lower() if words else "") not in _ABBREVIATIONS:
            trimmed = re.sub(r"[,\s]+$", "", trimmed[:-1])
    return trimmed


def _lead(side: str) -> tuple[str, bool]:
    """The first party of a side, and whether there are more. A comma that belongs to a name ("Marcelo, Jr.") does not end it."""
    head, *others = re.split(rf"(?:,|;)\s+(?!(?:{_NOT_PART_OF_NAME})\b)", side, flags=re.IGNORECASE)
    name, *joined = re.split(r"\s+and\s+", head)  # the Court writes the joining "and" in lowercase
    return name, bool(others or joined)


def short_case_name(title: str | None) -> str:
    """"FERDINAND E. MARCOS, ..., petitioners, vs. HONORABLE RAUL MANGLAPUS, ..." -> "Ferdinand E. Marcos et al. v. Honorable Raul Manglapus et al.\""""
    if not title:
        return "Untitled case"
    # "vs" is the divider when the caption has one; a lone "V." can be a middle initial ("RADITO V. PADRIGANO").
    parts = re.split(r"\s+vs\.?\s+", title, flags=re.IGNORECASE) if re.search(r"\s+vs\.?\s+", title, flags=re.IGNORECASE) else re.split(r"\s+v\.?\s+", title, flags=re.IGNORECASE)
    if len(parts) < 2:
        name, more = _lead(_strip_party_notes(re.sub(rf",\s*{_PARTY_ROLES}.*$", "", title, flags=re.IGNORECASE).strip()))
        return f"{title_case(name)}{' et al.' if more else ''}"

    def clean(side: str) -> str:
        return _trim_end(_strip_party_notes(re.sub(rf",?\s*{_PARTY_ROLES}\b.*$", "", side, flags=re.IGNORECASE)))

    first, first_more = _lead(clean(parts[0]))
    second, second_more = _lead(clean(" vs. ".join(parts[1:])))
    return f"{title_case(first)}{' et al.' if first_more else ''} v. {title_case(second)}{' et al.' if second_more else ''}"


_ORGANISATION_WORDS = re.compile(
    r"\b(?:Association|Corporation|Corp|Company|Co|Inc|Union|Bank|Commission|Department|Republic|People|City|Municipality|Province|Congress|Senate|"
    r"House|Court|Office|Board|Authority|Agency|Foundation|Club|Federation|Center|Centre|Institute|University|College|School|Hospital|Philippines|"
    r"Government|Bureau|Council|Society|Cooperative|Partnership|Enterprises|Industries|Services|Insurance|Party|Partylist|List|Alliance|"
    r"Coalition|Movement|Organization|Organisation|Group|Network)\b",
    re.IGNORECASE,
)
_TITLES = r"(?:Honorable|Hon\.|Atty\.|Attorney|Secretary|Executive Secretary|Director|Commissioner|Judge|Justice|Mayor|Governor|Dr\.|Engr\.)"


def surname_only(short_name: str) -> str:
    """"Ferdinand E. Marcos et al. v. Honorable Raul Manglapus et al." -> "Marcos v. Manglapus": the form lawyers cite. Only a PERSON is
    cut down to a surname; an organisation keeps its name ("Review Center Association of the Philippines v. Ermita")."""

    def cited(party: str) -> str:
        party = re.sub(r"\s+et al\.?$", "", party.strip())
        party = re.sub(rf"^(?:{_TITLES}\s+)+", "", party)
        if _ORGANISATION_WORDS.search(party) or not party.split():
            return party
        return party.split(",")[0].split()[-1]

    sides = re.split(r"\s+v\.\s+", short_name, maxsplit=1)
    if len(sides) < 2:
        return short_name
    return f"{cited(sides[0])} v. {cited(sides[1])}"


def justice_name(name: str) -> str:
    """"REYNATO S. PUNO" -> "Reynato S. Puno", "VELASCO, JR." -> "Velasco, Jr."."""
    return title_case(name)


def division_name(division: str) -> str:
    """"EN BANC" -> "En Banc"."""
    return re.sub(r"\b[a-z]", lambda m: m.group(0).upper(), division.lower())

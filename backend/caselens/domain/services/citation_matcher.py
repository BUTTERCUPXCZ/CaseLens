import re

from caselens.domain.entities import Case
from caselens.domain.value_objects import ClaimedCitation, MatchResult, MatchStatus

# Words that carry no identity in a case title ("Review Center v Ermita" vs the full
# "REVIEW CENTER ASSOCIATION OF THE PHILIPPINES, ... vs. EXECUTIVE SECRETARY EDUARDO ERMITA").
_TITLE_STOPWORDS = {"v", "vs", "versus", "of", "the", "and", "et", "al"}


class CitationMatcher:
    """Compares what a student *claims* with the official record.

    Only facts the official page contains are checked: G.R. number, year/date and the
    parties' names. The reporter citation ("538 SCRA 428") is not on Lawphil's page, so
    it is reported as *unverified* and never as correct or incorrect.
    """

    def match(self, claimed: ClaimedCitation, case: Case) -> MatchResult:
        mismatches: dict[str, dict] = {}

        # A joint decision settles several petitions: citing any of its numbers is correct.
        if claimed.gr_number.value not in case.all_numbers:
            mismatches["gr_no"] = {"claimed": str(claimed.gr_number), "official": str(case.gr_no)}

        self._check_date(claimed, case, mismatches)

        if claimed.title and case.title and not self._title_matches(claimed.title, case.title):
            mismatches["title"] = {"claimed": claimed.title, "official": case.title}

        unverified = ["reporter"] if claimed.reporter else []
        status = MatchStatus.MISMATCH if mismatches else MatchStatus.MATCH
        return MatchResult(status, mismatches, unverified)

    @staticmethod
    def _check_date(claimed: ClaimedCitation, case: Case, mismatches: dict) -> None:
        official = case.decision_date
        if official is None:
            return
        if claimed.claimed_year is not None and claimed.claimed_year != official.year:
            mismatches["year"] = {"claimed": claimed.claimed_year, "official": official.year}
        elif claimed.claimed_date is not None and claimed.claimed_date != official:
            mismatches["date"] = {
                "claimed": claimed.claimed_date.isoformat(),
                "official": official.isoformat(),
            }

    @classmethod
    def _title_matches(cls, claimed: str, official: str) -> bool:
        wanted = cls._tokens(claimed)
        return bool(wanted) and wanted <= cls._tokens(official)

    @staticmethod
    def _tokens(text: str) -> set[str]:
        words = re.findall(r"[a-z0-9]+", text.lower())
        return {w for w in words if w not in _TITLE_STOPWORDS}

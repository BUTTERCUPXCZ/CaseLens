from caselens.application.ports.queries import InsightQueries
from caselens.domain.insights import TrendsReport

# Counts over a handful of cases are anecdotes, not trends. Below this the report says so
# instead of presenting a ranking as if it meant something.
MINIMUM_CASES_FOR_TRENDS = 5


class GetTrends:
    def __init__(self, queries: InsightQueries, minimum_cases: int = MINIMUM_CASES_FOR_TRENDS) -> None:
        self._queries = queries
        self._minimum = minimum_cases

    def execute(self, limit: int = 10) -> TrendsReport:
        total = self._queries.total_cases()
        return TrendsReport(
            total_cases=total,
            minimum_cases=self._minimum,
            enough_data=total >= self._minimum,
            top_statutes=self._queries.top_statutes(limit),
            dispositions_by_year=self._queries.dispositions_by_year(),
            most_cited_cases=self._queries.most_cited_cases(limit),
            cases_per_ponente=self._queries.cases_per_ponente(limit),
        )

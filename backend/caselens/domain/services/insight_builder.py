from caselens.domain.entities import Case
from caselens.domain.insights import CaseInsights, OpinionRef
from caselens.domain.services.dispositive_extractor import DispositiveExtractor
from caselens.domain.services.signature_reader import SignatureReader


class CaseInsightBuilder:
    """Key findings for one stored case, read straight from its official text."""

    def __init__(
        self,
        dispositive: DispositiveExtractor | None = None,
        signatures: SignatureReader | None = None,
    ) -> None:
        self._dispositive = dispositive or DispositiveExtractor()
        self._signatures = signatures or SignatureReader()

    def build(self, case: Case) -> CaseInsights:
        paragraphs = case.full_text.split("\n")
        return CaseInsights(
            case_id=case.id,
            gr_no=str(case.gr_no),
            title=case.title,
            source_url=case.source_url,
            decision_date=case.decision_date,
            doc_type=case.doc_type,
            division=case.division,
            ponente=case.ponente,
            disposition=case.disposition,
            ruling=self._dispositive.extract(paragraphs),
            concurring_justices=self._signatures.concurring_justices(paragraphs),
            opinions=[OpinionRef(o.kind, o.author) for o in case.opinions],
            statutes=list(case.statutes),
            cited_cases=list(case.cited_cases),
            footnote_count=len(case.footnotes),
            word_count=len(case.full_text.split()),
        )

from caselens.application.ports.gateways import DocumentTextExtractor, UploadedFileReader
from caselens.domain.errors import UnsupportedDocumentError


class CompositeDocumentExtractor(UploadedFileReader):
    """Picks the right format-specific extractor by filename.

    Supporting a new format means writing one `DocumentTextExtractor` and adding it
    to the list in the composition root; nothing here changes (Open/Closed).
    """

    def __init__(self, extractors: list[DocumentTextExtractor]) -> None:
        self._extractors = extractors

    def read(self, filename: str, data: bytes) -> str:
        for extractor in self._extractors:
            if extractor.supports(filename):
                return extractor.extract(data)
        raise UnsupportedDocumentError(f"Unsupported file type: {filename}")

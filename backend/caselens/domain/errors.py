class DomainError(Exception):
    """Base class for errors raised by business rules."""


class UnsupportedDocumentError(DomainError):
    """The uploaded file type cannot be read."""


class DocumentExtractionError(DomainError):
    """A supported file could not be read (corrupt, encrypted, empty)."""


class CaseNotFoundError(DomainError):
    """No official record exists (or could be resolved) for the request."""


class DuplicateCaseError(DomainError):
    """A case with this source URL is already stored."""


class InvalidSourceUrlError(DomainError):
    """The URL is not an official case page we are willing to fetch."""


class CaseParseError(DomainError):
    """The official page did not have the structure the parser relies on."""


class SourceUnavailableError(DomainError):
    """The upstream legal source could not be reached or returned bad data."""


class AiUnavailableError(DomainError):
    """The AI service could not be reached, refused the key, or returned something unusable."""


class AiCreditError(AiUnavailableError):
    """The AI service refused because the account has no credit or billing left (Gemini 402): nothing helps until it is topped up."""

    STUDENT_MESSAGE = "The AI service has run out of credit, so nothing new can be written for now. Please tell the person who runs CaseLens."


class DigestNotFoundError(DomainError):
    """No digest with this id (or none yet for this case)."""


class InvalidDigestEditError(DomainError):
    """The edit cannot be applied: unknown field, or a passage outside the decision's body."""


class JobQueueUnavailableError(DomainError):
    """The background-job broker (RabbitMQ) could not be reached, so the work could not be queued."""

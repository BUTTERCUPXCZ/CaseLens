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
    """The AI service refused because the key has no credit left (Gemini 402) or has used up its daily allowance (a free-tier key,
    429 with a per-day quota): asking again cannot help until credit or billing is added, or the next day."""

    STUDENT_MESSAGE = (
        "The AI key has run out of credit (or used up today's free allowance), so nothing new can be written right now. "
        "Add credit or turn on billing for the key, or add another AI's key, in Settings. Then click Try again."
    )


class AiKeyError(AiUnavailableError):
    """The AI service refused the key itself (not valid, deleted, or not a Gemini key): nothing helps until a working key is saved."""

    STUDENT_MESSAGE = (
        "Your AI key is not valid, so the AI refused it. Open Settings, paste the key again from the AI's website "
        "(Groq, DeepSeek, OpenRouter or Google AI Studio), save it, then click Try again."
    )


class AiRateLimitError(AiUnavailableError):
    """The key's per-minute limit was reached on every model (a free key allows only a few calls a minute): it passes, but a
    bulk upload needs a key with billing on."""

    STUDENT_MESSAGE = (
        "Your AI key allows only a few requests per minute (a free key does), and that limit was reached. Wait a few minutes, "
        "then click Try again. To digest many cases at once, use a key with billing on, or add another AI's key in Settings."
    )


class AiInvalidRequestError(AiUnavailableError):
    """The AI service refused the request itself (a 4xx that is not about the key, credit or rate): asking again, or asking another
    provider the same thing, would only repeat the refusal, so it is not retried anywhere."""

    STUDENT_MESSAGE = (
        "The AI refused this request as it was sent, so asking again would not help. This is a problem in CaseLens, not your file: "
        "try another case, and tell the person who set up CaseLens."
    )


class DigestNotFoundError(DomainError):
    """No digest with this id (or none yet for this case)."""


class InvalidDigestEditError(DomainError):
    """The edit cannot be applied: unknown field, or a passage outside the decision's body."""


class JobQueueUnavailableError(DomainError):
    """The background-job broker (RabbitMQ) could not be reached, so the work could not be queued."""

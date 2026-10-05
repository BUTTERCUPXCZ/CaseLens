from abc import ABC, abstractmethod

from caselens.domain.digest_v2 import Section


class ReviewEditRepository(ABC):
    """The sections a student rewrote, per review (upload) and digest."""

    @abstractmethod
    def for_digest(self, batch_id: int, digest_id: int) -> dict[Section, str]: ...

    @abstractmethod
    def save(self, batch_id: int, digest_id: int, section: Section, text: str) -> None:
        """Keep the student's text for this section (replacing an earlier edit of it)."""

    @abstractmethod
    def remove(self, batch_id: int, digest_id: int, section: Section) -> None:
        """Forget the edit: the section shows the AI's text again."""

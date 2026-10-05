"""The subject tags a case is filed under in the library (the client's upload screen: Civil Law, Criminal Law, Remedial Law, ...).
A case can carry several. The student labels the case; the system never guesses a tag."""
from dataclasses import dataclass

# In the order of the client's upload screen.
DEFAULT_SUBJECTS: tuple[str, ...] = (
    "Civil Law",
    "Criminal Law",
    "Remedial Law",
    "Constitutional Law",
    "Labor Law",
    "Commercial Law",
    "Taxation Law",
    "Legal Ethics",
    "Political Law",
    "Litigation",
    "Administrative Law",
)

SOURCE_STUDENT = "student"  # the student chose it on the case page
SOURCE_BATCH = "batch"  # chosen once for a whole upload


@dataclass(frozen=True)
class Subject:
    id: int
    name: str


@dataclass(frozen=True)
class SubjectCount:
    """A tag with the number of main cases carrying it (a case with two tags counts under both). `subject_id` None = cases with no tag yet."""

    subject_id: int | None
    name: str
    count: int

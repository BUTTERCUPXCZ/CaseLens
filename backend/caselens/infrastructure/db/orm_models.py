"""SQLAlchemy persistence models.

These are NOT the domain entities. Repositories map between the two (see mappers.py),
so the domain layer never imports SQLAlchemy.
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, LargeBinary, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from caselens.infrastructure.db.base import Base


class CaseModel(Base):
    """One official Lawphil document. Keyed on source_url, never on gr_no alone:
    a G.R. number can have a decision, resolutions and separate-opinion files."""

    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    gr_no: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str | None] = mapped_column(Text)
    decision_date: Mapped[date | None] = mapped_column(Date)
    doc_type: Mapped[str] = mapped_column(String(32), server_default="decision")
    ponente: Mapped[str | None] = mapped_column(String(128))
    division: Mapped[str | None] = mapped_column(String(64))
    disposition: Mapped[str | None] = mapped_column(String(32))
    source_url: Mapped[str] = mapped_column(Text, unique=True)
    raw_html: Mapped[str] = mapped_column(Text)
    full_text: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    parser_version: Mapped[int] = mapped_column(Integer)
    # Every G.R. number the page prints (a joint decision has several); empty on older rows.
    numbers: Mapped[list[str]] = mapped_column(ARRAY(String(32)), server_default=text("'{}'"))

    footnotes: Mapped[list["CaseFootnoteModel"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    opinions: Mapped[list["CaseOpinionModel"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    statutes: Mapped[list["CaseStatuteModel"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    citations: Mapped[list["CaseCitationModel"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index(
            "ix_cases_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
        Index("ix_cases_numbers", "numbers", postgresql_using="gin"),
        Index(
            "ix_cases_full_text_fts",
            text("to_tsvector('english', full_text)"),
            postgresql_using="gin",
        ),
    )


class CaseOpinionModel(Base):
    """Separate/concurring/dissenting opinion on the same Lawphil page."""

    __tablename__ = "case_opinions"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    author: Mapped[str | None] = mapped_column(String(128))
    text: Mapped[str] = mapped_column(Text)

    case: Mapped[CaseModel] = relationship(back_populates="opinions")


class CaseFootnoteModel(Base):
    __tablename__ = "case_footnotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    opinion_id: Mapped[int | None] = mapped_column(
        ForeignKey("case_opinions.id", ondelete="CASCADE")
    )
    number: Mapped[int] = mapped_column(Integer)
    anchor: Mapped[str] = mapped_column(String(32))
    text: Mapped[str] = mapped_column(Text)

    case: Mapped[CaseModel] = relationship(back_populates="footnotes")


class CaseStatuteModel(Base):
    __tablename__ = "case_statutes"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    statute_type: Mapped[str] = mapped_column(String(16))
    number: Mapped[str] = mapped_column(String(32))
    raw: Mapped[str] = mapped_column(Text)

    case: Mapped[CaseModel] = relationship(back_populates="statutes")

    __table_args__ = (Index("ix_case_statutes_type_number", "statute_type", "number"),)


class CaseCitationModel(Base):
    __tablename__ = "case_citations"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    cited_title: Mapped[str] = mapped_column(Text)
    cited_gr_no: Mapped[str | None] = mapped_column(String(32), index=True)
    source: Mapped[str] = mapped_column(String(16))  # body | footnote
    footnote_number: Mapped[int | None] = mapped_column(Integer)

    case: Mapped[CaseModel] = relationship(back_populates="citations")


class MonthIndexModel(Base):
    """Cache of a Lawphil month index page so each one is fetched once."""

    __tablename__ = "month_indexes"

    url: Mapped[str] = mapped_column(Text, primary_key=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    links: Mapped[list[str]] = mapped_column(JSONB)


class UploadModel(Base):
    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    # The original file (up to 10 MB). Deferred: status polling never loads it; only building the finished reviewer does.
    file_data: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)
    status: Mapped[str] = mapped_column(String(16), server_default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    citations: Mapped[list["UploadCitationModel"]] = relationship(
        back_populates="upload", cascade="all, delete-orphan"
    )


class UploadCitationModel(Base):
    __tablename__ = "upload_citations"

    id: Mapped[int] = mapped_column(primary_key=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"), index=True)
    raw_citation: Mapped[str] = mapped_column(Text)
    gr_no: Mapped[str] = mapped_column(String(32), index=True)
    claimed_year: Mapped[int | None] = mapped_column(Integer)
    claimed_title: Mapped[str | None] = mapped_column(Text)
    claimed_date: Mapped[date | None] = mapped_column(Date)
    reporter: Mapped[str | None] = mapped_column(String(64))
    matched_case_id: Mapped[int | None] = mapped_column(
        ForeignKey("cases.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(16), server_default="pending")
    mismatches: Mapped[dict | None] = mapped_column(JSONB)
    unverified: Mapped[list | None] = mapped_column(JSONB)
    message: Mapped[str | None] = mapped_column(Text)

    upload: Mapped[UploadModel] = relationship(back_populates="citations")
    matched_case: Mapped[CaseModel | None] = relationship()


class CatalogEntryModel(Base):
    """One row of one of Lawphil's monthly lists (a case we can open, not yet saved)."""

    __tablename__ = "catalog_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_url: Mapped[str] = mapped_column(Text)
    link_number: Mapped[str] = mapped_column(String(32))  # the number in the link: the page we open
    label_key: Mapped[str] = mapped_column(Text)  # the numbers printed on the row, joined: tells joint rows apart
    title: Mapped[str] = mapped_column(Text)
    decision_date: Mapped[date | None] = mapped_column(Date)
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    index_url: Mapped[str] = mapped_column(Text)

    numbers: Mapped[list["CatalogNumberModel"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("source_url", "label_key", name="uq_catalog_entries_row"),
        Index("ix_catalog_entries_year_month", "year", "month"),
        Index(
            "ix_catalog_entries_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
    )


class CatalogNumberModel(Base):
    """Every G.R. number printed on a row (a joint decision has several), searchable by prefix."""

    __tablename__ = "catalog_numbers"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("catalog_entries.id", ondelete="CASCADE"))
    number: Mapped[str] = mapped_column(String(32))

    entry: Mapped[CatalogEntryModel] = relationship(back_populates="numbers")

    __table_args__ = (
        Index("ix_catalog_numbers_number_prefix", "number", postgresql_ops={"number": "text_pattern_ops"}),
        Index("ix_catalog_numbers_entry_id", "entry_id"),
    )


class CatalogMonthModel(Base):
    """Which monthly lists have been read, so a build can stop and resume."""

    __tablename__ = "catalog_months"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    month: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(16))  # read | broken
    entries: Mapped[int] = mapped_column(Integer)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DigestModel(Base):
    """A student's digest of one case, inside one uploaded reviewer (or stand-alone when upload_id is null)."""

    __tablename__ = "digests"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    upload_id: Mapped[int | None] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"), index=True)
    template: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), server_default="pending")
    error: Mapped[str | None] = mapped_column(Text)
    fields: Mapped[list] = mapped_column(JSONB)
    model: Mapped[str | None] = mapped_column(String(64))
    prompt_version: Mapped[str | None] = mapped_column(String(32))
    parser_version: Mapped[int | None] = mapped_column(Integer)
    ai_answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class JobLockModel(Base):
    """A held lock for background work. A lock past `locked_until` is free again, so a crashed worker cannot block it forever."""

    __tablename__ = "job_locks"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    locked_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

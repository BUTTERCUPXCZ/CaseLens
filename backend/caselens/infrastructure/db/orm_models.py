"""SQLAlchemy persistence models.

These are NOT the domain entities. Repositories map between the two (see mappers.py),
so the domain layer never imports SQLAlchemy.
"""
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, LargeBinary, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.types import JSON, TypeDecorator

# One schema for both databases: PostgreSQL (the web version) keeps its JSONB and ARRAY columns; SQLite (the desktop app) stores
# the same values as JSON. Indexes that only PostgreSQL has (trigram, full-text, GIN) are created there only.
JSONDoc = JSON().with_variant(JSONB(), "postgresql")


def ListOf(item):
    return JSON().with_variant(ARRAY(item), "postgresql")


class UTCDateTime(TypeDecorator):
    """A moment in time, always UTC. PostgreSQL keeps the time zone itself; SQLite stores plain text, so the zone is put back on read
    (otherwise "Today, 9:10 PM" would be shown in the wrong zone)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is not None:
            value = value.astimezone(UTC)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value
from sqlalchemy.orm import Mapped, mapped_column, relationship

from caselens.infrastructure.db.base import Base


class SubjectModel(Base):
    """A subject tag (Civil Law, Constitutional Law, ...). Seeded by migration 0010, made the client's list by 0013."""

    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    sort_order: Mapped[int] = mapped_column(Integer)


class CaseSubjectModel(Base):
    """One tag on one case. A case can have several; `source` says who gave it ("student" or "batch")."""

    __tablename__ = "case_subjects"

    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(16), server_default="student")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())


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
        UTCDateTime(), server_default=func.now()
    )
    parser_version: Mapped[int] = mapped_column(Integer)
    # Every G.R. number the page prints (a joint decision has several); empty on older rows.
    numbers: Mapped[list[str]] = mapped_column(ListOf(String(32)), default=list)
    subjects: Mapped[list[SubjectModel]] = relationship(
        secondary="case_subjects", viewonly=True, order_by=SubjectModel.sort_order, lazy="selectin"
    )  # the tags; written through CaseSubjectModel
    # A page that only belongs to another case (a Resolution, the same decision under another G.R. number) points at its main case.
    main_case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id", ondelete="SET NULL"), index=True)

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
        ).ddl_if(dialect="postgresql"),
        Index("ix_cases_numbers", "numbers", postgresql_using="gin").ddl_if(dialect="postgresql"),
        Index(
            "ix_cases_full_text_fts",
            text("to_tsvector('english', full_text)"),
            postgresql_using="gin",
        ).ddl_if(dialect="postgresql"),
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
        UTCDateTime(), server_default=func.now()
    )
    links: Mapped[list[str]] = mapped_column(JSONDoc)


class UploadModel(Base):
    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    # The original file (up to 10 MB). Deferred: status polling never loads it; only building the finished reviewer does.
    file_data: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)
    status: Mapped[str] = mapped_column(String(16), server_default="pending")
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), server_default=func.now()
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
    mismatches: Mapped[dict | None] = mapped_column(JSONDoc)
    unverified: Mapped[list | None] = mapped_column(JSONDoc)
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
        ).ddl_if(dialect="postgresql"),
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
    read_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())


class DigestModel(Base):
    """A student's digest of one case, inside one uploaded reviewer (or stand-alone when upload_id is null)."""

    __tablename__ = "digests"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    upload_id: Mapped[int | None] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"), index=True)
    template: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), server_default="pending")
    error: Mapped[str | None] = mapped_column(Text)
    fields: Mapped[list] = mapped_column(JSONDoc)
    model: Mapped[str | None] = mapped_column(String(64))
    prompt_version: Mapped[str | None] = mapped_column(String(32))
    parser_version: Mapped[int | None] = mapped_column(Integer)
    ai_answered_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())


class AppSettingModel(Base):
    """A setting changed from the website's Settings page (the AI model); the rest comes from the host's environment."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())


class JobLockModel(Base):
    """A held lock for background work. A lock past `locked_until` is free again, so a crashed worker cannot block it forever."""

    __tablename__ = "job_locks"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    locked_until: Mapped[datetime] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())


class CaseDigestV2Model(Base):
    """The case digest of one main case for one topic scope (the client's format): its sections as JSON, written once and kept.
    `scope_key` '' is the standard digest; a scope ("Presidential powers") gets its own focused digest."""

    __tablename__ = "case_digests_v2"
    __table_args__ = (UniqueConstraint("case_id", "scope_key", name="uq_case_digests_v2_case_scope"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    scope: Mapped[str] = mapped_column(String(300), server_default="")  # as the student wrote it
    scope_key: Mapped[str] = mapped_column(String(300), server_default="")  # the same, lower-cased with spaces collapsed: finds a repeat
    state: Mapped[str] = mapped_column(String(16), server_default="pending")
    sections: Mapped[dict] = mapped_column(JSONDoc, default=dict)
    written: Mapped[int] = mapped_column(Integer, server_default="0")
    dropped: Mapped[int] = mapped_column(Integer, server_default="0")
    error: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(64))
    prompt_version: Mapped[str | None] = mapped_column(String(32))
    input_tokens: Mapped[int] = mapped_column(Integer, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, server_default="0")
    stage: Mapped[str | None] = mapped_column(String(16))  # while pending: queued, writing, checking or repairing (the progress bar)
    stage_at: Mapped[datetime | None] = mapped_column(UTCDateTime())  # when that step began
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())


class CaseQuestionModel(Base):
    """A question a student asked about a case, and its checked answer (sentences that cite the decision's paragraphs)."""

    __tablename__ = "case_questions"
    __table_args__ = (Index("ix_case_questions_case_batch", "case_id", "batch_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("bulk_batches.id", ondelete="CASCADE"))
    question: Mapped[str] = mapped_column(String(500))
    answer: Mapped[dict | None] = mapped_column(JSONDoc)
    state: Mapped[str] = mapped_column(String(16), server_default="pending")
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now(), index=True)


class ReviewDigestEditModel(Base):
    """The text a student typed over one section of a case digest, in one review. The shared AI digest is never changed."""

    __tablename__ = "review_digest_edits"
    __table_args__ = (UniqueConstraint("batch_id", "digest_id", "section", name="uq_review_digest_edits_section"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("bulk_batches.id", ondelete="CASCADE"))
    digest_id: Mapped[int] = mapped_column(ForeignKey("case_digests_v2.id", ondelete="CASCADE"))
    section: Mapped[str] = mapped_column(String(32))
    text: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())


class BulkBatchModel(Base):
    """One bulk upload: many files or G.R. numbers given at once."""

    __tablename__ = "bulk_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_ids: Mapped[list[int]] = mapped_column(ListOf(Integer), default=list)  # the upload's tags
    topic_scope: Mapped[str] = mapped_column(String(300), server_default="")
    kind: Mapped[str] = mapped_column(String(16), server_default="bulk")  # "individual" | "bulk"
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())


class BulkItemModel(Base):
    """One thing in a bulk upload; it ends in a main case of the library or in a plain reason why not."""

    __tablename__ = "bulk_items"
    __table_args__ = (Index("ix_bulk_items_batch_status", "batch_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("bulk_batches.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(16))
    label: Mapped[str] = mapped_column(Text)
    gr_no: Mapped[str | None] = mapped_column(String(32))
    year: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), server_default="queued")
    message: Mapped[str | None] = mapped_column(Text)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id", ondelete="SET NULL"), index=True)
    reporter: Mapped[str | None] = mapped_column(String(64))  # "177 SCRA 668", when the file printed it
    source_url: Mapped[str | None] = mapped_column(Text)  # the exact Lawphil page the student picked (Individual)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())

from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint, Text, Table, Column, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid():
    return str(uuid4())


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


platform_consents=Table('platform_consents',Base.metadata,
    Column('id',String(36),primary_key=True),Column('tenant',String(160),nullable=False),
    Column('subject',String(160),nullable=False),Column('purpose',String(80),nullable=False),
    Column('notice_version',String(40),nullable=False),Column('status',String(20),nullable=False),
    Column('granted_at',String(40),nullable=False),Column('withdrawn_at',String(40)),Column('metadata_json',Text),
    Index('ix_platform_consents_subject','tenant','subject','purpose'))
platform_audit_ledger=Table('platform_audit_ledger',Base.metadata,
    Column('id',String(36),primary_key=True),Column('sequence',Integer,nullable=False),
    Column('tenant',String(160),nullable=False),Column('actor',String(160),nullable=False),
    Column('action',String(80),nullable=False),Column('timestamp',String(40),nullable=False),
    Column('prev_hash',String(64),nullable=False),Column('entry_hash',String(64),nullable=False),Column('payload_json',Text),
    Index('ix_platform_audit_seq','sequence'),Index('ux_platform_audit_sequence','sequence',unique=True))


class Case(Base):
    __tablename__ = 'cases'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant: Mapped[str] = mapped_column(String(160), index=True)
    owner: Mapped[str] = mapped_column(String(160), index=True)
    title: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(40), default='Draft')
    query_kind: Mapped[str] = mapped_column(String(32))
    jurisdiction: Mapped[dict] = mapped_column(JSON)
    as_of: Mapped[str] = mapped_column(String(10))
    passport: Mapped[dict] = mapped_column(JSON, default=dict)
    passport_version: Mapped[int] = mapped_column(Integer, default=0)
    consent: Mapped[dict] = mapped_column(JSON)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __mapper_args__ = {'version_id_col': revision}


class Snapshot(Base):
    __tablename__ = 'product_passport_versions'
    __table_args__ = (UniqueConstraint('case_id', 'version'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey('cases.id', ondelete='CASCADE'), index=True)
    version: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Artifact(Base):
    __tablename__ = 'case_artifacts'
    __table_args__ = (UniqueConstraint('case_id', 'kind', 'idempotency_key'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey('cases.id', ondelete='CASCADE'), index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    context_hash: Mapped[str] = mapped_column(String(64))
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    request_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Event(Base):
    __tablename__ = 'domain_event_outbox'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey('cases.id', ondelete='CASCADE'), index=True)
    tenant: Mapped[str] = mapped_column(String(160), index=True)
    actor: Mapped[str] = mapped_column(String(160))
    action: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SourceDocument(Base):
    __tablename__='source_documents'
    __table_args__=(UniqueConstraint('source_key','sha256'),)
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    source_key: Mapped[str]=mapped_column(String(120),index=True)
    sha256: Mapped[str]=mapped_column(String(64))
    title: Mapped[str]=mapped_column(String(500))
    authority: Mapped[str]=mapped_column(String(160))
    url: Mapped[str]=mapped_column(Text)
    domain: Mapped[str]=mapped_column(String(80))
    country: Mapped[str]=mapped_column(String(2),default='IN')
    active: Mapped[bool]=mapped_column(default=True)
    metadata_json: Mapped[dict]=mapped_column(JSON,default=dict)
    retrieved_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)


class Passage(Base):
    __tablename__='source_passages'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    document_id: Mapped[str]=mapped_column(ForeignKey('source_documents.id',ondelete='CASCADE'),index=True)
    page: Mapped[int]=mapped_column(Integer)
    text: Mapped[str]=mapped_column(Text)
    sha256: Mapped[str]=mapped_column(String(64))
    review: Mapped[dict]=mapped_column(JSON,default=dict)
    active: Mapped[bool]=mapped_column(default=True,server_default='true')
    extraction: Mapped[dict]=mapped_column(JSON,default=dict,server_default='{}')
    review_revision: Mapped[int]=mapped_column(Integer,default=0,server_default='0')


class PassageEmbedding(Base):
    __tablename__='passage_embeddings'
    passage_id: Mapped[str]=mapped_column(ForeignKey('source_passages.id',ondelete='CASCADE'),primary_key=True)
    model: Mapped[str]=mapped_column(String(160),primary_key=True)
    text_sha256: Mapped[str]=mapped_column(String(64))
    vector: Mapped[list]=mapped_column(JSON)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)


class CorpusReviewEvent(Base):
    __tablename__='corpus_review_events'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    passage_id: Mapped[str]=mapped_column(ForeignKey('source_passages.id',ondelete='CASCADE'),index=True)
    actor: Mapped[str]=mapped_column(String(160))
    payload: Mapped[dict]=mapped_column(JSON)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)


class Account(Base):
    __tablename__='accounts'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    email: Mapped[str]=mapped_column(String(254),unique=True)
    display_name: Mapped[str]=mapped_column(String(80),default='',server_default='')
    password_hash: Mapped[str]=mapped_column(String(256))
    tenant: Mapped[str]=mapped_column(String(36),default=uid)
    verified: Mapped[bool]=mapped_column(default=False)
    role: Mapped[str]=mapped_column(String(24),default='user')
    failures: Mapped[int]=mapped_column(Integer,default=0)
    locked_until: Mapped[int]=mapped_column(Integer,default=0)


class AccountSession(Base):
    __tablename__='account_sessions'
    digest: Mapped[str]=mapped_column(String(64),primary_key=True)
    account_id: Mapped[str]=mapped_column(ForeignKey('accounts.id',ondelete='CASCADE'),index=True)
    expires: Mapped[int]=mapped_column(Integer)


class AccountAction(Base):
    __tablename__='account_actions'
    digest: Mapped[str]=mapped_column(String(64),primary_key=True)
    account_id: Mapped[str]=mapped_column(ForeignKey('accounts.id',ondelete='CASCADE'),index=True)
    purpose: Mapped[str]=mapped_column(String(16))
    expires: Mapped[int]=mapped_column(Integer)

from __future__ import annotations
import os
from datetime import datetime, timezone
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, create_engine, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, relationship

DB_URL = os.getenv("VAULTX_DATABASE_URL", "postgresql+psycopg2://vaultx:vaultx-dev@localhost:5432/vaultx")
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    role: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Case(Base):
    __tablename__ = "cases"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    number: Mapped[str] = mapped_column(String, unique=True)
    title: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    
    investigation_runs = relationship("InvestigationRun", back_populates="case")
    transactions = relationship("Transaction", back_populates="case")
    suspect_wallets = relationship("SuspectWallet", back_populates="case")
    evidence = relationship("EvidenceRecord", back_populates="case")
    hypotheses = relationship("HypothesisRecord", back_populates="case")
    reports = relationship("Report", back_populates="case")

class SuspectWallet(Base):
    __tablename__ = "suspect_wallets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    address: Mapped[str] = mapped_column(String)
    chain: Mapped[str] = mapped_column(String)
    
    case = relationship("Case", back_populates="suspect_wallets")

class InvestigationRun(Base):
    __tablename__ = "investigation_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    status: Mapped[str] = mapped_column(String)
    manifest: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    
    case = relationship("Case", back_populates="investigation_runs")

class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    payload: Mapped[dict] = mapped_column(JSON)
    
    case = relationship("Case", back_populates="transactions")
    
    __table_args__ = (
        Index("ix_transaction_case_id", "case_id"),
    )

class EvidenceRecord(Base):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    payload: Mapped[dict] = mapped_column(JSON)
    raw_hash: Mapped[str] = mapped_column(String)
    prev_hash: Mapped[str] = mapped_column(String)
    integrity_hash: Mapped[str] = mapped_column(String)
    
    case = relationship("Case", back_populates="evidence")
    
    __table_args__ = (
        Index("ix_evidence_case_id", "case_id"),
    )

class HypothesisRecord(Base):
    __tablename__ = "hypotheses"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    payload: Mapped[dict] = mapped_column(JSON)
    
    case = relationship("Case", back_populates="hypotheses")
    hypothesis_evidence = relationship("HypothesisEvidence", back_populates="hypothesis")

class HypothesisEvidence(Base):
    __tablename__ = "hypothesis_evidence"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hypothesis_id: Mapped[str] = mapped_column(ForeignKey("hypotheses.id"))
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence.id"))
    relation: Mapped[str] = mapped_column(String)
    
    hypothesis = relationship("HypothesisRecord", back_populates="hypothesis_evidence")
    evidence = relationship("EvidenceRecord")

class Report(Base):
    __tablename__ = "reports"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    content: Mapped[dict] = mapped_column(JSON)
    
    case = relationship("Case", back_populates="reports")

class SahyogRequest(Base):
    __tablename__ = "sahyog_requests"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    attribution_id: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    case_id: Mapped[str] = mapped_column(String)
    actor: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    resource: Mapped[str] = mapped_column(String)
    result: Mapped[str] = mapped_column(String)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    prev_hash: Mapped[str] = mapped_column(String)
    integrity_hash: Mapped[str] = mapped_column(String)
    
    __table_args__ = (
        Index("ix_audit_events_occurred_at", "occurred_at"),
    )

def init_db() -> None:
    Base.metadata.create_all(engine)

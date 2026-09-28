from __future__ import annotations
import os
from datetime import datetime, timezone
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DB_URL = os.getenv("VAULTX_DATABASE_URL", "sqlite:///./vaultx.db")
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
class Base(DeclarativeBase): pass
def now() -> datetime: return datetime.now(timezone.utc)
class User(Base): __tablename__="users"; id: Mapped[str]=mapped_column(String, primary_key=True); role: Mapped[str]=mapped_column(String); name: Mapped[str]=mapped_column(String)
class Case(Base): __tablename__="cases"; id: Mapped[str]=mapped_column(String, primary_key=True); number: Mapped[str]=mapped_column(String, unique=True); title: Mapped[str]=mapped_column(String); status: Mapped[str]=mapped_column(String, default="open")
class SuspectWallet(Base): __tablename__="suspect_wallets"; id: Mapped[int]=mapped_column(Integer, primary_key=True); case_id: Mapped[str]=mapped_column(ForeignKey("cases.id")); address: Mapped[str]=mapped_column(String); chain: Mapped[str]=mapped_column(String)
class InvestigationRun(Base): __tablename__="investigation_runs"; id: Mapped[str]=mapped_column(String, primary_key=True); case_id: Mapped[str]=mapped_column(ForeignKey("cases.id")); status: Mapped[str]=mapped_column(String); manifest: Mapped[dict]=mapped_column(JSON, default=dict)
class Transaction(Base): __tablename__="transactions"; id: Mapped[str]=mapped_column(String, primary_key=True); case_id: Mapped[str]=mapped_column(ForeignKey("cases.id")); payload: Mapped[dict]=mapped_column(JSON)
class EvidenceRecord(Base): __tablename__="evidence"; id: Mapped[str]=mapped_column(String, primary_key=True); case_id: Mapped[str]=mapped_column(ForeignKey("cases.id")); payload: Mapped[dict]=mapped_column(JSON); raw_hash: Mapped[str]=mapped_column(String); prev_hash: Mapped[str]=mapped_column(String); integrity_hash: Mapped[str]=mapped_column(String)
class HypothesisRecord(Base): __tablename__="hypotheses"; id: Mapped[str]=mapped_column(String, primary_key=True); case_id: Mapped[str]=mapped_column(ForeignKey("cases.id")); payload: Mapped[dict]=mapped_column(JSON)
class HypothesisEvidence(Base): __tablename__="hypothesis_evidence"; id: Mapped[int]=mapped_column(Integer, primary_key=True); hypothesis_id: Mapped[str]=mapped_column(ForeignKey("hypotheses.id")); evidence_id: Mapped[str]=mapped_column(ForeignKey("evidence.id")); relation: Mapped[str]=mapped_column(String)
class Report(Base): __tablename__="reports"; id: Mapped[str]=mapped_column(String, primary_key=True); case_id: Mapped[str]=mapped_column(ForeignKey("cases.id")); content: Mapped[dict]=mapped_column(JSON)
class SahyogRequest(Base): __tablename__="sahyog_requests"; id: Mapped[str]=mapped_column(String, primary_key=True); attribution_id: Mapped[str]=mapped_column(String); payload: Mapped[dict]=mapped_column(JSON); status: Mapped[str]=mapped_column(String)
class AuditEvent(Base): __tablename__="audit_events"; id: Mapped[str]=mapped_column(String, primary_key=True); case_id: Mapped[str]=mapped_column(String); actor: Mapped[str]=mapped_column(String); action: Mapped[str]=mapped_column(String); resource: Mapped[str]=mapped_column(String); result: Mapped[str]=mapped_column(String); occurred_at: Mapped[datetime]=mapped_column(DateTime, default=now); prev_hash: Mapped[str]=mapped_column(String); integrity_hash: Mapped[str]=mapped_column(String)
def init_db() -> None: Base.metadata.create_all(engine)

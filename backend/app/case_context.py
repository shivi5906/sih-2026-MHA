"""Loads everything recorded for one investigation run, for document generation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select

from app.database import AuditEvent, Case, EvidenceRecord, GeneratedDocument, HypothesisRecord, InvestigationRun, SuspectWallet, Transaction
from app.evidence_writer import verify_chain
from app.osint import build_osint_report


@dataclass
class CaseContext:
    run: InvestigationRun
    case: Case
    banner: str
    mode: str
    suspects: list[dict[str, str]]
    hypotheses: list[dict[str, Any]]
    transactions: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    chain: dict[str, Any]
    audit: list[dict[str, Any]]
    documents: list[GeneratedDocument]
    osint: dict[str, Any]


def run_banner(run: InvestigationRun) -> tuple[str, str]:
    manifest = run.manifest or {}
    mode = (manifest.get("traceResult") or {}).get("mode", "")
    if mode == "fixture":
        return "FIXTURE TRACE (TEST DATA)", mode
    return manifest.get("banner") or "SNAPSHOT / CASE REPLAY", mode or "replay"


def load_case_context(session, run_id: str) -> CaseContext:
    run = session.get(InvestigationRun, run_id)
    if not run:
        raise HTTPException(404, "run not found")
    case = session.get(Case, run.case_id)
    if not case:
        raise HTTPException(404, "case not found")
    banner, mode = run_banner(run)
    hypotheses = [x.payload for x in session.scalars(select(HypothesisRecord).where(HypothesisRecord.case_id == case.id)).all()]
    # Re-running a trace stores the same hops again; documents list each transfer once.
    seen: set[tuple] = set()
    transactions = []
    for x in session.scalars(select(Transaction).where(Transaction.case_id == case.id)).all():
        p = x.payload
        key = (p.get("txHash") or p.get("id"), p.get("from"), p.get("to"), str(p.get("amount")))
        if key not in seen:
            seen.add(key)
            transactions.append(p)
    evidence = [{"id": x.id, **x.payload, "integrityHash": x.integrity_hash, "prevHash": x.prev_hash}
                for x in session.scalars(select(EvidenceRecord).where(EvidenceRecord.case_id == case.id).order_by(EvidenceRecord.id)).all()]
    audit = [{"when": x.occurred_at.isoformat(timespec="seconds") if x.occurred_at else "", "who": x.actor, "action": x.action, "resource": x.resource, "result": x.result, "integrityHash": x.integrity_hash}
             for x in session.scalars(select(AuditEvent).where(AuditEvent.case_id == case.id).order_by(AuditEvent.occurred_at)).all()]
    suspects = [{"address": w.address, "chain": w.chain} for w in session.scalars(select(SuspectWallet).where(SuspectWallet.case_id == case.id)).all()]
    documents = list(session.scalars(select(GeneratedDocument).where(GeneratedDocument.case_id == case.id).order_by(GeneratedDocument.created_at)).all())
    unique_suspects = list({s["address"]: s for s in suspects}.values())
    return CaseContext(
        run=run, case=case, banner=banner, mode=mode, suspects=unique_suspects, hypotheses=hypotheses,
        transactions=transactions, evidence=evidence, chain=verify_chain(session, case.id), audit=audit,
        documents=documents, osint=build_osint_report(run.id, banner, hypotheses, transactions),
    )

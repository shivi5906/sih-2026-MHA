from __future__ import annotations
import hashlib, json, uuid
from sqlalchemy import select
from app.database import EvidenceRecord
def canonical(value: dict) -> bytes: return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
def append_evidence(session, case_id: str, payload: dict, raw_row: dict, evidence_id: str | None = None) -> EvidenceRecord:
    previous = session.scalars(select(EvidenceRecord).where(EvidenceRecord.case_id==case_id).order_by(EvidenceRecord.id.desc())).first()
    prev_hash = previous.integrity_hash if previous else ""
    raw_hash = hashlib.sha256(canonical(raw_row)).hexdigest()
    integrity_hash = hashlib.sha256(canonical({"payload": payload, "rawHash": raw_hash, "prevHash": prev_hash})).hexdigest()
    record = EvidenceRecord(id=evidence_id or f"EV-{uuid.uuid4().hex}", case_id=case_id, payload=payload, raw_hash=raw_hash, prev_hash=prev_hash, integrity_hash=integrity_hash)
    session.add(record); return record
def verify_chain(session, case_id: str) -> dict:
    records=session.scalars(select(EvidenceRecord).where(EvidenceRecord.case_id==case_id).order_by(EvidenceRecord.id)).all(); prev=""
    for record in records:
        expected=hashlib.sha256(canonical({"payload":record.payload,"rawHash":record.raw_hash,"prevHash":prev})).hexdigest()
        if record.prev_hash != prev or record.integrity_hash != expected: return {"valid":False,"firstBrokenLink":record.id}
        prev=record.integrity_hash
    return {"valid":True,"headHash":prev,"merkleRoot":prev,"count":len(records)}

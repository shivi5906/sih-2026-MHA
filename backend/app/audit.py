from __future__ import annotations
import hashlib, uuid
from sqlalchemy import select
from app.database import AuditEvent
from app.evidence_writer import canonical
def log(session, actor: str, action: str, resource: str, result: str, case_id: str="") -> AuditEvent:
    prior=session.scalars(select(AuditEvent).order_by(AuditEvent.occurred_at.desc())).first(); prev=prior.integrity_hash if prior else ""
    digest=hashlib.sha256(canonical({"actor":actor,"action":action,"resource":resource,"result":result,"prevHash":prev})).hexdigest()
    row=AuditEvent(id=f"AU-{uuid.uuid4().hex}",case_id=case_id,actor=actor,action=action,resource=resource,result=result,prev_hash=prev,integrity_hash=digest); session.add(row); return row

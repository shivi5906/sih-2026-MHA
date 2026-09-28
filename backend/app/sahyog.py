from __future__ import annotations
import uuid
from app.database import SahyogRequest
def prepare(session, attribution_id: str, summary: str, hashes: list[str]) -> SahyogRequest:
    row=SahyogRequest(id=f"MOCK-{uuid.uuid4().hex}",attribution_id=attribution_id,payload={"ids":[attribution_id],"hashes":hashes,"summary":summary,"mock":True},status="pending_supervisor_approval")
    session.add(row); return row

import uuid
from sqlalchemy import delete
from app.database import Base, Case, EvidenceRecord, SessionLocal, engine
from app.evidence_writer import append_evidence, verify_chain
def test_tampering_is_detected():
    # Evidence rows reference cases, so create a throwaway case and remove it afterwards.
    Base.metadata.create_all(engine); session=SessionLocal(); case_id=f"tamper-case-{uuid.uuid4().hex[:8]}"
    try:
        session.add(Case(id=case_id,number=case_id,title="Tamper detection test")); session.commit()
        row=append_evidence(session,case_id,{"x":1},{"raw":1}); session.commit()
        assert verify_chain(session,case_id)["valid"] is True
        row.payload={"x":2}; session.commit()
        assert verify_chain(session,case_id)["valid"] is False
    finally:
        session.rollback(); session.execute(delete(EvidenceRecord).where(EvidenceRecord.case_id==case_id)); session.execute(delete(Case).where(Case.id==case_id)); session.commit(); session.close()

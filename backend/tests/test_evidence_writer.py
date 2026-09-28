from app.database import Base, SessionLocal, engine
from app.evidence_writer import append_evidence, verify_chain
def test_tampering_is_detected():
    Base.metadata.create_all(engine); session=SessionLocal()
    try:
        row=append_evidence(session,"tamper-case",{"x":1},{"raw":1}); session.commit(); row.payload={"x":2}; session.commit()
        assert verify_chain(session,"tamper-case")["valid"] is False
    finally: session.close()

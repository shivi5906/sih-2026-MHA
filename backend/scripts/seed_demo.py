from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from app.database import Case, EvidenceRecord, HypothesisRecord, InvestigationRun, Report, SessionLocal, Transaction, init_db
from app.evidence_writer import append_evidence, verify_chain
from vaultx.attribution.hypotheses import load_scoring_config, ranked_hypotheses
from vaultx.casedata.loader import load_case_data

CASE_ID="CYBER-2026-001"
def main():
    init_db(); session=SessionLocal()
    try:
        case=session.get(Case,CASE_ID)
        if not case: session.add(Case(id=CASE_ID,number=CASE_ID,title="Bitfinex 2016 hack (public dataset replay)",status="open"))
        data=load_case_data(); config_hash=load_scoring_config()[1]
        if not session.scalars(select(Transaction).where(Transaction.case_id==CASE_ID)).first():
            for tx in data.transactions: session.add(Transaction(id=tx.id,case_id=CASE_ID,payload=tx.model_dump(by_alias=True,mode="json")))
        labeled=next(tx for tx in data.january_transactions if tx.metadata["peerName"])
        hypotheses,evidence=ranked_hypotheses(labeled,data.january_transactions)
        for item in evidence:
            if not session.get(EvidenceRecord,item.id): append_evidence(session,CASE_ID,item.model_dump(by_alias=True,mode="json"),{"tx":item.tx_refs[0]},item.id)
        for item in hypotheses:
            if not session.get(HypothesisRecord,item.id): session.add(HypothesisRecord(id=item.id,case_id=CASE_ID,payload=item.model_dump(by_alias=True,mode="json")))
        run=session.scalars(select(InvestigationRun).where(InvestigationRun.case_id==CASE_ID)).first()
        if not run: session.add(InvestigationRun(id="RUN-CYBER-2026-001",case_id=CASE_ID,status="completed",manifest={"banner":"SNAPSHOT / CASE REPLAY","scoringYamlHash":config_hash,"calibrated":False}))
        chain=verify_chain(session,CASE_ID); content={"banner":"CASE REPLAY — PROTOTYPE — NOT SUBMITTED TO ANY GOVERNMENT SYSTEM","methodology":"Uncalibrated log-odds attribution with abstention.","scoringYamlHash":config_hash,"chainHeadHash":chain["headHash"],"merkleRoot":chain["merkleRoot"],"dataQualityIssues":[x.model_dump(by_alias=True) for x in data.report.issues]}
        if not session.get(Report,"REPORT-CYBER-2026-001"): session.add(Report(id="REPORT-CYBER-2026-001",case_id=CASE_ID,content=content))
        session.commit(); print("seeded",CASE_ID,chain)
    finally: session.close()
if __name__=="__main__": main()

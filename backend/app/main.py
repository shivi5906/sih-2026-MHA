from __future__ import annotations
import uuid
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from jinja2 import Template
from sqlalchemy import select
from app.audit import log
from app.database import Case, EvidenceRecord, HypothesisRecord, InvestigationRun, Report, SahyogRequest, SessionLocal, Transaction, init_db
from app.evidence_writer import verify_chain
from app.sahyog import prepare

app=FastAPI(title="VAULT-X", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])
@app.on_event("startup")
def startup(): init_db()
def db():
    session=SessionLocal()
    try: yield session; session.commit()
    except: session.rollback(); raise
    finally: session.close()
def actor(x_role: str=Header("Analyst"), authorization: str|None=Header(None)) -> str: return x_role
def audit_read(session, role, resource, case_id=""): log(session, role, "read", resource, "ok", case_id)
def require(role: str, allowed: set[str]):
    if role not in allowed: raise HTTPException(403, "role not permitted")

@app.post("/api/v1/auth/login")
def login(body: dict):
    role=body.get("role", "Analyst")
    if role not in {"Analyst","Senior Investigator","Supervisor","Auditor"}: raise HTTPException(400,"invalid role")
    return {"token":f"fake-jwt.{role}","user":{"id":body.get("email","demo"),"role":role},"mock":True}
@app.get("/api/v1/cases")
def cases(session=Depends(db), role=Depends(actor)):
    audit_read(session,role,"cases"); return [{"id":x.id,"number":x.number,"title":x.title,"status":x.status} for x in session.scalars(select(Case)).all()]
@app.post("/api/v1/cases")
def create_case(body:dict, session=Depends(db), role=Depends(actor)):
    require(role,{"Analyst","Senior Investigator","Supervisor"}); row=Case(id=body.get("id",uuid.uuid4().hex),number=body["number"],title=body["title"],status="open"); session.add(row); log(session,role,"write","case","created",row.id); return {"id":row.id,"number":row.number}
@app.get("/api/v1/cases/{case_id}")
def case(case_id:str,session=Depends(db),role=Depends(actor)):
    row=session.get(Case,case_id) or session.scalars(select(Case).where(Case.number==case_id)).first()
    if not row: raise HTTPException(404,"case not found")
    audit_read(session,role,"case",row.id); return {"id":row.id,"number":row.number,"title":row.title,"status":row.status}
@app.patch("/api/v1/cases/{case_id}")
def update_case(case_id:str,body:dict,session=Depends(db),role=Depends(actor)):
    row=session.get(Case,case_id) or session.scalars(select(Case).where(Case.number==case_id)).first()
    if not row: raise HTTPException(404,"case not found")
    row.title=body.get("title",row.title); row.status=body.get("status",row.status); log(session,role,"write","case","updated",row.id); return {"id":row.id,"status":row.status}
@app.post("/api/v1/cases/{case_id}/investigations")
def start(case_id:str,tasks:BackgroundTasks,session=Depends(db),role=Depends(actor)):
    run=InvestigationRun(id=uuid.uuid4().hex,case_id=case_id,status="completed",manifest={"banner":"SNAPSHOT / CASE REPLAY","calibrated":False}); session.add(run); log(session,role,"write","investigation","started",case_id); return {"id":run.id,"status":run.status}
@app.get("/api/v1/investigations/{run_id}")
def investigation(run_id:str,session=Depends(db),role=Depends(actor)):
    row=session.get(InvestigationRun,run_id)
    if not row: raise HTTPException(404,"run not found")
    audit_read(session,role,"investigation",row.case_id); return {"id":row.id,"status":row.status,"manifest":row.manifest}
@app.get("/api/v1/investigations/{run_id}/events")
def events(run_id:str): return StreamingResponse(iter(["event: status\ndata: {\"status\":\"completed\"}\n\n"]),media_type="text/event-stream")
def _run(session,run_id):
    row=session.get(InvestigationRun,run_id)
    if not row: raise HTTPException(404,"run not found")
    return row
@app.get("/api/v1/investigations/{run_id}/graph")
def graph(run_id:str,session=Depends(db),role=Depends(actor)):
    run=_run(session,run_id); txs=session.scalars(select(Transaction).where(Transaction.case_id==run.case_id)).all(); audit_read(session,role,"graph",run.case_id); return {"nodes":[],"edges":[x.payload for x in txs],"banner":"SNAPSHOT / CASE REPLAY"}
@app.get("/api/v1/investigations/{run_id}/attribution")
def attribution(run_id:str,session=Depends(db),role=Depends(actor)):
    run=_run(session,run_id); rows=session.scalars(select(HypothesisRecord).where(HypothesisRecord.case_id==run.case_id)).all(); audit_read(session,role,"attribution",run.case_id); return [x.payload for x in rows]
@app.get("/api/v1/attributions/{attribution_id}/why")
def why(attribution_id:str,session=Depends(db),role=Depends(actor)):
    row=session.get(HypothesisRecord,attribution_id); audit_read(session,role,"attribution-why"); return row.payload if row else {"detail":"NO_ATTRIBUTION"}
@app.get("/api/v1/attributions/{attribution_id}/counterfactual")
def counterfactual(attribution_id:str): return {"sensitivity":"single tier-C label required","calibrated":False}
@app.get("/api/v1/evidence")
def evidence(session=Depends(db),role=Depends(actor)):
    audit_read(session,role,"evidence"); return [{"id":x.id,**x.payload,"integrityHash":x.integrity_hash} for x in session.scalars(select(EvidenceRecord)).all()]
@app.get("/api/v1/evidence/{evidence_id}/verify")
def verify(evidence_id:str,session=Depends(db),role=Depends(actor)):
    row=session.get(EvidenceRecord,evidence_id)
    if not row: raise HTTPException(404,"evidence not found")
    audit_read(session,role,"evidence-verify",row.case_id); return verify_chain(session,row.case_id)
@app.get("/api/v1/investigations/{run_id}/replay")
def replay(run_id:str): return {"banner":"SNAPSHOT / CASE REPLAY","calibrated":False}
@app.get("/api/v1/investigations/{run_id}/reports")
def reports(run_id:str,session=Depends(db),role=Depends(actor)):
    run=_run(session,run_id); rows=session.scalars(select(Report).where(Report.case_id==run.case_id)).all(); return [x.content for x in rows]
@app.get("/api/v1/reports/{report_id}/html", response_class=HTMLResponse)
def report_html(report_id:str,session=Depends(db),role=Depends(actor)):
    row=session.get(Report,report_id)
    if not row: raise HTTPException(404,"report not found")
    audit_read(session,role,"report",row.case_id)
    return Template("<main><h1>{{ r.banner }}</h1><h2>Methodology</h2><p>{{ r.methodology }}</p><p>Scoring YAML: {{ r.scoringYamlHash }}</p><p>Chain head: {{ r.chainHeadHash }}</p><h2>Data quality</h2><pre>{{ r.dataQualityIssues }}</pre></main>").render(r=row.content)
@app.get("/api/v1/audit")
def audit(session=Depends(db),role=Depends(actor)):
    require(role,{"Auditor","Supervisor"}); return [{"id":x.id,"who":x.actor,"what":x.action,"resource":x.resource,"result":x.result,"integrityHash":x.integrity_hash} for x in session.scalars(select(__import__('app.database',fromlist=['AuditEvent']).AuditEvent)).all()]
@app.get("/api/v1/intel/vasps")
def vasps(): return {"items":[{"name":"Xzzx.biz","sourceTier":"C","verified":False}]}
@app.post("/api/v1/attributions/{attribution_id}/sahyog/prepare")
def sahyog_prepare(attribution_id:str,session=Depends(db),role=Depends(actor)):
    item=prepare(session,attribution_id,"Uncalibrated case-replay attribution",[]); log(session,role,"write","sahyog-mock","prepared"); return {"id":item.id,"status":item.status,"mock":True,"payload":item.payload}
@app.post("/api/v1/attributions/{attribution_id}/sahyog/approve")
def sahyog_approve(attribution_id:str,session=Depends(db),role=Depends(actor)):
    require(role,{"Supervisor"}); item=session.scalars(select(SahyogRequest).where(SahyogRequest.attribution_id==attribution_id)).first()
    if not item: raise HTTPException(404,"mock request not found")
    item.status="mock_acknowledged"; log(session,role,"write","sahyog-mock","approved"); return {"id":item.id,"status":item.status,"mock":True}

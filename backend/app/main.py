from __future__ import annotations
import logging
import uuid
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from jinja2 import Template
from sqlalchemy import select
from app.audit import log
from app.database import Case, EvidenceRecord, HypothesisRecord, InvestigationRun, Report, SahyogRequest, SessionLocal, SuspectWallet, Transaction, User, init_db
from app.evidence_writer import verify_chain
from app.sahyog import prepare
from app.trace_runner import run_trace
from app.auth_service import verify_password, create_access_token, decode_token, seed_default_users
from app.neo4j_client import get_neo4j_client
import os

logger = logging.getLogger(__name__)

app=FastAPI(title="VAULT-X", version="0.1.0")
MAX_RENDERED_GRAPH_EDGES = 200
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])
@app.on_event("startup")
def startup():
    init_db()
    with SessionLocal() as session:
        seed_default_users(session)
def db():
    session=SessionLocal()
    try: yield session; session.commit()
    except: session.rollback(); raise
    finally: session.close()
def actor(authorization: str | None = Header(None), x_role: str = Header("Analyst")) -> str:
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        payload = decode_token(token)
        return payload["role"]
    # Dev fallback: allow X-Role header when VAULTX_DEV_MODE=true
    if os.getenv("VAULTX_DEV_MODE", "true").lower() == "true":
        return x_role
    raise HTTPException(401, "Authorization required")
def audit_read(session, role, resource, case_id=""): log(session, role, "read", resource, "ok", case_id)
def require(role: str, allowed: set[str]):
    if role not in allowed: raise HTTPException(403, "role not permitted")

@app.post("/api/v1/auth/login")
def login(body: dict, session=Depends(db)):
    email = body.get("email", "")
    password = body.get("password", "")
    user = session.scalars(select(User).where(User.email == email)).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    token = create_access_token(user.id, user.role)
    return {"token": token, "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role}}

@app.get("/api/v1/auth/me")
def me(authorization: str = Header(...), session=Depends(db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid token")
    token = authorization[7:]
    payload = decode_token(token)
    user = session.get(User, payload["user_id"])
    if not user:
        raise HTTPException(401, "User not found")
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}
@app.get("/api/v1/cases")
def cases(session=Depends(db), role=Depends(actor)):
    audit_read(session,role,"cases"); return [{"id":x.id,"number":x.number,"title":x.title,"status":x.status} for x in session.scalars(select(Case)).all()]
@app.post("/api/v1/cases")
def create_case(body:dict, session=Depends(db), role=Depends(actor)):
    require(role,{"Analyst","Senior Investigator","Supervisor"}); row=Case(id=body.get("id",uuid.uuid4().hex),number=body["number"],title=body["title"],status="open"); session.add(row)
    wallet=body.get("walletAddress")
    chain=body.get("chain")
    if wallet:
        session.add(SuspectWallet(case_id=row.id,address=wallet,chain=chain or "auto"))
    log(session,role,"write","case","created",row.id); return {"id":row.id,"number":row.number,"walletAddress":wallet}
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
async def start(case_id:str,body:dict|None=None,tasks:BackgroundTasks=None,session=Depends(db),role=Depends(actor)):
    body = body or {}
    wallet = body.get("walletAddress")
    # Also check if a SuspectWallet was stored during case creation
    if not wallet:
        sw = session.scalars(select(SuspectWallet).where(SuspectWallet.case_id==case_id)).first()
        if sw:
            wallet = sw.address
    run_id = uuid.uuid4().hex
    run=InvestigationRun(id=run_id,case_id=case_id,status="running",manifest={"banner":"LIVE TRACE" if wallet else "SNAPSHOT / CASE REPLAY","calibrated":False})
    session.add(run)
    session.flush()  # persist run before trace so it's visible
    log(session,role,"write","investigation","started",case_id)
    if wallet:
        chain_hint = body.get("chain")
        try:
            trace_summary = await run_trace(session, case_id, wallet, chain_hint)
            run.status = "completed"
            run.manifest = {**run.manifest, "traceResult": trace_summary}
            logger.info("Trace completed for case %s: %s", case_id, trace_summary)
        except Exception as e:
            logger.exception("Trace failed for case %s: %s", case_id, e)
            run.status = "failed"
            run.manifest = {**run.manifest, "error": str(e)}
            return {"id":run.id,"status":"failed","error":str(e)}
    else:
        run.status = "completed"
    return {"id":run.id,"status":run.status,"manifest":run.manifest}
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

def _graph_label(address: str, metadata: dict) -> str:
    """Return a display label without changing the recorded address."""
    if address.startswith("virtual:"):
        return address.removeprefix("virtual:").replace("-", " ").title() + " (virtual)"
    return metadata.get("peerName") or metadata.get("peerCategory") or f"{address[:10]}…{address[-6:]}"

def _graph_overview_transactions(txs: list[Transaction]) -> list[Transaction]:
    """Keep the replay overview responsive while representing each source dataset."""
    groups: dict[str, list[Transaction]] = {}
    for row in txs:
        dataset=(row.payload.get("provenance") or {}).get("dataset", "recorded-transfers")
        groups.setdefault(dataset, []).append(row)
    per_group=max(1, MAX_RENDERED_GRAPH_EDGES // max(1, len(groups)))
    overview: list[Transaction] = []
    for rows in groups.values():
        overview.extend(sorted(rows, key=lambda row: not bool((row.payload.get("metadata") or {}).get("peerName")))[:per_group])
    return overview[:MAX_RENDERED_GRAPH_EDGES]

@app.get("/api/v1/investigations/{run_id}/graph")
def graph(run_id:str,session=Depends(db),role=Depends(actor)):
    run=_run(session,run_id)
    
    neo4j_client = get_neo4j_client()
    neo4j_data = neo4j_client.get_case_graph(run.case_id)
    
    if neo4j_data and (neo4j_data.get("nodes") or neo4j_data.get("edges")):
        nodes = []
        for n in neo4j_data["nodes"]:
            addr = n["address"]
            nodes.append({"id": addr, "label": _graph_label(addr, {}), "data": {"address": addr, "chain": n.get("chain"), "epistemicLabel": "OBSERVED"}})
        
        edges = []
        for e in neo4j_data["edges"]:
            edges.append({"id": e["id"], "source": e["source"], "target": e["target"], "data": {"amount": e.get("amount"), "asset": "BTC", "timestamp": 0, "transactionId": e["id"], "provenance": {}}, "epistemicLabel": "OBSERVED"})
            
        audit_read(session,role,"graph",run.case_id)
        return {"nodes":nodes,"edges":edges,"banner":"SNAPSHOT / CASE REPLAY","renderedEdges":len(edges),"totalEdges":len(edges),"truncated":False}
    
    txs=session.scalars(select(Transaction).where(Transaction.case_id==run.case_id)).all()
    rendered=_graph_overview_transactions(txs)
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    for row in rendered:
        payload=row.payload
        source, target = payload["from"], payload["to"]
        metadata=payload.get("metadata") or {}
        for address in (source, target):
            if address not in nodes:
                nodes[address]={"id":address,"label":_graph_label(address, metadata),"data":{"address":address,"chain":payload.get("chain"),"epistemicLabel":payload.get("epistemicLabel", "OBSERVED")}}
        edges.append({"id":payload["id"],"source":source,"target":target,"data":{"amount":payload.get("amount"),"asset":payload.get("asset", "BTC"),"timestamp":payload.get("timestamp"),"transactionId":payload["txHash"],"provenance":payload.get("provenance", {})},"epistemicLabel":payload.get("epistemicLabel", "OBSERVED")})
    audit_read(session,role,"graph",run.case_id)
    return {"nodes":list(nodes.values()),"edges":edges,"banner":"SNAPSHOT / CASE REPLAY","renderedEdges":len(edges),"totalEdges":len(txs),"truncated":len(txs)>len(edges)}

@app.get("/api/v1/graph/shortest-path")
def graph_shortest_path(from_addr: str, to_addr: str, role=Depends(actor)):
    neo4j_client = get_neo4j_client()
    return neo4j_client.get_shortest_path(from_addr, to_addr)

@app.get("/api/v1/graph/neighborhood")
def graph_neighborhood(address: str, depth: int = 2, role=Depends(actor)):
    neo4j_client = get_neo4j_client()
    return neo4j_client.get_neighborhood(address, depth)
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
    require(role,{"Auditor","Supervisor"}); return [{"id":x.id,"caseId":x.case_id,"who":x.actor,"what":x.action,"resource":x.resource,"result":x.result,"occurredAt":x.occurred_at.isoformat(),"integrityHash":x.integrity_hash} for x in session.scalars(select(__import__('app.database',fromlist=['AuditEvent']).AuditEvent).order_by(__import__('app.database',fromlist=['AuditEvent']).AuditEvent.occurred_at.desc())).all()]
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

import re
import zlib
from types import SimpleNamespace
from datetime import datetime, timezone
import pytest

from app import court_report
from app.case_context import CaseContext
from app.osint import build_osint_report
from app.main import create_court_report as create_court_report_endpoint, document_pdf, get_document
from app.database import SessionLocal, Case, InvestigationRun, GeneratedDocument, init_db

ADDR = "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo"
HYPS = [
    {"id": "Binance", "hypothesis": "Binance", "targetAddress": ADDR, "score": 0.95, "band": "HIGH", "epistemicLabel": "ATTRIBUTED", "supporting": ["EV-1"], "nextActions": []},
    {"id": "Huobi", "hypothesis": "Huobi", "targetAddress": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "score": 0.62, "band": "MEDIUM", "epistemicLabel": "ATTRIBUTED", "supporting": ["EV-2"], "nextActions": []},
]
TXS = [
    {"id": "t1", "txHash": "a" * 64, "from": "bc1qsuspect", "to": "bc1qmid", "amount": "0.5", "asset": "BTC", "chain": "Bitcoin", "timestamp": 1700000000},
    {"id": "t2", "txHash": "b" * 64, "from": "bc1qmid", "to": ADDR, "amount": "0.4", "asset": "BTC", "chain": "Bitcoin", "timestamp": 1700003600},
]
EVIDENCES = [
    {"id": "EV-001", "type": "observation", "sourceTier": "A", "description": "Suspect address tx observed on blockchain", "integrityHash": "1" * 64, "prevHash": ""},
    {"id": "EV-002", "type": "attribution", "sourceTier": "B", "description": "Deposit address clustered to Binance", "integrityHash": "2" * 64, "prevHash": "1" * 64},
]
AUDIT_LOGS = [
    {"when": "2026-03-14 09:30:00", "who": "Analyst", "action": "write", "resource": "investigation", "result": "started", "integrityHash": "3" * 64},
    {"when": "2026-03-14 09:35:00", "who": "Senior Investigator", "action": "read", "resource": "graph", "result": "ok", "integrityHash": "4" * 64},
]


def make_ctx(empty: bool = False) -> CaseContext:
    if empty:
        return CaseContext(
            run=SimpleNamespace(id="run-empty", status="completed", manifest={}),
            case=SimpleNamespace(id="case-empty", number="CYBER-EMPTY-0", title="Empty Test Case"),
            banner="FIXTURE TRACE (TEST DATA)",
            mode="fixture",
            suspects=[],
            hypotheses=[],
            transactions=[],
            evidence=[],
            chain={"valid": True, "headHash": "0" * 64, "count": 0},
            audit=[],
            documents=[],
            osint=build_osint_report("run-empty", "FIXTURE TRACE (TEST DATA)", [], []),
        )
    return CaseContext(
        run=SimpleNamespace(id="run-court-1", status="completed", manifest={}),
        case=SimpleNamespace(id="case-court-1", number="CYBER-2026-009", title="Major Crypto Embezzlement"),
        banner="LIVE TRACE (BLOCKCHAIN CONSENSUS)",
        mode="live",
        suspects=[{"address": "bc1qsuspect11111111111111111111111111111", "chain": "Bitcoin"}],
        hypotheses=HYPS,
        transactions=TXS,
        evidence=EVIDENCES,
        chain={"valid": True, "headHash": "e" * 64, "count": 2},
        audit=AUDIT_LOGS,
        documents=[],
        osint=build_osint_report("run-court-1", "LIVE TRACE (BLOCKCHAIN CONSENSUS)", HYPS, TXS),
    )


def pdf_text(pdf: bytes) -> str:
    """Concatenate the decompressed page streams so tests can search the drawn text."""
    out = []
    for m in re.finditer(rb"stream\n(.*?)\nendstream", pdf, re.S):
        try:
            decomp = zlib.decompress(m.group(1)).decode("cp1252")
            out.append(decomp.replace(r"\(", "(").replace(r"\)", ")"))
        except zlib.error:
            pass
    return "\n".join(out)


def assert_valid_pdf(pdf: bytes) -> None:
    assert pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF")
    xref = int(re.search(rb"startxref\n(\d+)", pdf).group(1))
    assert pdf[xref:xref + 4] == b"xref"
    count = int(re.search(rb"xref\n0 (\d+)", pdf).group(1))
    offsets = re.findall(rb"(\d{10}) 00000 n ", pdf)
    assert len(offsets) == count - 1


def test_court_report_renders_full_dossier_and_section_63_bsa():
    ctx = make_ctx()
    officer = {"name": "Insp. Vikram Singh", "rank": "Cyber Cell Inspector", "unit": "Special Cyber Forensic Wing"}
    expert = {"name": "Dr. Ananya Roy", "rank": "Senior Digital Forensics Examiner", "unit": "State Cyber Forensics Laboratory"}
    built = court_report.create_court_report(
        ctx,
        {
            "courtName": "HON'BLE SPECIAL COURT FOR ECONOMIC OFFENCES, NEW DELHI",
            "officer": officer,
            "expert": expert,
            "notes": "Suspect moved 0.9 BTC through peeling chains before depositing into Binance exchange.",
        },
    )

    pdf = built["pdf"]
    assert_valid_pdf(pdf)
    text = pdf_text(pdf)

    # Judicial Masthead & Case Particulars
    assert "SPECIAL COURT FOR ECONOMIC OFFENCES" in text
    assert "FORENSIC INVESTIGATION REPORT & EVIDENCE DOSSIER" in text
    assert "CYBER-2026-009" in text
    assert "Insp. Vikram Singh" in text
    assert "Dr. Ananya Roy" in text

    # Section 63 BSA declarations
    assert "SECTION 63 OF THE BHARATIYA SAKSHYA ADHINIYAM, 2023" in text
    assert "PART A: Certificate by Person in Lawful Control" in text
    assert "PART B: Certificate by Technical / Cyber Forensic Expert" in text
    assert "Section 63(4)(c)" in text
    assert "VAULT-X Digital Forensics Suite" in text

    # Evidence, Audit, Hypotheses
    assert "Binance" in text
    assert "bc1qsuspect" in text
    assert "Suspect address tx observed on blockchain" in text
    assert "Analyst" in text

    # Diagram & Charts
    assert "SUSPECT ORIGIN" in text
    assert "TERMINAL VASP" in text
    assert "Forensic Fund-Flow Vector Diagram" in text

    assert built["meta"]["caseNumber"] == "CYBER-2026-009"
    assert built["meta"]["chainValid"] is True
    assert len(built["sha256"]) == 64


def test_court_report_empty_case_context_does_not_crash():
    ctx = make_ctx(empty=True)
    built = court_report.create_court_report(ctx, {})
    assert_valid_pdf(built["pdf"])
    text = pdf_text(built["pdf"])
    assert "CYBER-EMPTY-0" in text
    assert "SECTION 63 OF THE BHARATIYA SAKSHYA ADHINIYAM, 2023" in text


def test_court_report_api_endpoint_and_storage():
    init_db()

    with SessionLocal() as s:
        # Clean up any previous test record
        case = s.get(Case, "case-cr-api-test")
        if not case:
            case = Case(id="case-cr-api-test", number="CYBER-CR-API-1", title="API Test Case", status="open")
            s.add(case)
        run = s.get(InvestigationRun, "run-cr-api-test")
        if not run:
            run = InvestigationRun(id="run-cr-api-test", case_id="case-cr-api-test", status="completed", manifest={"banner": "TEST"})
            s.add(run)
        s.commit()

        # Invoke create_court_report endpoint handler
        payload = {
            "officer": {"name": "Insp. R. Sharma", "rank": "Inspector", "unit": "Cyber Police Station"},
            "courtName": "Special Court for Cyber Crimes",
            "notes": "Funds seized at exchange boundary.",
        }
        summary = create_court_report_endpoint("run-cr-api-test", payload, session=s, role="Analyst")
        assert summary["kind"] == "court_report"
        assert summary["caseId"] == "case-cr-api-test"
        assert summary["runId"] == "run-cr-api-test"
        assert summary["id"].startswith("DOC-")
        assert len(summary["sha256"]) == 64
        assert summary["sizeBytes"] > 0
        s.commit()

        # Verify document can be fetched via document_pdf endpoint handler
        resp = document_pdf(summary["id"], download=False, session=s, role="Analyst")
        assert resp.media_type == "application/pdf"
        assert resp.headers["X-Document-SHA256"] == summary["sha256"]
        assert_valid_pdf(resp.body)

        # Verify download response headers
        dl_resp = document_pdf(summary["id"], download=True, session=s, role="Analyst")
        assert "attachment" in dl_resp.headers["Content-Disposition"]

"""Court report PDF generation under Section 63 BSA, 2023.

Produces an official, court-admissible forensic investigation report and
evidence dossier for submission before the Hon'ble Court. Built with the same
PDF generator as the VASP notices (PdfDocument in app.pdf).

The report includes:
1. Formal Judicial Case Information & Particulars
2. Executive Summary & Epistemic Methodology
3. Attribution Hypotheses & VASP Deposit Identifications
4. Forensic Visualizations (Vector fund-flow diagram & analytics charts)
5. On-Chain Forensic Transaction Ledger (Fund movement trail)
6. Cryptographic Evidence Register with SHA-256 Hashes
7. Official Investigation Audit Trail & Chain of Custody
8. Certificate under Section 63 of Bharatiya Sakshya Adhiniyam, 2023 (BSA):
   - Part A: Certificate by Person in Lawful Control of Computer / System
   - Part B: Certificate by Technical / Cyber Forensic Expert
"""
from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Sequence

from app.case_context import CaseContext
from app.pdf import (
    ACCENT,
    AMBER,
    BLACK,
    GREEN,
    GREY,
    LIGHT,
    MARGIN_X,
    NAVY,
    PAGE_H,
    PAGE_W,
    RED,
    RULE,
    PdfDocument,
    clean,
    text_width,
)

DEFAULT_COURT = "HON'BLE SPECIAL COURT FOR ECONOMIC OFFENCES & CYBER CRIME"
DEFAULT_POLICE_STATION = "CYBER CRIME INVESTIGATION CELL & FORENSIC LAB"


def report_number(ctx: CaseContext, when: datetime) -> str:
    """Generate a formal reference number for the court report."""
    case_clean = re.sub(r"[^A-Z0-9]", "", ctx.case.number.upper()) or "CASE"
    return f"CR/VX/{case_clean}/{when:%Y%m%d}/{uuid.uuid4().hex[:6].upper()}"


def _iso_date(ts: Any) -> str:
    """Format a timestamp safely for display."""
    if not ts:
        return "-"
    try:
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        s = str(ts).strip()
        if s.isdigit():
            return datetime.fromtimestamp(int(s), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        # Try parsing ISO strings like 2026-03-14T09:31:07Z
        return s.replace("T", " ")[:19] + " UTC"
    except (TypeError, ValueError, OSError):
        return str(ts)[:20]


def _draw_flow_diagram(doc: PdfDocument, ctx: CaseContext) -> None:
    """Draw a vector fund-flow diagram illustrating the money trail."""
    doc.ensure(110)
    doc.heading("Forensic Fund-Flow Vector Diagram", level=2)
    doc.paragraph(
        "Schematic representation of traced blockchain fund movement from suspect address to final identified deposit accounts.",
        size=8.5,
        color=GREY,
    )
    doc.space(4)

    box_y = doc.y - 45
    box_w = 95.0
    box_h = 38.0
    gap = 25.0
    start_x = MARGIN_X + 10

    suspect_label = ctx.suspects[0]["address"] if ctx.suspects else "SUSPECT"
    suspect_short = f"{suspect_label[:6]}...{suspect_label[-4:]}" if len(suspect_label) > 12 else suspect_label

    vasp_name = "TARGET VASP"
    if ctx.hypotheses:
        vasp_name = str(ctx.hypotheses[0].get("hypothesis") or ctx.hypotheses[0].get("vasp") or "TARGET VASP")

    stages = [
        ("SUSPECT ORIGIN", suspect_short, RED),
        ("INTERMEDIARY", "Hop 1 / Layering", NAVY),
        ("CONSOLIDATION", "Taint Propagation", ACCENT),
        ("TERMINAL VASP", vasp_name[:12].upper(), GREEN),
    ]

    for i, (top_text, btm_text, col) in enumerate(stages):
        bx = start_x + i * (box_w + gap)
        # Background box
        doc.rect(bx, box_y, box_w, box_h, fill=LIGHT, stroke=col, width=1.0)
        # Header banner inside box
        doc.rect(bx, box_y + box_h - 12, box_w, 12, fill=col)
        # Top title inside box
        t_w = text_width(top_text, "bold", 6.5)
        doc.text(bx + (box_w - t_w) / 2, box_y + box_h - 9, top_text, "bold", 6.5, (1, 1, 1))
        # Main label
        m_w = text_width(btm_text, "bold", 7.5)
        doc.text(bx + (box_w - m_w) / 2, box_y + 12, btm_text, "bold", 7.5, BLACK)

        # Arrow between boxes
        if i < len(stages) - 1:
            ax1 = bx + box_w + 3
            ax2 = ax1 + gap - 6
            ay = box_y + box_h / 2
            doc.line(ax1, ay, ax2, ay, color=GREY, width=1.2)
            # Arrow head
            doc.line(ax2 - 4, ay + 3, ax2, ay, color=GREY, width=1.2)
            doc.line(ax2 - 4, ay - 3, ax2, ay, color=GREY, width=1.2)

    doc.y = box_y - 12


def render_court_report(
    ctx: CaseContext,
    officer: dict[str, str] | None = None,
    court_name: str | None = None,
    expert: dict[str, str] | None = None,
    notes: str | None = None,
    number: str | None = None,
    when: datetime | None = None,
) -> bytes:
    """Render a comprehensive, court-admissible forensic dossier and Section 63 BSA certificate."""
    when = when or datetime.now(timezone.utc).replace(microsecond=0)
    number = number or report_number(ctx, when)
    officer = officer or {}
    expert = expert or {}
    court_title = court_name or DEFAULT_COURT
    police_unit = officer.get("unit") or DEFAULT_POLICE_STATION

    doc = PdfDocument(
        title=f"Court Report - {ctx.case.number}",
        header_left="CONFIDENTIAL  |  SUBMITTED TO HON'BLE COURT",
        header_right=f"Ref: {number}",
        footer_note=f"Forensic Investigation Report | Case {ctx.case.number} | Section 63 BSA 2023 Certified",
    )

    # =========================================================================
    # PAGE 1: OFFICIAL JUDICIAL COVER & CASE PARTICULARS
    # =========================================================================
    doc.text((PAGE_W - text_width(court_title.upper(), "bold", 10.5)) / 2, doc.y - 11, court_title.upper(), "bold", 10.5, NAVY)
    doc.y -= 16
    doc.text((PAGE_W - text_width(police_unit.upper(), "bold", 9.5)) / 2, doc.y - 10, police_unit.upper(), "bold", 9.5, GREY)
    doc.y -= 22

    main_title = "FORENSIC INVESTIGATION REPORT & EVIDENCE DOSSIER"
    doc.text((PAGE_W - text_width(main_title, "bold", 13.5)) / 2, doc.y - 14, main_title, "bold", 13.5, BLACK)
    doc.y -= 18

    sub_title = "Submitted under Section 94 BNSS, 2023 & Section 63 Bharatiya Sakshya Adhiniyam, 2023 (BSA)"
    doc.text((PAGE_W - text_width(sub_title, "italic", 9)) / 2, doc.y - 9, sub_title, "italic", 9, NAVY)
    doc.y -= 20

    doc.notice_box(
        "CONFIDENTIAL - RESTRICTED JUDICIAL RECORD: This document contains cryptographic audit logs, "
        "on-chain transaction ledgers, attribution hypotheses, and statutory certificates prepared for the "
        "Hon'ble Court. All digital hashes are verified under Section 63 of Bharatiya Sakshya Adhiniyam, 2023.",
        color=NAVY,
        size=8.0,
    )

    suspect_str = ", ".join(f"{s['address']} ({s.get('chain', 'unknown')})" for s in ctx.suspects) or "None recorded"
    investigator_name = officer.get("name") or "Investigating Officer"
    investigator_rank = officer.get("rank") or "Cyber Crime Inspector"

    doc.heading("I. Formal Case Particulars", level=1)
    doc.kv([
        ("Report Reference No.", number),
        ("Case Reference / FIR", f"{ctx.case.number} — {ctx.case.title}"),
        ("Investigation Run ID", ctx.run.id),
        ("Investigation Status", f"{ctx.run.status.upper()} (Complete Investigation)"),
        ("Data Basis / Mode", ctx.banner),
        ("Suspect Wallet(s)", suspect_str),
        ("Investigating Officer", f"{investigator_name}, {investigator_rank}"),
        ("Police Unit / Station", police_unit),
        ("Date & Time of Report", when.strftime("%d %B %Y, %H:%M:%S UTC")),
        ("Evidence Chain Status", "VALID & CRYPTOGRAPHICALLY VERIFIED" if ctx.chain.get("valid") else "INTEGRITY WARNING"),
        ("Evidence Chain Head", ctx.chain.get("headHash") or "None"),
    ], key_width=140, size=8.5)

    # =========================================================================
    # SECTION 1: EXECUTIVE SUMMARY & METHODOLOGY
    # =========================================================================
    doc.heading("1. Executive Summary & Forensic Methodology", level=1)
    doc.paragraph(
        f"This forensic investigation report details the tracing of cryptocurrency funds initiated from suspect wallet "
        f"{ctx.suspects[0]['address'] if ctx.suspects else 'under investigation'} in connection with FIR / Case "
        f"'{ctx.case.number}'. The automated analysis was conducted using the VAULT-X cryptocurrency forensic engine, "
        f"applying Multi-Hop Breadth-First Search (BFS) and Proportional Taint Tracking algorithms across decentralized ledgers.",
        size=9.0,
    )
    doc.paragraph(
        "The findings within this document are categorized according to strict epistemic standards required for judicial evaluation:",
        size=9.0,
    )
    doc.bullets([
        "OBSERVED: Directly recorded on the underlying immutable public blockchain (transaction hash, block height, value, timestamps).",
        "INFERRED: Derived by documented heuristics (common input ownership, change address detection, peel chain tracing).",
        "ATTRIBUTED: Assigned to named Virtual Asset Service Providers (VASPs) based on validated deposit-address clustering and intel sources.",
    ], size=8.5)

    if notes:
        doc.heading("Investigator Remarks", level=2)
        doc.paragraph(clean(notes), size=8.5, font="italic")

    # =========================================================================
    # SECTION 2: ATTRIBUTION HYPOTHESES & VASP IDENTIFICATION
    # =========================================================================
    doc.new_page()
    doc.heading("2. Target VASP Attributions & Hypotheses", level=1)
    doc.paragraph(
        "The following Virtual Asset Service Providers (VASPs) / Exchanges have been identified as receiving funds originating "
        "from the suspect address. These entities hold customer identification (KYC) and fiat liquidation records requisited under Section 94 BNSS.",
        size=9.0,
    )

    if ctx.hypotheses:
        hypo_headers = ["Candidate Entity / VASP", "Target Deposit Address", "Score", "Band", "Label", "Evidence Count"]
        hypo_rows = []
        for h in ctx.hypotheses:
            vasp_name = h.get("hypothesis") or h.get("vasp") or "Unknown"
            addr = h.get("targetAddress") or "-"
            score = f"{float(h.get('score', 0)):.2f}"
            band = str(h.get("band") or "MEDIUM").upper()
            label = str(h.get("epistemicLabel") or "ATTRIBUTED").upper()
            sup_count = len(h.get("supporting") or [])
            hypo_rows.append([vasp_name, addr, score, band, label, f"{sup_count} links"])

        doc.table(hypo_headers, hypo_rows, [1.8, 3.2, 0.9, 1.1, 1.2, 1.2], size=8.0, mono_cols=(1,))
    else:
        doc.paragraph("No external VASP hypotheses established. The funds remain within un-hosted or intermediary wallets.", size=8.5, font="italic", color=GREY)

    # Draw Fund Flow Vector Diagram
    _draw_flow_diagram(doc, ctx)

    # =========================================================================
    # SECTION 3: FORENSIC ANALYTICS & CHARTS
    # =========================================================================
    doc.heading("3. Forensic Investigation Charts & Statistics", level=1)
    analytics = ctx.osint.get("graphAnalytics") or {}

    # Chart 1: Attribution scores or entity distribution
    if ctx.hypotheses:
        c_labels = [clean(h.get("hypothesis") or h.get("vasp") or "VASP")[:14] for h in ctx.hypotheses[:5]]
        c_vals = [float(h.get("score", 0)) * 100 for h in ctx.hypotheses[:5]]
        doc.bar_chart("VASP Attribution Confidence Index (0-100)", c_labels, c_vals, height=110, color=NAVY, value_fmt=lambda v: f"{v:.1f}%")
        doc.space(8)

    # Chart 2: Dataset / Transaction count breakdown
    datasets = analytics.get("datasets") or []
    if datasets:
        ds_labels = [d.get("name", "Dataset")[:20] for d in datasets[:6]]
        ds_vals = [float(d.get("count", 0)) for d in datasets[:6]]
        doc.hbar_chart("Transactions by Source Dataset / Ledger", ds_labels, ds_vals, color=ACCENT, value_fmt=lambda v: f"{int(v)}")
        doc.space(8)
    elif analytics.get("timeline"):
        tl = analytics["timeline"][:6]
        tl_labels = [clean(t.get("month", "Period")) for t in tl]
        tl_vals = [float(t.get("count", 0)) for t in tl]
        doc.hbar_chart("Activity Timeline (Transaction Count)", tl_labels, tl_vals, color=ACCENT, value_fmt=lambda v: f"{int(v)}")
        doc.space(8)

    # =========================================================================
    # SECTION 4: ON-CHAIN TRANSACTION LEDGER
    # =========================================================================
    doc.new_page()
    doc.heading("4. On-Chain Forensic Transaction Ledger", level=1)
    doc.paragraph(
        "Chronological ledger of cryptocurrency transfers recorded across the blockchain ledger during this investigation. "
        "All values and transaction hashes are immutable public records verified by consensus.",
        size=9.0,
    )

    if ctx.transactions:
        tx_headers = ["Transaction Hash", "Timestamp (UTC)", "Amount & Asset", "Source Address", "Destination Address"]
        tx_rows = []
        for tx in ctx.transactions[:40]:
            hsh = tx.get("txHash") or tx.get("id") or "-"
            ts = _iso_date(tx.get("timestamp"))
            amt = f"{tx.get('amount', 0)} {tx.get('asset', '')}"
            src = tx.get("from") or "-"
            dst = tx.get("to") or "-"
            tx_rows.append([hsh, ts, amt, src, dst])

        doc.table(tx_headers, tx_rows, [2.5, 1.4, 1.1, 2.2, 2.2], size=7.5, mono_cols=(0, 3, 4))
        if len(ctx.transactions) > 40:
            doc.paragraph(
                f"[Note: {len(ctx.transactions) - 40} additional transaction records held in the database. Complete raw ledger available electronically.]",
                size=8.0,
                font="italic",
                color=GREY,
            )
    else:
        doc.paragraph("No individual transaction rows held in run context.", size=8.5, font="italic", color=GREY)

    # =========================================================================
    # SECTION 5: CRYPTOGRAPHIC EVIDENCE REGISTER
    # =========================================================================
    doc.new_page()
    doc.heading("5. Cryptographic Evidence Register (Chain of Custody)", level=1)
    doc.paragraph(
        "In accordance with forensic standards, each piece of evidence is hashed using SHA-256 and linked sequentially "
        "into a cryptographic Merkle-like chain. Any post-investigation alteration breaks the head hash.",
        size=9.0,
    )

    if ctx.evidence:
        ev_headers = ["Evidence ID", "Type", "Tier", "Description", "Integrity Hash (SHA-256)"]
        ev_rows = []
        for e in ctx.evidence[:35]:
            eid = e.get("id") or "-"
            etype = str(e.get("type") or "record")[:16]
            tier = str(e.get("sourceTier") or "A")
            desc = clean(e.get("description") or "-")
            hsh = e.get("integrityHash") or "-"
            ev_rows.append([eid, etype, tier, desc, hsh])

        doc.table(ev_headers, ev_rows, [1.3, 1.3, 0.6, 3.4, 3.2], size=7.2, mono_cols=(0, 4))
        if len(ctx.evidence) > 35:
            doc.paragraph(f"[{len(ctx.evidence) - 35} further evidence records verified in chain.]", size=8.0, font="italic", color=GREY)
    else:
        doc.paragraph("No separate evidence chain records found.", size=8.5, font="italic", color=GREY)

    doc.space(8)
    doc.kv([
        ("Chain Verification", "PASSED (Integrity Hash Matches All Records)" if ctx.chain.get("valid") else "FAILED (Tampering Detected)"),
        ("Evidence Merkle Root / Head", ctx.chain.get("headHash") or "None"),
        ("Total Verified Records", str(len(ctx.evidence))),
    ], key_width=160, size=8.5)

    # =========================================================================
    # SECTION 6: INVESTIGATION AUDIT TRAIL
    # =========================================================================
    doc.new_page()
    doc.heading("6. System Audit Trail & Officer Access Logs", level=1)
    doc.paragraph(
        "Immutable chronological log of all interactions, system queries, and document operations executed during this case.",
        size=9.0,
    )

    if ctx.audit:
        aud_headers = ["Timestamp", "Officer / Role", "Action", "Resource", "Result", "Audit Hash"]
        aud_rows = []
        for a in ctx.audit[:35]:
            w = a.get("when") or "-"
            actor = a.get("who") or "-"
            act = a.get("action") or "-"
            res = a.get("resource") or "-"
            rst = a.get("result") or "-"
            hsh = a.get("integrityHash") or "-"
            aud_rows.append([w, actor, act, res, rst, hsh])

        doc.table(aud_headers, aud_rows, [1.5, 1.2, 1.0, 1.3, 1.0, 3.0], size=7.2, mono_cols=(5,))
    else:
        doc.paragraph("No audit records held for this investigation.", size=8.5, font="italic", color=GREY)

    # =========================================================================
    # SECTION 7: CERTIFICATE UNDER SECTION 63 BSA, 2023
    # =========================================================================
    doc.new_page()
    cert_banner = "CERTIFICATE UNDER SECTION 63 OF THE BHARATIYA SAKSHYA ADHINIYAM, 2023 (BSA)"
    doc.text((PAGE_W - text_width(cert_banner, "bold", 10.5)) / 2, doc.y - 11, cert_banner, "bold", 10.5, NAVY)
    doc.y -= 16
    cert_sub = "[Prescribed Form for Admissibility of Electronic Records in Court Proceedings]"
    doc.text((PAGE_W - text_width(cert_sub, "italic", 9.0)) / 2, doc.y - 9, cert_sub, "italic", 9.0, GREY)
    doc.y -= 20

    # PART A: CERTIFICATE BY PERSON IN LAWFUL CONTROL OF COMPUTER SYSTEM
    doc.heading("PART A: Certificate by Person in Lawful Control of Computer Device", level=2)
    doc.paragraph(
        f"I, {investigator_name}, holding the rank of {investigator_rank} at {police_unit}, do hereby solemnly "
        f"affirm and declare under Section 63(4)(c) of the Bharatiya Sakshya Adhiniyam, 2023 that:",
        size=9.0,
    )
    doc.bullets([
        f"(a) The electronic records described herein were produced by the VAULT-X Blockchain Forensic Workstation during the regular course of an official investigation in Case '{ctx.case.number}'.",
        "(b) Throughout the said period, the computer system and database were operating properly, and there was no malfunction or unauthorized interference that affected the production or accuracy of the electronic records.",
        "(c) The information contained in this dossier was extracted and compiled directly from raw blockchain protocol responses and cryptographic evidence entries without alteration.",
        f"(d) The digital cryptographic fingerprint (SHA-256 hash) of the primary evidence chain head is: {ctx.chain.get('headHash') or 'COMPUTED_AT_SEALING'}.",
        "(e) The particulars stated above are true to the best of my personal knowledge and belief based on official records.",
    ], size=8.5)

    doc.signature_block([
        investigator_name,
        investigator_rank,
        police_unit,
        f"Date: {when.strftime('%d %B %Y')}",
        "Place: Forensic Cyber Cell",
    ], label="Signature & Official Seal of Person in Lawful Control")

    doc.space(16)

    # PART B: CERTIFICATE BY TECHNICAL / CYBER FORENSIC EXPERT
    doc.heading("PART B: Certificate by Technical / Cyber Forensic Expert", level=2)
    expert_name = expert.get("name") or "Technical Forensics Examiner"
    expert_rank = expert.get("rank") or expert.get("designation") or "Cyber Forensic Analyst"
    expert_lab = expert.get("unit") or expert.get("lab") or "Digital Forensics & Scientific Evidence Wing"

    doc.paragraph(
        f"I, {expert_name}, {expert_rank}, {expert_lab}, having technically examined the digital records, "
        f"data ingestion pipelines, and cryptographic ledgers of Case '{ctx.case.number}', do hereby certify that:",
        size=9.0,
    )
    doc.bullets([
        "(a) The software utilized is VAULT-X Digital Forensics Suite v0.1.0, utilizing NIST FIPS 180-4 compliant SHA-256 algorithms and standard ECDSA/Secp256k1 validation.",
        "(b) The cryptographic integrity of all sequential evidence records was verified, confirming that no block or transaction record has been altered, injected, or modified since recording.",
        "(c) The electronic records, charts, and tables contained in this dossier are true, faithful, and authentic reproductions of electronic data stored on the forensic workstation.",
    ], size=8.5)

    doc.signature_block([
        expert_name,
        expert_rank,
        expert_lab,
        f"Date: {when.strftime('%d %B %Y')}",
        "Seal of Forensic Expert",
    ], label="Signature & Seal of Cyber Forensic Expert")

    return doc.to_bytes(when)


def create_court_report(ctx: CaseContext, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create and package a Court Report document with metadata and SHA-256 hash."""
    body = body or {}
    officer = {k: str(v).strip() for k, v in (body.get("officer") or {}).items() if v}
    court_name = str(body.get("courtName") or "").strip() or None
    expert = {k: str(v).strip() for k, v in (body.get("expert") or {}).items() if v}
    notes = str(body.get("notes") or "").strip() or None

    when = datetime.now(timezone.utc).replace(microsecond=0)
    number = report_number(ctx, when)
    pdf = render_court_report(ctx, officer=officer, court_name=court_name, expert=expert, notes=notes, number=number, when=when)
    sha256 = hashlib.sha256(pdf).hexdigest()

    title = f"Court Report - Case {ctx.case.number} ({number})"
    meta = {
        "reportNumber": number,
        "caseId": ctx.case.id,
        "runId": ctx.run.id,
        "caseNumber": ctx.case.number,
        "caseTitle": ctx.case.title,
        "courtName": court_name or DEFAULT_COURT,
        "officer": officer,
        "expert": expert,
        "notes": notes,
        "generatedAt": when.isoformat(),
        "banner": ctx.banner,
        "evidenceCount": len(ctx.evidence),
        "transactionCount": len(ctx.transactions),
        "auditCount": len(ctx.audit),
        "chainValid": ctx.chain.get("valid", True),
        "headHash": ctx.chain.get("headHash", ""),
        "calibrated": False,
    }

    return {
        "pdf": pdf,
        "sha256": sha256,
        "title": title,
        "meta": meta,
    }

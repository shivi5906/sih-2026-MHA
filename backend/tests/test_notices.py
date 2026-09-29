import re
import socket
import threading
import zlib
from types import SimpleNamespace

import pytest

from app import mailer, notices
from app.case_context import CaseContext
from app.osint import build_osint_report
from app.pdf import PdfDocument

ADDR = "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo"
HYPS = [{"id": "Binance", "hypothesis": "Binance", "targetAddress": ADDR, "score": 0.95, "band": "HIGH", "epistemicLabel": "ATTRIBUTED", "supporting": ["EV-1"], "nextActions": []}]
TXS = [
    {"id": "t1", "txHash": "a" * 64, "from": "bc1qsuspect", "to": "bc1qmid", "amount": "0.5", "asset": "BTC", "chain": "Bitcoin", "timestamp": 1700000000},
    {"id": "t2", "txHash": "b" * 64, "from": "bc1qmid", "to": ADDR, "amount": "0.4", "asset": "BTC", "chain": "Bitcoin", "timestamp": 1700003600},
]


def make_ctx() -> CaseContext:
    return CaseContext(
        run=SimpleNamespace(id="run-1", manifest={}), case=SimpleNamespace(id="case-1", number="CYBER-TEST-1", title="Test case"),
        banner="FIXTURE TRACE (TEST DATA)", mode="fixture", suspects=[{"address": "bc1qsuspect", "chain": "Bitcoin"}], hypotheses=HYPS,
        transactions=TXS, evidence=[], chain={"valid": True, "headHash": "f" * 64, "count": 1}, audit=[], documents=[],
        osint=build_osint_report("run-1", "FIXTURE TRACE (TEST DATA)", HYPS, TXS),
    )


def pdf_text(pdf: bytes) -> str:
    """Concatenate the decompressed page streams so tests can search the drawn text."""
    out = []
    for m in re.finditer(rb"stream\n(.*?)\nendstream", pdf, re.S):
        try:
            out.append(zlib.decompress(m.group(1)).decode("cp1252"))
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
    for i, off in enumerate(offsets, start=1):
        assert pdf[int(off):int(off) + len(f"{i} 0 obj")] == f"{i} 0 obj".encode()


def test_pdf_writer_wraps_tables_across_pages():
    doc = PdfDocument("t", "left", "right", "footer")
    doc.heading("Heading")
    doc.table(["A", "B"], [[f"row {i}", "x" * 120] for i in range(80)], [1, 3])
    pdf = doc.to_bytes()
    assert_valid_pdf(pdf)
    assert pdf.count(b"/Type /Page ") >= 3
    assert "Page 1 of" in pdf_text(pdf)


def test_drafts_offer_found_channels_and_no_invented_contact():
    draft = notices.drafts(make_ctx())[0]
    assert draft["vasp"] == "Binance" and draft["priority"] == "HIGH"
    assert {c["platform"] for c in draft["channels"]} == {"X / Twitter", "Telegram", "Facebook", "Instagram"}
    assert draft["recipient"]["email"] is None and draft["recipient"]["verified"] is False


def test_notice_pdf_has_legal_basis_facts_and_annexure():
    built = notices.create_notice(make_ctx(), {"targetId": "Binance", "recipientEmail": "le@example.org", "officer": {"name": "Insp. A. Kumar", "unit": "Cyber Cell"}, "deadlineDays": 10})
    assert_valid_pdf(built["pdf"])
    text = pdf_text(built["pdf"])
    for expected in ["SECTION 94, BNSS 2023", "b" * 40, "UNCALIBRATED", "Annexure A", "Insp. A. Kumar", "le@example.org", "FIXTURE TRACE"]:
        assert expected in text, expected
    assert "a" * 64 not in text  # transfers into other addresses are not listed as facts
    assert built["meta"]["recipientEmail"] == "le@example.org" and built["meta"]["noticeNumber"].startswith("VX/CYBER-TEST-1/BINANCE/")
    assert len(built["sha256"]) == 64


def test_notice_rejects_bad_recipient_and_unknown_target():
    with pytest.raises(ValueError):
        notices.create_notice(make_ctx(), {"targetId": "Binance", "recipientEmail": "not-an-email"})
    with pytest.raises(ValueError):
        notices.create_notice(make_ctx(), {"targetId": "Nope", "recipientEmail": "le@example.org"})


def test_email_without_smtp_goes_to_outbox(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    result = mailer.send_email("le@example.org", "s", "b", b"%PDF", "n.pdf")
    assert result["mode"] == "outbox" and result["delivered"] is False


class SmtpSink:
    """Minimal SMTP server that accepts one message, for exercising the real send path."""

    def __init__(self):
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.data = b""
        self.rcpt = []
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        conn, _ = self.sock.accept()
        f = conn.makefile("rb")
        conn.sendall(b"220 sink\r\n")
        while True:
            line = f.readline()
            if not line:
                break
            cmd = line.strip().upper()
            if cmd.startswith((b"EHLO", b"HELO")):
                conn.sendall(b"250 sink\r\n")
            elif cmd.startswith(b"RCPT"):
                self.rcpt.append(line.strip())
                conn.sendall(b"250 ok\r\n")
            elif cmd == b"DATA":
                conn.sendall(b"354 go\r\n")
                while (chunk := f.readline()) != b".\r\n":
                    self.data += chunk
                conn.sendall(b"250 queued\r\n")
            elif cmd == b"QUIT":
                conn.sendall(b"221 bye\r\n")
                break
            else:
                conn.sendall(b"250 ok\r\n")
        conn.close()


def test_email_with_smtp_sends_pdf_attachment(monkeypatch):
    sink = SmtpSink()
    monkeypatch.setenv("SMTP_HOST", "127.0.0.1")
    monkeypatch.setenv("SMTP_PORT", str(sink.port))
    monkeypatch.setenv("SMTP_STARTTLS", "false")
    monkeypatch.setenv("SMTP_FROM", "cyber.cell@example.org")
    monkeypatch.delenv("SMTP_USER", raising=False)
    built = notices.create_notice(make_ctx(), {"targetId": "Binance", "recipientEmail": "le@example.org"})
    subject, body = notices.email_text(built["meta"], "CYBER-TEST-1")
    result = mailer.send_email("le@example.org", subject, body, built["pdf"], "notice.pdf")
    assert result["mode"] == "smtp" and result["delivered"] is True
    assert any(b"le@example.org" in r for r in sink.rcpt)
    assert b"application/pdf" in sink.data and b'filename="notice.pdf"' in sink.data

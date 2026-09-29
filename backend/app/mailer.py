"""Outbound e-mail for notices. Sends over SMTP when configured in .env, otherwise keeps an outbox record only."""
from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import make_msgid


def _flag(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def email_config() -> dict:
    host = os.getenv("SMTP_HOST", "").strip()
    return {
        "mode": "smtp" if host else "outbox",
        "host": host or None,
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER", "").strip() or None,
        "password": os.getenv("SMTP_PASSWORD", ""),
        "sender": os.getenv("SMTP_FROM", "").strip() or os.getenv("SMTP_USER", "").strip() or "vaultx@localhost",
        "starttls": _flag("SMTP_STARTTLS", "true"),
        "ssl": _flag("SMTP_SSL", "false"),
        "timeout": float(os.getenv("SMTP_TIMEOUT", "20")),
    }


def public_email_status() -> dict:
    cfg = email_config()
    return {"mode": cfg["mode"], "configured": cfg["mode"] == "smtp", "host": cfg["host"], "port": cfg["port"], "sender": cfg["sender"] if cfg["mode"] == "smtp" else None}


def send_email(to: str, subject: str, body: str, attachment: bytes, filename: str, cc: str | None = None) -> dict:
    cfg = email_config()
    if cfg["mode"] != "smtp":
        return {"channel": "email", "mode": "outbox", "delivered": False, "note": "SMTP is not configured in .env, so the notice was stored in the outbox and not sent."}
    msg = EmailMessage()
    msg["From"] = cfg["sender"]
    msg["To"] = to
    if cc:
        msg["Cc"] = cc
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain=cfg["sender"].split("@")[-1] or "localhost")
    msg.set_content(body)
    msg.add_attachment(attachment, maintype="application", subtype="pdf", filename=filename)
    if cfg["ssl"]:
        client: smtplib.SMTP = smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=cfg["timeout"], context=ssl.create_default_context())
    else:
        client = smtplib.SMTP(cfg["host"], cfg["port"], timeout=cfg["timeout"])
    with client:
        client.ehlo()
        if cfg["starttls"] and not cfg["ssl"] and client.has_extn("starttls"):
            client.starttls(context=ssl.create_default_context())
            client.ehlo()
        if cfg["user"]:
            client.login(cfg["user"], cfg["password"])
        refused = client.send_message(msg)
    return {"channel": "email", "mode": "smtp", "delivered": not refused, "messageId": msg["Message-ID"], "refused": list(refused) if refused else []}

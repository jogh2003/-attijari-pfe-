"""notifications.py — Envoi d'emails (SMTP) avec fallback non-bloquant
Configuré via variables d'environnement : SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, SMTP_USE_TLS
"""
import os
import smtplib
from email.message import EmailMessage
from typing import List

from app.core.logging_config import logger


def send_email(recipients: List[str], subject: str, body: str) -> bool:
    """Envoie un email aux destinataires. Retourne True si envoyé ou simulé avec succès."""
    smtp_host = os.getenv("SMTP_HOST")
    if not smtp_host:
        logger.warning("SMTP non configuré — envoi simulé vers %s", recipients)
        return True

    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user or "no-reply@attijaribank.tn")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    try:
        if use_tls:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)

        if smtp_user and smtp_password:
            server.login(smtp_user, smtp_password)

        server.send_message(msg)
        server.quit()
        logger.info("Email envoyé à %s (subject=%s)", recipients, subject)
        return True
    except Exception as exc:
        logger.warning("Échec envoi email à %s : %s", recipients, exc)
        return False

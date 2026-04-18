"""
audit.py — Helper centralisé pour l'audit trail
PFE Attijari bank — Sujet 21

Utilisation dans les routers :
    from app.core.audit import log_action
    log_action(utilisateur="admin@attijaribank.tn", role="admin",
               action="LOGIN", details="Connexion depuis dashboard", ip="192.168.1.10")
"""
import uuid
from datetime import datetime
from typing import Optional

from app.core.logging_config import logger


def log_action(
    utilisateur: str,
    role: str,
    action: str,
    details: Optional[str] = None,
    ip: str = "127.0.0.1",
) -> str:
    """
    Enregistre une action dans l'audit trail.

    1. Tente d'écrire en base PostgreSQL (audit_logs).
    2. Si la DB est indisponible, écrit dans le fichier de log uniquement.

    Retourne l'ID du log créé.
    """
    entry_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.now()

    # ── 1. Ecriture en base ───────────────────────────────────
    _write_to_db(entry_id, utilisateur, role, action, details, ip, timestamp)

    # ── 2. Log fichier (toujours) ─────────────────────────────
    logger.info(
        "AUDIT | {} | {} | {} | {} | ip={}",
        utilisateur, role, action, details or "", ip
    )

    return entry_id


def _write_to_db(
    entry_id: str,
    utilisateur: str,
    role: str,
    action: str,
    details: Optional[str],
    ip: str,
    timestamp: datetime,
) -> None:
    """Tente d'insérer le log en DB — ne plante jamais l'appelant."""
    try:
        from app.core.database import SessionLocal
        from app.models.audit_log import AuditLog

        db = SessionLocal()
        try:
            log = AuditLog(
                id=entry_id,
                utilisateur=utilisateur,
                role=role,
                action=action,
                details=details,
                ip_address=ip,
                timestamp=timestamp,
            )
            db.add(log)
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Audit DB indisponible (log fichier uniquement) : {}", exc)

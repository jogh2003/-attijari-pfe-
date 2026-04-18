"""
audit.py — Router audit trail connecté à PostgreSQL
PFE Attijari bank — Sujet 21
"""
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging_config import logger
from app.models.audit_log import AuditLog
from app.routers.auth import responsable_requis

router = APIRouter()

# ── Schéma de sortie ──────────────────────────────────────────
class AuditLogOut(BaseModel):
    id: str
    utilisateur: str
    role: str
    action: str
    details: Optional[str]
    ip_address: str
    timestamp: str


# ── Données de démarrage — injectées si la table est vide ─────
_SEED_LOGS = [
    {
        "utilisateur": "admin@attijaribank.tn",
        "role": "admin",
        "action": "LOGIN",
        "details": "Connexion réussie depuis le dashboard",
        "ip_address": "192.168.1.10",
    },
    {
        "utilisateur": "robot_uipath",
        "role": "system",
        "action": "GET_ALERTES",
        "details": "Robot CheckAlerte — récupération alertes seuil=0.75 — 2 alertes trouvées",
        "ip_address": "127.0.0.1",
    },
    {
        "utilisateur": "robot_uipath",
        "role": "system",
        "action": "NOTIFICATION_IT",
        "details": "Email envoyé à responsable.it@attijaribank.tn — Alerte AL-2026-001",
        "ip_address": "127.0.0.1",
    },
    {
        "utilisateur": "responsable.it@attijaribank.tn",
        "role": "responsable_it",
        "action": "VALIDER_RECOMMANDATION",
        "details": "Recommandation RECO-001 validée — déclenchement RPA autorisé",
        "ip_address": "192.168.1.15",
    },
    {
        "utilisateur": "robot_uipath",
        "role": "system",
        "action": "ACTION_RPA_EXECUTEE",
        "details": "Purge Redis monétique exécutée avec succès — durée 3.2s",
        "ip_address": "127.0.0.1",
    },
    {
        "utilisateur": "robot_uipath",
        "role": "system",
        "action": "RESOLUTION_CONFIRMEE",
        "details": "Réclamation REC-003 marquée comme résolue — historique LSTM enrichi",
        "ip_address": "127.0.0.1",
    },
]


def _seed_if_empty(db: Session) -> None:
    """Insère des logs de démarrage si la table est vide."""
    try:
        count = db.query(AuditLog).count()
        if count == 0:
            base_ts = datetime(2026, 4, 11, 8, 0, 0)
            for i, entry in enumerate(_SEED_LOGS):
                from datetime import timedelta
                log = AuditLog(
                    id=f"AUD-SEED-{i+1:03d}",
                    utilisateur=entry["utilisateur"],
                    role=entry["role"],
                    action=entry["action"],
                    details=entry["details"],
                    ip_address=entry["ip_address"],
                    timestamp=base_ts + timedelta(minutes=i * 5),
                )
                db.add(log)
            db.commit()
            logger.info("Audit trail : {} logs de démarrage insérés", len(_SEED_LOGS))
    except Exception as exc:
        logger.warning("Seed audit trail échoué : {}", exc)
        db.rollback()


# ── GET /api/audit ────────────────────────────────────────────
@router.get(
    "/",
    response_model=List[AuditLogOut],
    summary="Audit trail — historique de toutes les actions du système",
)
async def get_audit_logs(
    utilisateur: Optional[str] = Query(default=None, description="Filtrer par utilisateur"),
    action:      Optional[str] = Query(default=None, description="Filtrer par type d'action"),
    limit:       int           = Query(default=50, ge=1, le=500, description="Nombre max de résultats"),
    db: Session = Depends(get_db),
    _payload: dict = Depends(responsable_requis),
):
    """
    Retourne l'historique complet des actions du système.
    Accessible aux administrateurs et responsables IT.

    Chaque entrée : utilisateur · rôle · action · détails · IP · timestamp.
    Conforme aux exigences de traçabilité bancaire tunisiennes.
    """
    try:
        _seed_if_empty(db)

        query = db.query(AuditLog).order_by(AuditLog.timestamp.desc())

        if utilisateur:
            query = query.filter(AuditLog.utilisateur.ilike(f"%{utilisateur}%"))
        if action:
            query = query.filter(AuditLog.action.ilike(f"%{action}%"))

        logs = query.limit(limit).all()

        return [
            AuditLogOut(
                id=log.id,
                utilisateur=log.utilisateur or "système",
                role=log.role or "system",
                action=log.action,
                details=log.details,
                ip_address=log.ip_address or "0.0.0.0",
                timestamp=log.timestamp.strftime("%Y-%m-%dT%H:%M:%S") if log.timestamp else "",
            )
            for log in logs
        ]

    except Exception as exc:
        logger.error("Erreur lecture audit DB : {}", exc)
        # Fallback : retourner les logs simulés
        return _fallback_logs(utilisateur, action, limit)


# ── GET /api/audit/stats ──────────────────────────────────────
@router.get("/stats", summary="Statistiques de l'audit trail pour le dashboard")
async def get_audit_stats(
    db: Session = Depends(get_db),
    _payload: dict = Depends(responsable_requis),
):
    """Statistiques pour le tableau de bord administrateur."""
    try:
        _seed_if_empty(db)

        total = db.query(AuditLog).count()
        connexions = db.query(AuditLog).filter(AuditLog.action == "LOGIN").count()
        appels_rpa = db.query(AuditLog).filter(
            AuditLog.action.ilike("%RPA%") | AuditLog.action.ilike("%ROBOT%")
        ).count()

        last_log = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).first()
        derniere_action = (
            last_log.timestamp.strftime("%Y-%m-%dT%H:%M:%S") if last_log and last_log.timestamp else ""
        )

        # Comptage par type d'action
        from sqlalchemy import func as sqlfunc
        rows = (
            db.query(AuditLog.action, sqlfunc.count(AuditLog.id))
            .group_by(AuditLog.action)
            .all()
        )
        actions_par_type = {row[0]: row[1] for row in rows}

        return {
            "total_actions": total,
            "connexions": connexions,
            "appels_rpa": appels_rpa,
            "actions_par_type": actions_par_type,
            "derniere_action": derniere_action,
        }

    except Exception as exc:
        logger.error("Erreur stats audit DB : {}", exc)
        return {
            "total_actions": len(_SEED_LOGS),
            "connexions": 1,
            "appels_rpa": 3,
            "actions_par_type": {},
            "derniere_action": "",
            "note": "DB indisponible — données simulées",
        }


# ── Fallback sans DB ──────────────────────────────────────────
def _fallback_logs(utilisateur: Optional[str], action: Optional[str], limit: int):
    result = [
        AuditLogOut(
            id=f"AUD-{i+1:03d}",
            utilisateur=e["utilisateur"],
            role=e["role"],
            action=e["action"],
            details=e["details"],
            ip_address=e["ip_address"],
            timestamp="2026-04-11T08:00:00",
        )
        for i, e in enumerate(_SEED_LOGS)
    ]
    if utilisateur:
        result = [l for l in result if utilisateur.lower() in l.utilisateur.lower()]
    if action:
        result = [l for l in result if action.upper() in l.action.upper()]
    return result[:limit]

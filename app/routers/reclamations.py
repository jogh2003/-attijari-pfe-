"""
reclamations.py — Router réclamations sur données réelles Attijari bank
PFE Sujet 21
"""
import os
import uuid
import re
from datetime import datetime
from typing import List, Optional

import pandas as pd
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.audit import log_action
from app.core.database import get_db
from app.core.logging_config import logger
from app.models.reclamation import Reclamation
from app.routers.auth import verifier_token
from app.services.hybrid_detection import detecter_hybride

router = APIRouter()

# ── Charger les données réelles ───────────────────────────────
DF_RECLAMATIONS = None


def charger_donnees() -> None:
    global DF_RECLAMATIONS
    for path in [
        "data/processed/dataset_nlp_enrichi.csv",
        "data/cleaned/reclamations_propres.csv",
    ]:
        if os.path.exists(path):
            DF_RECLAMATIONS = pd.read_csv(path, on_bad_lines="skip")
            # Trier par date décroissante (tickets récents en premier)
            if "date" in DF_RECLAMATIONS.columns:
                DF_RECLAMATIONS["date"] = pd.to_datetime(
                    DF_RECLAMATIONS["date"], errors="coerce"
                )
                DF_RECLAMATIONS = DF_RECLAMATIONS.sort_values(
                    "date", ascending=False, na_position="last"
                ).reset_index(drop=True)
            logger.info("Réclamations : {} tickets chargés ({})", len(DF_RECLAMATIONS), path)
            _charger_reclamations_postgres()
            return
            logger.warning("Données réclamations non trouvées — tentative de chargement PostgreSQL")
            _charger_reclamations_postgres()


def _charger_reclamations_postgres() -> None:
    """Ajoute les tickets soumis en PostgreSQL au DataFrame mémoire pour dashboard et UiPath."""
    global DF_RECLAMATIONS
    try:
        from app.core.database import SessionLocal
        from app.models.reclamation import Reclamation as ReclamationModel

        db = SessionLocal()
        rows = db.query(ReclamationModel).order_by(ReclamationModel.date.desc()).all()
        db.close()
        if not rows:
            return

        data = []
        for row in rows:
            data.append({
                "id": row.id,
                "date": row.date,
                "type_operation": row.type_operation,
                "categorie": row.categorie or "",
                "objet": row.objet or row.description or "",
                "description": row.description or "",
                "action_effectuee": row.action_effectuee or "",
                "severite": row.severite,
                "statut": row.statut,
                "priorite_orig": row.priorite_orig or "",
                "type_demande": row.type_demande or "Réclamation",
                "en_retard": row.en_retard or False,
                "duree_resolution_min": row.duree_resolution_min or 0.0,
                "score_anomalie": row.score_anomalie,
                "score_risque": row.score_risque,
            })

        df_postgres = pd.DataFrame(data)
        if "date" in df_postgres.columns:
            df_postgres["date"] = pd.to_datetime(df_postgres["date"], errors="coerce")

        if DF_RECLAMATIONS is None:
            DF_RECLAMATIONS = df_postgres
        else:
            DF_RECLAMATIONS = pd.concat([DF_RECLAMATIONS, df_postgres], ignore_index=True)
            DF_RECLAMATIONS = DF_RECLAMATIONS.drop_duplicates(subset=["id"], keep="first")
            if "date" in DF_RECLAMATIONS.columns:
                DF_RECLAMATIONS = DF_RECLAMATIONS.sort_values("date", ascending=False, na_position="last").reset_index(drop=True)

        logger.info("Réclamations PostgreSQL ajoutées au DataFrame : {} tickets total", len(DF_RECLAMATIONS))
    except Exception as exc:
        logger.warning("Chargement réclamations PostgreSQL échoué : {}", exc)


try:
    charger_donnees()
except Exception as exc:
    logger.error("Erreur chargement données : {}", exc)


# ── Schémas ────────────────────────────────────────────────────
class ReclamationOut(BaseModel):
    id: str
    date: str
    type_operation: str
    categorie: str
    objet: str
    action_effectuee: Optional[str]
    severite: int
    statut: str
    priorite_orig: str
    type_demande: str
    en_retard: bool
    duree_resolution_min: float
    score_anomalie: Optional[float]
    score_risque: Optional[float]


class AnalyseNLPIn(BaseModel):
    description: str
    type_operation: str
    categorie: Optional[str] = ""
    severite: int = 2


# ── GET /reclamations ─────────────────────────────────────────
@router.get("/", summary="Liste des réclamations réelles Attijari bank")
async def get_reclamations(
    statut:         Optional[str]  = Query(default=None, description="Filtrer par statut"),
    type_operation: Optional[str]  = Query(default=None, description="Filtrer par groupe"),
    type_demande:   Optional[str]  = Query(default=None, description="Réclamation ou Demande de Service"),
    en_retard:      Optional[bool] = Query(default=None, description="Tickets en retard SLA"),
    severite_min:   Optional[int]  = Query(default=None, ge=1, le=4, description="Sévérité minimum 1–4"),
    limit:          int            = Query(default=50,  ge=1, le=500, description="Nombre max de résultats"),
    offset:         int            = Query(default=0,   ge=0, description="Pagination"),
    payload: dict = Depends(verifier_token),
):
    """
    Retourne les tickets réels Attijari bank (Fév–Mars 2026).
    1507 tickets uniques après dédoublonnage.
    """
    if DF_RECLAMATIONS is None:
        return {"message": "Données non chargées", "data": [], "total": 0}

    df = DF_RECLAMATIONS.copy()

    if statut:
        df = df[df["statut"] == statut]
    if type_operation:
        df = df[df["type_operation"].str.contains(type_operation, case=False, na=False)]
    if type_demande:
        df = df[df["type_demande"] == type_demande]
    if en_retard is not None:
        df = df[df["en_retard"] == en_retard]
    if severite_min is not None:
        df = df[df["severite"] <= severite_min]

    # Trier par date décroissante (tickets récents en premier)
    # Forcer la conversion en datetime pour éviter le mélange Timestamp/str
    if "date" in df.columns:
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values("date", ascending=False, na_position="last")

    total = len(df)
    df    = df.iloc[offset : offset + limit]

    cols = [
        "id", "date", "type_operation", "categorie", "objet", "description",
        "action_effectuee", "severite", "statut", "priorite_orig",
        "type_demande", "en_retard", "duree_resolution_min",
        "score_anomalie", "score_risque",
    ]
    nullable = {"score_anomalie", "score_risque", "action_effectuee", "description"}

    result = []
    for _, row in df.iterrows():
        rec = {}
        for col in cols:
            val = row.get(col, "")
            if pd.isna(val):
                val = None if col in nullable else ""
            rec[col] = val
        result.append(rec)

    logger.debug(
        "GET /reclamations → {} / {} tickets ({} filtres)",
        len(result), total, sum(1 for x in [statut, type_operation, type_demande, en_retard, severite_min] if x is not None)
    )
    return {"total": total, "offset": offset, "limit": limit, "data": result}


# ── GET /reclamations/stats ───────────────────────────────────
@router.get("/stats", summary="Statistiques pour le dashboard")
async def get_stats(payload: dict = Depends(verifier_token)):
    """Statistiques globales pour les graphiques Chart.js du binôme."""
    if DF_RECLAMATIONS is None:
        return {"erreur": "Données non chargées"}

    df = DF_RECLAMATIONS

    groupes   = df["type_operation"].value_counts().head(8).to_dict()
    priorites = df["priorite_orig"].value_counts().to_dict()
    statuts   = df["statut"].value_counts().to_dict()

    total_retard = int(df["en_retard"].sum())
    pct_retard   = round(float(df["en_retard"].mean()) * 100, 1)
    score_col    = "score_anomalie" if "score_anomalie" in df.columns else None
    score_moy    = round(float(df[score_col].mean()), 3) if score_col else 0
    nb_risque    = int((df[score_col] >= 0.75).sum()) if score_col else 0
    nb_surveill  = int(((df[score_col] >= 0.50) & (df[score_col] < 0.75)).sum()) if score_col else 0

    # Distribution par sévérité (1=Critique → 4=Basse)
    severite_distribution: dict = {}
    if "severite" in df.columns:
        sev_counts = df["severite"].value_counts().sort_index()
        severite_distribution = {int(k): int(v) for k, v in sev_counts.items()}

    # % retard SLA par groupe (groupes avec au moins 5 tickets)
    retard_par_groupe: dict = {}
    if "en_retard" in df.columns and "type_operation" in df.columns:
        grp = df.groupby("type_operation")["en_retard"].agg(["sum", "count"])
        retard_par_groupe = {
            g: round(float(row["sum"] / row["count"] * 100), 1)
            for g, row in grp.iterrows() if int(row["count"]) >= 5
        }

    return {
        "total_tickets":        len(df),
        "reclamations":         int((df["type_demande"] == "Réclamation").sum()),
        "demandes_service":     int((df["type_demande"] == "Demande de Service").sum()),
        "en_retard_sla":        total_retard,
        "pct_retard_sla":       pct_retard,
        "duree_moy_resolution": round(float(df["duree_resolution_min"].mean()), 0),
        "score_anomalie_moyen": score_moy,
        "tickets_risque_eleve": nb_risque,
        "tickets_surveillance": nb_surveill,
        "groupes":              groupes,
        "priorites":            priorites,
        "statuts":              statuts,
        "severite_distribution": severite_distribution,
        "retard_par_groupe":    retard_par_groupe,
        "source":               "Données réelles Attijari bank — Fév–Mars 2026",
    }


# ── GET /reclamations/export ──────────────────────────────────
@router.get("/export", summary="Export CSV des réclamations")
async def export_reclamations(payload: dict = Depends(verifier_token)):
    """Export CSV de toutes les réclamations (BOM UTF-8 pour Excel)."""
    import io
    from fastapi.responses import StreamingResponse

    if DF_RECLAMATIONS is None:
        raise HTTPException(status_code=503, detail="Données non disponibles")

    cols = [
        "id", "date", "type_operation", "categorie", "objet",
        "severite", "statut", "priorite_orig", "type_demande",
        "en_retard", "duree_resolution_min", "score_anomalie", "score_risque",
    ]
    export_cols = [c for c in cols if c in DF_RECLAMATIONS.columns]
    csv_bytes = DF_RECLAMATIONS[export_cols].to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

    utilisateur = payload.get("sub", "anonyme")
    log_action(
        utilisateur=utilisateur,
        role=payload.get("role", ""),
        action="EXPORT_CSV",
        details=f"Export {len(DF_RECLAMATIONS)} tickets",
    )
    logger.info("Export CSV : {} tickets ({})", len(DF_RECLAMATIONS), utilisateur)

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": "attachment; filename=reclamations_attijari.csv"},
    )


# ── Soumissions en mémoire (par utilisateur) ─────────────────
_SOUMISSIONS: dict = {}


class SoumissionIn(BaseModel):
    description: str
    type_operation: str = "Helpdesk"
    categorie: Optional[str] = ""
    severite: int = 3


# ── GET /reclamations/mes-tickets ─────────────────────────────
@router.get("/mes-tickets", summary="Tickets soumis par l'utilisateur connecté")
async def mes_tickets(
    payload: dict = Depends(verifier_token),
    db: Session = Depends(get_db),
):
    utilisateur = payload.get("sub", "anonyme")
    try:
        tickets_db = (
            db.query(Reclamation)
            .filter(Reclamation.soumis_par == utilisateur)
            .order_by(Reclamation.created_at.desc())
            .all()
        )
        tickets = [
            {
                "id":             t.id,
                "utilisateur":    t.soumis_par,
                "description":    t.description or "",
                "type_operation": t.type_operation,
                "severite":       t.severite,
                "score_anomalie": t.score_anomalie,
                "niveau":         (
                    "CRITIQUE"     if (t.score_anomalie or 0) >= 0.75 else
                    "SURVEILLANCE" if (t.score_anomalie or 0) >= 0.50 else
                    "NORMAL"
                ),
                "solution":       t.action_effectuee or "",
                "statut":         t.statut,
                "timestamp":      t.created_at.strftime("%Y-%m-%dT%H:%M:%S") if t.created_at else "",
            }
            for t in tickets_db
        ]
        return {"total": len(tickets), "data": tickets, "source": "postgresql"}
    except Exception as exc:
        logger.warning("DB indisponible pour mes-tickets, fallback mémoire : {}", exc)
        tickets = _SOUMISSIONS.get(utilisateur, [])
        return {"total": len(tickets), "data": list(reversed(tickets)), "source": "memoire"}


# ── GET /reclamations/{id} ────────────────────────────────────
@router.get("/{reclamation_id}", summary="Détail d'un ticket")
async def get_reclamation(reclamation_id: str, payload: dict = Depends(verifier_token)):
    if DF_RECLAMATIONS is None:
        raise HTTPException(status_code=503, detail="Données non chargées")

    row = DF_RECLAMATIONS[DF_RECLAMATIONS["id"] == reclamation_id]
    if row.empty:
        raise HTTPException(status_code=404, detail=f"Ticket {reclamation_id} non trouvé")

    r = row.iloc[0]
    return {col: (None if pd.isna(r[col]) else r[col]) for col in DF_RECLAMATIONS.columns}


# ── POST /reclamations/soumettre ──────────────────────────────
@router.post("/soumettre", summary="Utilisateur soumet une réclamation et reçoit la solution IA")
async def soumettre_reclamation(
    req: SoumissionIn,
    payload: dict = Depends(verifier_token),
    db: Session = Depends(get_db),
):
    """
    Flow utilisateur complet :
    1. Score NLP (anomalie)
    2. Recommandation LightGBM (action corrective)
    3. Sauvegarde en mémoire
    4. Retourne la solution avec niveau de risque
    """
    from app.routers.recommandations import recommander_lgbm, recommander_knn

    utilisateur = payload.get("sub", "anonyme")

    # ── Détection Hybride 3 niveaux ───────────────────────────
    from app.routers.predictions import XGB_MODEL as _XGB, LE_GROUPE as _LE_G
    detection = detecter_hybride(
        description    = req.description,
        type_operation = req.type_operation,
        categorie      = req.categorie or "",
        severite       = req.severite,
        xgb_model      = _XGB,
        le_groupe      = _LE_G,
    )
    score  = detection["score_anomalie"]
    niveau = detection["niveau"]
    alerte = detection["alerte_declenchee"]
    desc_lower = req.description.lower()

    systemes = [s for s in ["SWIFT", "Amplitude", "IDC", "Outlook", "VPN", "Firewall", "Redis", "NMR", "Tanit"]
                if s.lower() in desc_lower]

    # Recommandation LightGBM
    reco = recommander_lgbm(req.description, req.type_operation, req.categorie or "", req.severite)

    # Recommandation KNN incidents similaires
    knn_reco = recommander_knn(req.description, req.type_operation, req.categorie or "", req.severite)

    # Message contextuel adapté au niveau
    if niveau == "CRITIQUE":
        msg = "Votre réclamation a été escaladée en urgence au département IT. Un responsable vous contactera dans les 30 minutes."
    elif niveau == "SURVEILLANCE":
        msg = "Votre réclamation est prise en compte. Le département IT a été notifié et traitera votre demande dans les 2 heures."
    else:
        msg = "Votre réclamation est enregistrée. Appliquez la solution recommandée ci-dessous."

    rec_id = f"REC-{str(uuid.uuid4())[:6].upper()}"
    soumission = {
        "id": rec_id,
        "utilisateur": utilisateur,
        "description": req.description[:200],
        "type_operation": req.type_operation,
        "severite": req.severite,
        "score_anomalie": score,
        "niveau": niveau,
        "solution": reco["action_suggeree"],
        "statut": "ouverte",
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
    _SOUMISSIONS.setdefault(utilisateur, []).append(soumission)

    # ── Mise à jour du DataFrame en mémoire (visible dans GET /reclamations/) ──
    global DF_RECLAMATIONS
    if DF_RECLAMATIONS is not None:
        new_row = {
            "id":                   rec_id,
            "date":                 pd.Timestamp.now(),
            "type_operation":       req.type_operation,
            "categorie":            req.categorie or "",
            "objet":                req.description[:200],
            "action_effectuee":     reco["action_suggeree"],
            "severite":             req.severite,
            "statut":               "ouverte",
            "priorite_orig":        "haute" if req.severite <= 2 else "normale",
            "type_demande":         "Réclamation",
            "en_retard":            False,
            "duree_resolution_min": 0.0,
            "score_anomalie":       score,
            "score_risque":         round(score * 0.95, 3),
        }
        DF_RECLAMATIONS = pd.concat(
            [DF_RECLAMATIONS, pd.DataFrame([new_row])], ignore_index=True
        )
        logger.info("Ticket {} ajouté au DataFrame (total={})", rec_id, len(DF_RECLAMATIONS))

    # ── Sauvegarde PostgreSQL ─────────────────────────────────
    try:
        rec_db = Reclamation(
            id=rec_id,
            date=datetime.now(),
            type_operation=req.type_operation,
            categorie=req.categorie or "",
            description=req.description[:500],
            severite=req.severite,
            statut="ouverte",
            score_anomalie=score,
            score_risque=round(score * 0.95, 3),
            soumis_par=utilisateur,
        )
        db.add(rec_db)
        db.commit()
        logger.info("Ticket {} sauvegardé en PostgreSQL ({})", rec_id, utilisateur)
    except Exception as exc:
        logger.warning("Sauvegarde DB échouée, ticket en mémoire uniquement : {}", exc)
        db.rollback()

    log_action(
        utilisateur=utilisateur,
        role=payload.get("role", ""),
        action="SOUMISSION_RECLAMATION",
        details=f"Ticket={rec_id} | Score={score} | Niveau={niveau} | Alerte={alerte}",
    )
    logger.info("Soumission réclamation {} — score={} niveau={} ({})", rec_id, score, niveau, utilisateur)

    return {
        "reclamation_id":            rec_id,
        "score_anomalie":            score,
        "score_risque":              detection["score_risque"],
        "niveau":                    niveau,
        "alerte_declenchee":         alerte,
        "systemes_detectes":         systemes,
        "solution":                  reco["action_suggeree"],
        "confidence_lightgbm":       reco["taux_succes"],
        "alternatives_lightgbm":     reco.get("cas_similaires", []),
        "action_similaire_knn":      knn_reco["action_suggeree"],
        "similarite_knn":            knn_reco["similarite_moyenne"],
        "incidents_similaires":      knn_reco.get("incidents_similaires", []),
        "priorite_recommandation":   reco["priorite"],
        "methode_recommandation":    "LightGBM + KNN",
        "methode_detection":         detection["methode_detection"],
        "niveau_detection":          detection["niveau_detection"],
        "detail_detection":          detection.get("detail", ""),
        "message_utilisateur":       msg,
        "timestamp":                 datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }


# ── POST /reclamations/analyser ───────────────────────────────
@router.post("/analyser", summary="Analyser un ticket via NLP")
async def analyser_reclamation(req: AnalyseNLPIn, payload: dict = Depends(verifier_token)):
    """
    Analyse un ticket via l'architecture hybride (Score Anomalie + XGBoost).
    NIVEAU 1 : Score Anomalie (règles, < 10ms)
    NIVEAU 2 : XGBoost confirmation (zone grise 0.60–0.75)
    """
    from app.routers.predictions import XGB_MODEL as _XGB, LE_GROUPE as _LE_G
    from app.routers.recommandations import recommander_knn

    detection = detecter_hybride(
        description    = req.description,
        type_operation = req.type_operation,
        categorie      = req.categorie or "",
        severite       = req.severite,
        xgb_model      = _XGB,
        le_groupe      = _LE_G,
    )

    desc_lower = req.description.lower()
    systemes = [s for s in ["SWIFT", "Amplitude", "IDC", "Outlook", "VPN", "Firewall", "Redis", "NMR", "Tanit"]
                if s.lower() in desc_lower]
    erreurs  = [e for e in ["spam", "compromission", "blocage", "timeout", "authentification"]
                if e.lower() in desc_lower]

    utilisateur = payload.get("sub", "anonyme")
    log_action(
        utilisateur=utilisateur,
        role=payload.get("role", ""),
        action="ANALYSE_NLP",
        details=(
            f"Ticket analysé — score={detection['score_anomalie']} "
            f"| groupe={req.type_operation} "
            f"| méthode={detection['methode_detection']}"
        ),
    )
    logger.info(
        "Analyse hybride : score={} méthode={} niveau={} ({})",
        detection["score_anomalie"], detection["methode_detection"],
        detection["niveau"], utilisateur,
    )

    knn_reco = recommander_knn(req.description, req.type_operation, req.categorie or "", req.severite)

    return {
        "reclamation_id":    str(uuid.uuid4()),
        "texte_analyse":     req.description,
        "systemes_detectes": systemes,
        "erreurs_detectees": erreurs,
        "score_anomalie":    detection["score_anomalie"],
        "score_risque":      detection["score_risque"],
        "niveau":            detection["niveau"],
        "alerte_declenchee": detection["alerte_declenchee"],
        "methode_detection":    detection["methode_detection"],
        "niveau_detection":     detection["niveau_detection"],
        "label_methode":        detection["label_methode"],
        "detail_detection":     detection.get("detail", ""),
        "solution_knn":         knn_reco["action_suggeree"],
        "similarite_knn":       knn_reco["similarite_moyenne"],
        "incidents_similaires": knn_reco["incidents_similaires"],
        "methode":              "Architecture Hybride — Score Anomalie (N1) + XGBoost (N2) + KNN (N3)",
        "timestamp":            datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
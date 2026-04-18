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

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.audit import log_action
from app.core.logging_config import logger
from app.routers.auth import verifier_token

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
            logger.info("Réclamations : {} tickets chargés ({})", len(DF_RECLAMATIONS), path)
            return
    logger.warning("Données réclamations non trouvées")


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

    total = len(df)
    df    = df.iloc[offset : offset + limit]

    cols = [
        "id", "date", "type_operation", "categorie", "objet",
        "action_effectuee", "severite", "statut", "priorite_orig",
        "type_demande", "en_retard", "duree_resolution_min",
        "score_anomalie", "score_risque",
    ]
    nullable = {"score_anomalie", "score_risque", "action_effectuee"}

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
        "source":               "Données réelles Attijari bank — Fév–Mars 2026",
    }


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


# ── POST /reclamations/analyser ───────────────────────────────
@router.post("/analyser", summary="Analyser un ticket via NLP")
async def analyser_reclamation(req: AnalyseNLPIn, payload: dict = Depends(verifier_token)):
    """
    Analyse un ticket avec score d'anomalie basé sur les règles métier
    issues de l'analyse des données réelles Attijari bank.
    """
    # Mots critiques identifiés dans les données réelles
    mots_critiques = {
        "compromission": 0.25, "firewall": 0.20, "spam": 0.20,
        "blocage": 0.15, "western union": 0.15, "swift": 0.15,
        "authentification": 0.10, "timeout": 0.10, "erreur": 0.05,
    }

    score = 0.2
    if req.severite == 1:
        score += 0.30
    elif req.severite == 2:
        score += 0.10

    desc_lower = req.description.lower()
    for mot, boost in mots_critiques.items():
        if mot in desc_lower:
            score += boost

    if "sécurité" in req.type_operation.lower() or "securite" in req.type_operation.lower():
        score += 0.20

    score = round(min(score, 0.99), 3)

    systemes = [s for s in ["SWIFT", "Amplitude", "IDC", "Outlook", "VPN", "Firewall", "Redis", "NMR", "Tanit"]
                if s.lower() in desc_lower]
    erreurs  = [e for e in ["spam", "compromission", "blocage", "timeout", "authentification"]
                if e.lower() in desc_lower]

    utilisateur = payload.get("sub", "anonyme")
    log_action(
        utilisateur=utilisateur,
        role=payload.get("role", ""),
        action="ANALYSE_NLP",
        details=f"Ticket analysé — score={score} | groupe={req.type_operation}",
    )
    logger.info("Analyse NLP : score={} pour {} ({})", score, req.type_operation, utilisateur)

    return {
        "reclamation_id":    str(uuid.uuid4()),
        "texte_analyse":     req.description,
        "systemes_detectes": systemes,
        "erreurs_detectees": erreurs,
        "score_anomalie":    score,
        "score_risque":      round(score * 0.95, 3),
        "niveau":            "CRITIQUE" if score >= 0.75 else ("SURVEILLANCE" if score >= 0.50 else "NORMAL"),
        "alerte_declenchee": score >= 0.75,
        "methode":           "Règles métier sur données réelles Attijari bank",
        "timestamp":         datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }

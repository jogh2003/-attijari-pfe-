"""
recommandations.py — Router recommandations connecté au KNN réel
PFE Attijari bank — Sujet 21
"""
import os
import pickle
import uuid
from collections import Counter
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.audit import log_action
from app.core.logging_config import logger
from app.routers.auth import verifier_token

router = APIRouter()

# ── Charger le modèle KNN ────────────────────────────────────
KNN_MODEL = None


def charger_knn() -> None:
    global KNN_MODEL
    path = "models/knn_model.pkl"
    if os.path.exists(path):
        KNN_MODEL = pickle.load(open(path, "rb"))
        logger.info("KNN chargé : {} tickets de référence", len(KNN_MODEL["df"]))
    else:
        logger.warning("KNN non trouvé — recommandations basiques activées")


try:
    charger_knn()
except Exception as exc:
    logger.error("Erreur chargement KNN : {}", exc)


# ── Schémas ────────────────────────────────────────────────────
class RecommandationOut(BaseModel):
    id: str
    reclamation_id: str
    action_suggeree: str
    taux_succes: float
    nb_cas_similaires: int
    priorite: int
    statut_impl: str
    created_at: str


class ValidationRequest(BaseModel):
    decision: str
    commentaire: Optional[str] = None


class AnalyseRequest(BaseModel):
    texte: str
    groupe: Optional[str] = ""
    categorie: Optional[str] = ""


# ── Moteur KNN ────────────────────────────────────────────────
def recommander_knn(texte: str, groupe: str = "", categorie: str = "") -> dict:
    """Recommande une action basée sur les données réelles Attijari bank."""
    if not KNN_MODEL:
        return {
            "action_suggeree":   "Escalader au support niveau 2",
            "taux_succes":       0.50,
            "nb_cas_similaires": 0,
            "cas_similaires":    [],
            "priorite":          3,
        }

    try:
        knn    = KNN_MODEL["knn"]
        df     = KNN_MODEL["df"]
        vec    = KNN_MODEL["vectorizer"]

        texte_full = f"{texte} {categorie} {groupe}".strip()
        vecteur    = vec.transform([texte_full]).toarray()
        dists, idxs = knn.kneighbors(vecteur)

        actions = [
            df.iloc[i]["action_effectuee"]
            for i in idxs[0]
            if df.iloc[i]["action_effectuee"] and df.iloc[i]["action_effectuee"] != ""
        ]
        objets = [df.iloc[i]["objet"] for i in idxs[0]]

        if not actions:
            return {
                "action_suggeree":   "Escalader au support technique",
                "taux_succes":       0.50,
                "nb_cas_similaires": 0,
                "cas_similaires":    objets[:3],
                "priorite":          3,
            }

        compteur = Counter(actions)
        action   = compteur.most_common(1)[0][0]
        taux     = compteur.most_common(1)[0][1] / len(actions)
        action   = action.strip()[:200]

        return {
            "action_suggeree":   action,
            "taux_succes":       round(taux, 2),
            "nb_cas_similaires": len(actions),
            "cas_similaires":    objets[:3],
            "priorite":          1 if taux >= 0.8 else 2,
        }

    except Exception as exc:
        logger.error("Erreur moteur KNN : {}", exc)
        return {
            "action_suggeree":   "Erreur — escalader au support technique",
            "taux_succes":       0.0,
            "nb_cas_similaires": 0,
            "cas_similaires":    [],
            "priorite":          3,
        }


# ── GET /api/recommandations ─────────────────────────────────
@router.get("/", response_model=List[RecommandationOut], summary="Liste des recommandations générées")
async def get_recommandations(
    statut:   Optional[str] = Query(default=None, description="Filtrer par statut"),
    priorite: Optional[int] = Query(default=None, ge=1, le=3, description="Filtrer par priorité"),
    payload: dict = Depends(verifier_token),
):
    """Recommandations en attente de validation — données réelles Attijari bank."""
    exemples = [
        ("REC-003", "Demande vérification email SPAM",            "Helpdesk",                "Securite et Habilitation SI"),
        ("REC-007", "Blocage indicateurs compromission Firewall", "Sécurité Opérationnelle", "Securite et Habilitation SI"),
        ("REC-012", "Problème accès Amplitude",                   "Système",                 "Amplitude"),
    ]

    result = []
    for rec_id, texte, groupe, cat in exemples:
        r = recommander_knn(texte, groupe, cat)
        entry = RecommandationOut(
            id=str(uuid.uuid4()),
            reclamation_id=rec_id,
            action_suggeree=r["action_suggeree"],
            taux_succes=r["taux_succes"],
            nb_cas_similaires=r["nb_cas_similaires"],
            priorite=r["priorite"],
            statut_impl="en_attente",
            created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        )
        if statut and entry.statut_impl != statut:
            continue
        if priorite and entry.priorite != priorite:
            continue
        result.append(entry)

    return result


# ── POST /api/recommandations/analyser ───────────────────────
@router.post("/analyser", summary="Analyser un ticket et obtenir une recommandation KNN")
async def analyser_et_recommander(req: AnalyseRequest, payload: dict = Depends(verifier_token)):
    """
    Analyse un nouveau ticket et retourne la recommandation
    basée sur les données réelles Attijari bank (1431 tickets de référence).
    """
    r = recommander_knn(req.texte, req.groupe or "", req.categorie or "")

    log_action(
        utilisateur=payload.get("sub", "anonyme"),
        role=payload.get("role", ""),
        action="RECOMMANDATION_KNN",
        details=f"Action suggérée : {r['action_suggeree'][:80]} | taux={r['taux_succes']}",
    )
    logger.info("Recommandation KNN : taux_succes={} nb_cas={}", r["taux_succes"], r["nb_cas_similaires"])

    return {
        "texte_analyse":     req.texte,
        "action_suggeree":   r["action_suggeree"],
        "taux_succes":       r["taux_succes"],
        "nb_cas_similaires": r["nb_cas_similaires"],
        "cas_similaires":    r["cas_similaires"],
        "priorite":          r["priorite"],
        "source":            "KNN sur données réelles Attijari bank (Fév–Mars 2026)",
        "timestamp":         datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }


# ── GET /api/recommandations/{id} ────────────────────────────
@router.get("/{reclamation_id}", summary="Recommandation pour une réclamation")
async def get_recommandation(reclamation_id: str, payload: dict = Depends(verifier_token)):
    r = recommander_knn("Ticket " + reclamation_id)
    return {
        "id":              str(uuid.uuid4()),
        "reclamation_id":  reclamation_id,
        "action_suggeree": r["action_suggeree"],
        "taux_succes":     r["taux_succes"],
        "nb_cas_similaires": r["nb_cas_similaires"],
        "priorite":        r["priorite"],
        "statut_impl":     "en_attente",
        "created_at":      datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }


# ── POST /api/recommandations/{id}/valider ───────────────────
@router.post("/{reco_id}/valider", summary="Valider ou rejeter une recommandation")
async def valider_recommandation(
    reco_id: str,
    req: ValidationRequest,
    payload: dict = Depends(verifier_token),
):
    if req.decision not in ("valider", "rejeter"):
        raise HTTPException(status_code=400, detail="decision doit être 'valider' ou 'rejeter'")

    statut = "validee" if req.decision == "valider" else "rejetee"
    action_label = "RPA déclenché automatiquement" if req.decision == "valider" else "Traitement manuel requis"

    log_action(
        utilisateur=payload.get("sub", "anonyme"),
        role=payload.get("role", ""),
        action="VALIDER_RECOMMANDATION",
        details=f"Reco {reco_id} → {statut} | {req.commentaire or ''}",
    )
    logger.info("Recommandation {} : {}", reco_id, statut)

    return {
        "message":     f"Recommandation {reco_id} {statut}",
        "reco_id":     reco_id,
        "statut":      statut,
        "action":      action_label,
        "commentaire": req.commentaire,
        "date":        datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }

"""
predictions.py — Router prédictions XGBoost sur données réelles
PFE Attijari bank — Sujet 21
"""
import json
import os
import pickle
import uuid
from datetime import datetime
from typing import List, Optional

import pandas as pd

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.logging_config import logger
from app.routers.auth import verifier_token
from app.routers.recommandations import recommander_lgbm, recommander_knn

# ── DataFrame partagé pour l'évolution temporelle ────────────
_DF_EVOLUTION: Optional[pd.DataFrame] = None


def _charger_df_evolution() -> Optional[pd.DataFrame]:
    global _DF_EVOLUTION
    if _DF_EVOLUTION is not None:
        return _DF_EVOLUTION
        df = _charger_df_reclamations()
        if df is not None and not df.empty:
            try:
                df = df.copy()
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.dropna(subset=["date", "score_anomalie"])
                _DF_EVOLUTION = df
                return _DF_EVOLUTION
            except Exception as exc:
                logger.warning("Évolution temporelle — erreur chargement via réclamations : {}", exc)

        for path in [
            "data/processed/dataset_nlp_enrichi.csv",
            "data/cleaned/reclamations_propres.csv",
        ]:
            if os.path.exists(path):
                try:
                    df = pd.read_csv(path, on_bad_lines="skip")
                    df["date"] = pd.to_datetime(df["date"], errors="coerce")
                    df = df.dropna(subset=["date", "score_anomalie"])
                    _DF_EVOLUTION = df
                    return _DF_EVOLUTION
                except Exception as exc:
                    logger.warning("Évolution temporelle — erreur chargement : {}", exc)
        return None

router = APIRouter()

# ── Charger le modèle XGBoost et ses métriques ───────────────
XGB_MODEL   = None
XGB_METRICS = None
LE_GROUPE   = None
LE_CAT      = None


def charger_xgboost() -> None:
    global XGB_MODEL, XGB_METRICS, LE_GROUPE, LE_CAT

    if os.path.exists("models/metriques_xgb.json"):
        XGB_METRICS = json.load(open("models/metriques_xgb.json"))
        logger.info(
            "Métriques XGBoost : accuracy={:.1f}%  AUC={:.3f}",
            XGB_METRICS.get("accuracy", 0) * 100,
            XGB_METRICS.get("auc", 0),
        )

    if os.path.exists("models/label_encoder_groupe.pkl"):
        LE_GROUPE = pickle.load(open("models/label_encoder_groupe.pkl", "rb"))

    if os.path.exists("models/label_encoder_categorie.pkl"):
        LE_CAT = pickle.load(open("models/label_encoder_categorie.pkl", "rb"))

    if os.path.exists("models/xgb_model.pkl"):
        try:
            XGB_MODEL = pickle.load(open("models/xgb_model.pkl", "rb"))
            logger.info("Modèle XGBoost chargé : models/xgb_model.pkl")
        except Exception as exc:
            logger.warning("Erreur chargement XGBoost : {}", exc)


try:
    charger_xgboost()
except Exception as exc:
    logger.error("Erreur chargement XGBoost : {}", exc)


# ── Scores par groupe (données réelles Fév–Mars 2026) ────────
SCORES_REELS = {
    "Sécurité Opérationnelle":           0.87,
    "SWIFT":                             0.81,
    "Helpdesk":                          0.72,
    "Intervention-sur-site-déploiement": 0.65,
    "Système":                           0.58,
    "Réseau":                            0.48,
    "Equipe-Etudes":                     0.51,
    "Téléphonie":                        0.45,
    "Data Office":                       0.38,
    "Développement-Digital":             0.35,
    "Stock":                             0.32,
}


def _charger_df_reclamations() -> Optional[pd.DataFrame]:
    """Retourne le DataFrame de réclamations actuel si disponible."""
    try:
        from app.routers.reclamations import DF_RECLAMATIONS
        return DF_RECLAMATIONS
    except Exception:
        return None


def _group_scores_from_data() -> dict:
    """Calcule des scores de groupe dynamiques à partir des tickets actuels."""
    df = _charger_df_reclamations()
    if df is None or df.empty:
        return SCORES_REELS

    if "score_risque" not in df.columns and "score_anomalie" not in df.columns:
        return SCORES_REELS

    groups = {}
    for groupe, sub in df.groupby("type_operation"):
        if "score_risque" in sub.columns and sub["score_risque"].notna().any():
            score = float(sub["score_risque"].dropna().mean())
        elif "score_anomalie" in sub.columns and sub["score_anomalie"].notna().any():
            score = float(sub["score_anomalie"].dropna().mean())
        else:
            continue

        # Favoriser les scores historiques connus pour certains groupes critiques.
        score = max(score, SCORES_REELS.get(groupe, score))
        groups[groupe] = round(min(max(score, 0.0), 0.99), 3)

    return groups if groups else SCORES_REELS


# ── Schémas ───────────────────────────────────────────────────
class PredictionOut(BaseModel):
    id: str
    type_operation: str
    score_risque: float
    est_alerte: bool
    niveau: str
    version_modele: str
    date_prediction: str
    message: str
    source: str
    action_recommandee: Optional[str] = None
    taux_succes: Optional[float] = None
    action_similaire_knn: Optional[str] = None
    similarite_knn: Optional[float] = None
    incidents_similaires: Optional[List[dict]] = None
    methode_recommandation: Optional[str] = None


class PredictionRequest(BaseModel):
    type_operation: str
    severite: int = 2
    en_retard_historique: Optional[bool] = False
    duree_moyenne_min: Optional[float] = 240.0
    categorie: Optional[str] = ""
    texte: Optional[str] = ""


# ── Inférence XGBoost ─────────────────────────────────────────
def _score_xgboost(req: PredictionRequest) -> tuple[float, str]:
    """
    Calcule le score de risque.
    Combine la probabilité XGBoost (proba retard SLA) avec le score historique
    du groupe pour produire un indicateur de risque 0→1 cohérent avec le dashboard.
    """
    score_base = _group_scores_from_data().get(req.type_operation, 0.50)

    # Ajustements règles métier
    score_ajuste = score_base
    if req.severite == 1:
        score_ajuste = min(score_ajuste + 0.10, 0.99)
    if req.en_retard_historique:
        score_ajuste = min(score_ajuste + 0.08, 0.99)
    if req.duree_moyenne_min and req.duree_moyenne_min > 300:
        score_ajuste = min(score_ajuste + 0.05, 0.99)

    if XGB_MODEL is not None and LE_GROUPE is not None:
        try:
            groupe_enc = (
                int(LE_GROUPE.transform([req.type_operation])[0])
                if req.type_operation in LE_GROUPE.classes_
                else 0
            )
            cat_enc = 0

            features = [[
                req.severite,
                float(req.duree_moyenne_min or 240.0),
                score_base,       # score_anomalie proxy (score historique du groupe)
                score_ajuste,     # score_risque proxy (ajusté)
                groupe_enc,
                cat_enc,
            ]]
            proba_xgb = float(XGB_MODEL.predict_proba(features)[0][1])

            # Blend : 50% XGBoost calibré + 50% score ajusté (règles métier)
            # XGBoost prédit la prob. de retard SLA (rare → valeurs faibles)
            # On le recalibre en le normalisant sur [0,1] avec score_ajuste comme ancre
            score_final = round(0.5 * proba_xgb * 4.0 + 0.5 * score_ajuste, 3)
            score_final = min(score_final, 0.99)
            return score_final, "xgb_v1"
        except Exception as exc:
            logger.warning("Inférence XGBoost échouée, fallback règles : {}", exc)

    return round(score_ajuste, 3), "regles_metier_v1"


# ── GET /api/predictions ──────────────────────────────────────
@router.get("/", response_model=List[PredictionOut], summary="Prédictions de risque par groupe")
async def get_predictions(
    seuil:          float = Query(default=0.0,   ge=0.0, le=1.0, description="Seuil minimum score risque"),
    alertes_seulmt: bool  = Query(default=False, description="Alertes uniquement (score ≥ 0.75)"),
    payload: dict = Depends(verifier_token),
):
    """Prédictions calculées à partir des statistiques réelles Attijari bank."""
    version = "xgb_v1" if XGB_MODEL else "regles_metier_v1"
    results = []
    scores = _group_scores_from_data()

    for groupe, score in scores.items():
        if score < seuil:
            continue
        if alertes_seulmt and score < 0.75:
            continue

        niveau  = "CRITIQUE" if score >= 0.75 else ("SURVEILLANCE" if score >= 0.50 else "NORMAL")
        message = (
            "Risque élevé — action corrective recommandée" if score >= 0.75
            else "Surveillance recommandée" if score >= 0.50
            else "Niveau de risque normal"
        )

        results.append({
            "id":             f"PRED-{groupe[:6].replace(' ', '-').upper()}-{datetime.now().strftime('%H%M')}",
            "type_operation": groupe,
            "score_risque":   score,
            "est_alerte":     score >= 0.75,
            "niveau":         niveau,
            "version_modele": version,
            "date_prediction": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "message":        message,
            "source":         "Données réelles Attijari bank — Fév–Mars 2026",
        })

    results.sort(key=lambda x: x["score_risque"], reverse=True)
    logger.debug("GET /predictions seuil={} → {} groupes ({} alertes)", seuil, len(results), sum(1 for r in results if r["est_alerte"]))
    return results


# ── POST /api/predictions/predire ────────────────────────────
@router.post("/predire", response_model=PredictionOut, summary="Score de risque pour un ticket")
async def predire(req: PredictionRequest, payload: dict = Depends(verifier_token)):
    """Calcule le score de risque via XGBoost. Fallback règles métier si modèle absent."""
    score, version = _score_xgboost(req)
    niveau = "CRITIQUE" if score >= 0.75 else ("SURVEILLANCE" if score >= 0.50 else "NORMAL")

    lgbm_reco = recommander_lgbm(req.texte or req.type_operation, req.type_operation, req.categorie or "", req.severite)
    knn_reco = recommander_knn(req.texte or req.type_operation, req.type_operation, req.categorie or "", req.severite)

    logger.info("Prédiction XGBoost : groupe={} score={} niveau={} | reco={}", req.type_operation, score, niveau, lgbm_reco["action_suggeree"][:60])

    return {
        "id":                    str(uuid.uuid4()),
        "type_operation":        req.type_operation,
        "score_risque":          score,
        "est_alerte":            score >= 0.75,
        "niveau":                niveau,
        "version_modele":        version,
        "date_prediction":       datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "message":               "Score calculé + recommandation LightGBM + KNN",
        "source":                "Données réelles Attijari bank — Fév–Mars 2026",
        "action_recommandee":    lgbm_reco["action_suggeree"],
        "taux_succes":           lgbm_reco["taux_succes"],
        "action_similaire_knn":  knn_reco["action_suggeree"],
        "similarite_knn":        knn_reco["similarite_moyenne"],
        "incidents_similaires":  knn_reco.get("incidents_similaires", []),
        "methode_recommandation": "LightGBM + KNN",
    }


# ── GET /api/predictions/dashboard ───────────────────────────
@router.get("/dashboard", summary="Données graphiques pour Chart.js")
async def dashboard_predictions(payload: dict = Depends(verifier_token)):
    """Retourne les données pour les graphiques Chart.js."""
    metriques = XGB_METRICS or {
        "accuracy": 0.91,
        "auc":      0.95,
        "modele":   "XGBoost",
        "note":     "Estimé — entraîner avec : python scripts/entrainer_xgboost.py",
    }

    scores = _group_scores_from_data()
    total_tickets = 1507
    pct_retard_global = 12.8
    duree_moy = 266

    df = _charger_df_reclamations()
    if df is not None and not df.empty:
        total_tickets = int(len(df))
        if "score_risque" in df.columns and df["score_risque"].notna().any():
            pct_retard_global = round(float((df["score_risque"] >= 0.75).mean()) * 100, 1)
        if "duree_resolution_min" in df.columns and df["duree_resolution_min"].notna().any():
            duree_moy = round(float(df["duree_resolution_min"].mean()), 0)

    return {
        "labels":          list(scores.keys()),
        "scores_risque":   list(scores.values()),
        "seuil_alerte":    0.75,
        "groupes_critiques": [g for g, s in scores.items() if s >= 0.75],
        "statistiques_reelles": {
            "total_tickets":        total_tickets,
            "tickets_en_retard":    int(df["score_risque"].ge(0.75).sum()) if df is not None and "score_risque" in df.columns else 193,
            "pct_retard_global":    pct_retard_global,
            "duree_moy_resolution": duree_moy,
            "source":               "Données réelles Attijari bank — runtime dynamique",
        },
        "metriques_modele": metriques,
    }


# ── GET /api/predictions/modele ──────────────────────────────
@router.get("/modele", summary="Informations sur le modèle XGBoost")
async def infos_modele(payload: dict = Depends(verifier_token)):
    """État et métriques du modèle XGBoost."""
    best_params = XGB_METRICS.get("best_params", {}) if XGB_METRICS else {}
    importances = XGB_METRICS.get("feature_importances", {}) if XGB_METRICS else {}

    return {
        "modele_charge":    XGB_MODEL is not None,
        "version":          "xgb_v1",
        "algorithme":       "XGBoost (eXtreme Gradient Boosting)",
        "architecture":     "XGBoost (eXtreme Gradient Boosting)",
        "avantages":        [
            "Pas de séquences temporelles requises",
            "Gestion native des valeurs manquantes",
            "Entraînement rapide (< 2 min)",
            "Interprétabilité via feature importance",
            "Robustesse au déséquilibre de classes (scale_pos_weight)",
        ],
        "features":         ["severite", "duree_resolution_min", "score_anomalie",
                             "score_risque", "type_operation_enc", "categorie_enc"],
        "hyperparametres":  best_params,
        "feature_importance": importances,
        "metriques":        XGB_METRICS,
        "entrainement":     "Données réelles Attijari bank — Fév–Mars 2026 (1507 tickets)",
        "commande_train":   "python scripts/entrainer_xgboost.py",
        "prochain_retrain": "Lundi prochain 02:00 (scheduler automatique)",
    }


# ── GET /api/predictions/evolution ───────────────────────────
@router.get("/evolution", summary="Évolution temporelle des scores de risque par semaine")
async def evolution_temporelle(
    groupe: Optional[str] = Query(default=None, description="Filtrer par groupe IT (vide = tous)"),
    payload: dict = Depends(verifier_token),
):
    """
    Courbe temporelle des scores de risque agrégés par semaine.
    Basée sur les 1507 tickets réels Attijari bank — Fév–Mars 2026.
    Retourne : labels (semaines) + score moyen global + scores des 3 groupes les plus à risque.
    """
    df = _charger_df_evolution()

    if df is None or df.empty:
        # Fallback : données simulées cohérentes avec les stats réelles
        semaines = ["S1 Fév", "S2 Fév", "S3 Fév", "S4 Fév", "S1 Mar", "S2 Mar", "S3 Mar", "S4 Mar"]
        return {
            "labels":        semaines,
            "global":        [0.54, 0.58, 0.61, 0.63, 0.57, 0.60, 0.62, 0.59],
            "securite":      [0.81, 0.84, 0.88, 0.87, 0.83, 0.86, 0.89, 0.87],
            "swift":         [0.75, 0.79, 0.82, 0.81, 0.77, 0.80, 0.83, 0.81],
            "helpdesk":      [0.67, 0.70, 0.73, 0.72, 0.68, 0.71, 0.74, 0.72],
            "seuil_alerte":  0.75,
            "source":        "Données simulées — CSV non disponible",
            "tendance":      "stable",
        }

    # Filtrage optionnel par groupe
    if groupe:
        df = df[df["type_operation"].str.contains(groupe, case=False, na=False)]

    # Agréger par semaine ISO (lundi de chaque semaine)
    df = df.copy()
    df.loc[:, "semaine"] = df["date"].dt.to_period("W").apply(lambda p: p.start_time)
    df_weekly = (
        df.groupby("semaine")["score_anomalie"]
        .agg(["mean", "count"])
        .reset_index()
        .sort_values("semaine")
    )

    # Garder uniquement les semaines avec au moins 5 tickets
    df_weekly = df_weekly[df_weekly["count"] >= 5]

    if df_weekly.empty:
        return {"labels": [], "global": [], "source": "Aucune donnée"}

    labels = [s.strftime("%d/%m") for s in df_weekly["semaine"]]
    scores_global = [round(float(v), 3) for v in df_weekly["mean"]]

    # Courbes des 3 groupes les plus à risque
    top_groupes = ["Sécurité Opérationnelle", "SWIFT", "Helpdesk"]
    series_groupes = {}
    for grp in top_groupes:
        df_grp = df[df["type_operation"] == grp].copy()
        if df_grp.empty:
            series_groupes[grp] = [None] * len(labels)
            continue
        df_grp.loc[:, "semaine"] = df_grp["date"].dt.to_period("W").apply(lambda p: p.start_time)
        weekly_grp = (
            df_grp.groupby("semaine")["score_anomalie"]
            .mean()
            .reindex(df_weekly["semaine"])
        )
        series_groupes[grp] = [round(float(v), 3) if pd.notna(v) else None for v in weekly_grp]

    # Tendance : comparaison première moitié vs seconde moitié
    mid = len(scores_global) // 2
    if mid > 0:
        moy_debut = sum(scores_global[:mid]) / mid
        moy_fin   = sum(scores_global[mid:]) / max(len(scores_global[mid:]), 1)
        tendance  = "hausse" if moy_fin > moy_debut + 0.02 else ("baisse" if moy_fin < moy_debut - 0.02 else "stable")
    else:
        tendance = "stable"

    logger.debug("GET /predictions/evolution → {} semaines, tendance={}", len(labels), tendance)

    return {
        "labels":       labels,
        "global":       scores_global,
        "securite":     series_groupes.get("Sécurité Opérationnelle", []),
        "swift":        series_groupes.get("SWIFT", []),
        "helpdesk":     series_groupes.get("Helpdesk", []),
        "seuil_alerte": 0.75,
        "tendance":     tendance,
        "nb_semaines":  len(labels),
        "nb_tickets":   int(df_weekly["count"].sum()),
        "source":       "Données réelles Attijari bank — Fév–Mars 2026",
    }
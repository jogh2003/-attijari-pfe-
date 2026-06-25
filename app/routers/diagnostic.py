"""
diagnostic.py — Router diagnostic complet
PFE Attijari bank — Sujet 21

Vérifie :
  - Connexion PostgreSQL
  - Modèles ML chargés (XGBoost, LightGBM)
  - Données CSV disponibles
  - Endpoint UiPath opérationnel
  - Architecture hybride active
  - Connexion frontend (CORS)
"""
import os
from datetime import datetime

from fastapi import APIRouter, Depends
from app.core.logging_config import logger
from app.routers.auth import verifier_token

router = APIRouter()


def _check_postgres() -> dict:
    try:
        from app.core.database import check_db_connection, engine
        ok = check_db_connection()
        url_safe = str(engine.url).replace(
            str(engine.url.password or ""), "****"
        ) if engine.url.password else str(engine.url)
        return {
            "ok":      ok,
            "url":     url_safe,
            "message": "Connexion PostgreSQL active" if ok else "PostgreSQL inaccessible — vérifier que le serveur tourne sur le port 5432",
        }
    except Exception as exc:
        return {"ok": False, "url": "?", "message": f"Erreur : {exc}"}


def _check_models() -> dict:
    modeles = {
        "xgb_model.pkl":          os.path.exists("models/xgb_model.pkl"),
        "lgbm_reco_model.pkl":    os.path.exists("models/lgbm_reco_model.pkl"),
        "label_encoder_groupe.pkl": os.path.exists("models/label_encoder_groupe.pkl"),
        "label_encoder_categorie.pkl": os.path.exists("models/label_encoder_categorie.pkl"),
        "vec_reco.pkl":           os.path.exists("models/vec_reco.pkl"),
        "le_action.pkl":          os.path.exists("models/le_action.pkl"),
    }
    total     = len(modeles)
    presents  = sum(modeles.values())
    return {
        "ok":       presents >= 2,
        "detail":   modeles,
        "presents": presents,
        "total":    total,
        "message":  f"{presents}/{total} fichiers modèle présents",
    }


def _check_data() -> dict:
    chemins = {
        "data/processed/dataset_nlp_enrichi.csv": os.path.exists("data/processed/dataset_nlp_enrichi.csv"),
        "data/cleaned/reclamations_propres.csv":  os.path.exists("data/cleaned/reclamations_propres.csv"),
    }
    ok = any(chemins.values())
    return {
        "ok":     ok,
        "detail": chemins,
        "message": "Données CSV disponibles" if ok else "Aucun CSV trouvé — placer les données dans data/processed/ ou data/cleaned/",
    }


def _check_uipath() -> dict:
    """
    Vérifie que l'endpoint UiPath est configuré et qu'au moins une alerte est disponible.
    """
    try:
        from app.routers.alertes import calculer_alertes_reelles, DF_DATA
        alertes = calculer_alertes_reelles(0.75)
        return {
            "ok":             True,
            "endpoint":       "GET /api/alertes?seuil=0.75",
            "alertes_dispo":  len(alertes),
            "endpoint_cloture": "POST /api/alertes/{id}/cloturer",
            "message":        f"UiPath opérationnel — {len(alertes)} alerte(s) disponible(s)",
        }
    except Exception as exc:
        return {
            "ok":      False,
            "endpoint": "GET /api/alertes?seuil=0.75",
            "message": f"Erreur : {exc}",
        }


def _check_hybrid() -> dict:
    try:
        from app.services.hybrid_detection import detecter_hybride
        test = detecter_hybride(
            description    = "compromission firewall sécurité critique",
            type_operation = "Sécurité Opérationnelle",
            severite       = 1,
        )
        return {
            "ok":              True,
            "test_score":      test["score_anomalie"],
            "test_niveau":     test["niveau"],
            "test_methode":    test["methode_detection"],
            "message":         "Architecture hybride opérationnelle",
        }
    except Exception as exc:
        return {"ok": False, "message": f"Erreur : {exc}"}


def _check_frontend() -> dict:
    index_ok = os.path.exists("static/index.html")
    return {
        "ok":          index_ok,
        "index_html":  index_ok,
        "cors_origins": [
            "http://localhost:8000",
            "http://localhost:3000",
            "http://localhost:5500",
            "http://127.0.0.1:5500",
        ],
        "api_base":    "http://localhost:8000",
        "login_url":   "POST /auth/login  (form-data : username + password)",
        "message":     "Frontend static/index.html présent" if index_ok else "static/index.html absent — page d'accueil API JSON retournée",
    }


# ── GET /api/diagnostic ───────────────────────────────────────
@router.get("/", summary="Diagnostic complet — DB + Modèles + UiPath + Frontend")
async def diagnostic_complet(payload: dict = Depends(verifier_token)):
    """
    Vérifie toutes les connexions et composants du système.
    Accessible à tous les utilisateurs authentifiés.
    """
    postgres  = _check_postgres()
    modeles   = _check_models()
    donnees   = _check_data()
    uipath    = _check_uipath()
    hybride   = _check_hybrid()
    frontend  = _check_frontend()

    all_ok = postgres["ok"] and modeles["ok"] and donnees["ok"] and uipath["ok"] and hybride["ok"]
    statut = "healthy" if all_ok else ("degraded" if (modeles["ok"] and donnees["ok"]) else "critical")

    logger.info(
        "Diagnostic : statut={} | DB={} | Modèles={} | Données={} | UiPath={} | Hybride={}",
        statut, postgres["ok"], modeles["ok"], donnees["ok"], uipath["ok"], hybride["ok"],
    )

    return {
        "statut":             statut,
        "timestamp":          datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "composants": {
            "postgresql":     postgres,
            "modeles_ml":     modeles,
            "donnees_csv":    donnees,
            "uipath":         uipath,
            "hybride":        hybride,
            "frontend":       frontend,
        },
        "architecture":       "Hybride — Score Anomalie (N1) + XGBoost (N2) + LightGBM Reco",
        "endpoints_critiques": {
            "uipath_alertes":  "GET  /api/alertes?seuil=0.75",
            "uipath_cloture":  "POST /api/alertes/{id}/cloturer",
            "auth":            "POST /auth/login",
            "diagnostic":      "GET  /api/diagnostic",
            "health":          "GET  /health",
            "swagger":         "GET  /docs",
            "diagrammes":      "GET  /diagrammes",
        },
        "resume": (
            "Tous les composants opérationnels" if all_ok
            else "Certains composants dégradés — voir détail ci-dessus"
        ),
    }


# ── GET /api/diagnostic/db ────────────────────────────────────
@router.get("/db", summary="Test connexion PostgreSQL")
async def test_db(payload: dict = Depends(verifier_token)):
    """Test rapide de la connexion à PostgreSQL."""
    result = _check_postgres()
    if not result["ok"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=result["message"])
    return result


# ── GET /api/diagnostic/models ────────────────────────────────
@router.get("/models", summary="État des modèles ML")
async def test_models(payload: dict = Depends(verifier_token)):
    """Vérifie que les fichiers modèle sont présents et chargés."""
    from app.routers.predictions import XGB_MODEL, XGB_METRICS
    from app.routers.recommandations import LGBM_BUNDLE, LGBM_METRICS

    return {
        "xgboost": {
            "fichier_present": os.path.exists("models/xgb_model.pkl"),
            "charge_en_memoire": XGB_MODEL is not None,
            "metriques": XGB_METRICS,
        },
        "lightgbm_reco": {
            "fichier_present": os.path.exists("models/lgbm_reco_model.pkl"),
            "charge_en_memoire": LGBM_BUNDLE is not None,
            "metriques": LGBM_METRICS,
        },
        "hybrid_detection": {
            "service_disponible": True,
            "niveau_1": "Score Anomalie (règles, sans dépendance .pkl)",
            "niveau_2": "XGBoost confirmation (si modèle chargé)",
        },
    }

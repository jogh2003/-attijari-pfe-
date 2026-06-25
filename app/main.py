"""
main.py — Point d'entrée FastAPI — Version finale
PFE Attijari bank — Sujet 21

Lancer : uvicorn app.main:app --reload
Swagger : http://localhost:8000/docs
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.logging_config import logger, setup_logging
from app.routers.auth           import router as auth_router
from app.routers.reclamations   import router as reclamations_router
from app.routers.alertes        import router as alertes_router
from app.routers.predictions    import router as predictions_router
from app.routers.recommandations import router as recommandations_router
from app.routers.audit          import router as audit_router


def _seed_users() -> None:
    """Crée les utilisateurs par défaut en base PostgreSQL si la table est vide."""
    try:
        from app.core.database import SessionLocal
        from app.models.utilisateur import Utilisateur
        from passlib.context import CryptContext

        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        users_defaut = [
            {"id": "user-001", "nom": "Administrateur",  "email": "admin@attijaribank.tn",          "password": "Admin@2026!",  "role": "admin"},
            {"id": "user-002", "nom": "Responsable IT",  "email": "responsable.it@attijaribank.tn", "password": "Resp@2026!",   "role": "responsable_it"},
            {"id": "user-003", "nom": "Meriam",          "email": "meriam@attijaribank.tn",          "password": "Stage@2026!",  "role": "utilisateur"},
            {"id": "user-rpa", "nom": "Robot UiPath",    "email": "robot@attijaribank.tn",           "password": "Robot@2026!",  "role": "responsable_it"},
        ]

        db = SessionLocal()
        try:
            if db.query(Utilisateur).count() == 0:
                for u in users_defaut:
                    db.add(Utilisateur(
                        id=u["id"],
                        nom=u["nom"],
                        email=u["email"],
                        mot_de_passe=pwd_ctx.hash(u["password"]),
                        role=u["role"],
                        est_actif=True,
                    ))
                db.commit()
                logger.info("Utilisateurs initialisés en base ({} comptes)", len(users_defaut))
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Seed utilisateurs ignoré (DB indisponible) : {}", exc)


# ── Lifecycle (startup / shutdown) ────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialisation au démarrage, nettoyage à l'arrêt."""
    # ─ Startup ──────────────────────────────────────────
    debug = os.getenv("DEBUG", "false").lower() == "true"
    setup_logging(debug=debug)
    logger.info("═══ Démarrage API PFE Attijari bank v1.0.0 ═══")

    # Création automatique des tables PostgreSQL + seed utilisateurs
    try:
        from app.core.database import create_tables
        create_tables()
        logger.info("Tables PostgreSQL vérifiées / créées")
        _seed_users()
    except Exception as exc:
        logger.warning("PostgreSQL indisponible au démarrage : {}", exc)

    # Scheduler (réentraînement automatique chaque lundi)
    try:
        from app.core.scheduler import start_scheduler
        start_scheduler()
    except Exception as exc:
        logger.warning("Scheduler non démarré : {}", exc)

    logger.info("API prête — Swagger : http://localhost:8000/docs")
    logger.info("Endpoint UiPath : GET /api/alertes?seuil=0.75")

    # Vérifier présence modèles IA et entraîner si nécessaire
    try:
        auto_train = os.getenv("AUTO_TRAIN", "false").lower() == "true"
        models_needed = ["models/xgb_model.pkl", "models/lgbm_reco_model.pkl", "models/knn_model.pkl"]
        missing = [p for p in models_needed if not os.path.exists(p)]
        if missing:
            logger.warning("Modèles manquants : %s", ", ".join(missing))
            if auto_train:
                import subprocess, sys
                logger.info("AUTO_TRAIN activé — lancement du wrapper d'entraînement")
                try:
                    rc = subprocess.call([sys.executable, "scripts/train_all_models.py"])
                    if rc != 0:
                        logger.error("Entraînement automatique a échoué (code=%s)", rc)
                    else:
                        logger.info("Entraînement automatique terminé — modèles disponibles")
                except Exception as exc:
                    logger.error("Erreur lors de l'appel train_all_models : %s", exc)
            else:
                logger.info("Définir AUTO_TRAIN=true pour lancer l'entraînement automatique si nécessaire")
        else:
            logger.info("Tous les modèles IA sont présents")
    except Exception as exc:
        logger.warning("Vérification modèles IA échouée : %s", exc)

    yield  # L'application tourne ici

    # ─ Shutdown ─────────────────────────────────────────
    logger.info("Arrêt de l'API…")
    try:
        from app.core.scheduler import stop_scheduler
        stop_scheduler()
    except Exception:
        pass
    logger.info("API arrêtée proprement")


# ── Application FastAPI ───────────────────────────────────────
app = FastAPI(
    title="Systeme IA Attijari bank",
    description=(
        "API REST — Système de détection IA & RPA — Attijari bank\n\n"
        "**Données réelles** : 1507 tickets IT Février–Mars 2026\n\n"
        "**Authentification** : POST /auth/login avec form-data (username + password)\n\n"
        "**Endpoint UiPath** : GET /api/alertes?seuil=0.75\n\n"
        "**Réentraînement automatique** : chaque lundi à 02h00 (APScheduler)"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS pour le frontend HTML/JS du binôme ───────────────────
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://localhost:5500",
    "http://localhost:8000",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# ── Fichiers statiques (HTML/CSS/JS) ─────────────────────────
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Routers ───────────────────────────────────────────────────
app.include_router(auth_router,             prefix="/auth",                tags=["Authentification"])
app.include_router(reclamations_router,     prefix="/reclamations",        tags=["Analyse IA"])
app.include_router(alertes_router,          prefix="/api/alertes",         tags=["RPA — UiPath"])
app.include_router(predictions_router,      prefix="/api/predictions",     tags=["Prédictions LSTM"])
app.include_router(recommandations_router,  prefix="/api/recommandations", tags=["Recommandations KNN"])
app.include_router(audit_router,            prefix="/api/audit",           tags=["Audit Trail"])


# ── Endpoints de base ─────────────────────────────────────────
@app.get("/", tags=["Système"])
async def root(request: Request):
    """Serve the frontend dashboard at the root URL when available."""
    index_path = "static/index.html"
    if os.path.exists(index_path):
        accept_header = request.headers.get("accept", "")
        user_agent = request.headers.get("user-agent", "").lower()
        if "application/json" in accept_header or "python" in user_agent or "httpx" in user_agent:
            return {
                "message":   "API PFE Attijari bank — Système IA & RPA",
                "version":   "1.0.0",
                "docs":      "http://localhost:8000/docs",
                "uipath":    "GET /api/alertes?seuil=0.75 — endpoint UiPath CheckAlerte",
                "scheduler": "Réentraînement LSTM + KNN : chaque lundi 02h00",
                "statut":    "operationnel",
            }
        if "text/html" in accept_header:
            return FileResponse(index_path, media_type="text/html")
        return {
            "message":   "API PFE Attijari bank — Système IA & RPA",
            "version":   "1.0.0",
            "docs":      "http://localhost:8000/docs",
            "uipath":    "GET /api/alertes?seuil=0.75 — endpoint UiPath CheckAlerte",
            "scheduler": "Réentraînement LSTM + KNN : chaque lundi 02h00",
            "statut":    "operationnel",
        }
    return {
        "message":   "API PFE Attijari bank — Système IA & RPA",
        "version":   "1.0.0",
        "docs":      "http://localhost:8000/docs",
        "uipath":    "GET /api/alertes?seuil=0.75 — endpoint UiPath CheckAlerte",
        "scheduler": "Réentraînement LSTM + KNN : chaque lundi 02h00",
        "statut":    "operationnel",
    }


@app.get("/health", tags=["Système"])
async def health():
    """Endpoint de santé — appelé par UiPath pour vérifier que l'API tourne."""
    from app.core.database import check_db_connection
    from app.routers.predictions import XGB_MODEL
    from app.routers.recommandations import LGBM_BUNDLE, KNN_BUNDLE

    db_ok   = check_db_connection()
    xgb_ok  = XGB_MODEL is not None or os.path.exists("models/xgb_model.pkl")
    lgbm_ok = LGBM_BUNDLE is not None or os.path.exists("models/lgbm_reco_model.pkl")
    knn_ok  = KNN_BUNDLE is not None or os.path.exists("models/knn_model.pkl")
    # Vérifier les deux chemins possibles pour les données
    data_ok = (
        os.path.exists("data/processed/dataset_nlp_enrichi.csv") or
        os.path.exists("data/cleaned/reclamations_propres.csv")
    )

    overall = "healthy" if xgb_ok and lgbm_ok and knn_ok and data_ok else "degraded"

    return {
        "status":      overall,
        "db_ok":       db_ok,
        "xgb_charge":  xgb_ok,
        "lgbm_charge": lgbm_ok,
        "knn_charge":  knn_ok,
        "donnees_ok":  data_ok,
    }


@app.get("/favicon.ico", tags=["Système"], include_in_schema=False)
async def favicon():
    """Favicon pour éviter l'erreur 404 dans les logs du navigateur."""
    from fastapi.responses import FileResponse
    favicon_path = "static/favicon.ico"
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/x-icon")
    return {"status": 204}  # No Content

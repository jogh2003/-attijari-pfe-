"""
main.py — Point d'entrée FastAPI — Version finale
PFE Attijari bank — Sujet 21

Lancer : uvicorn app.main:app --reload
Swagger : http://localhost:8000/docs
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    "http://127.0.0.1:5500",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# ── Routers ───────────────────────────────────────────────────
app.include_router(auth_router,             prefix="/auth",                tags=["Authentification"])
app.include_router(reclamations_router,     prefix="/reclamations",        tags=["Analyse IA"])
app.include_router(alertes_router,          prefix="/api/alertes",         tags=["RPA — UiPath"])
app.include_router(predictions_router,      prefix="/api/predictions",     tags=["Prédictions LSTM"])
app.include_router(recommandations_router,  prefix="/api/recommandations", tags=["Recommandations KNN"])
app.include_router(audit_router,            prefix="/api/audit",           tags=["Audit Trail"])


# ── Endpoints de base ─────────────────────────────────────────
@app.get("/", tags=["Système"])
async def root():
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

    db_ok   = check_db_connection()
    knn_ok  = os.path.exists("models/knn_model.pkl")
    lstm_ok = os.path.exists("models/lstm_model.h5")
    # Vérifier les deux chemins possibles pour les données
    data_ok = (
        os.path.exists("data/processed/dataset_nlp_enrichi.csv") or
        os.path.exists("data/cleaned/reclamations_propres.csv")
    )

    overall = "healthy" if (knn_ok or lstm_ok) and data_ok else "degraded"

    return {
        "status":      overall,
        "db_ok":       db_ok,
        "knn_charge":  knn_ok,
        "lstm_charge": lstm_ok,
        "donnees_ok":  data_ok,
    }

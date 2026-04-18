"""
database.py — Connexion PostgreSQL avec SQLAlchemy
PFE Attijari bank — Sujet 21
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

load_dotenv()

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/attijari_pfe"
)

# ── Engine avec pool de connexions ────────────────────────────
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,           # connexions permanentes
    max_overflow=20,        # connexions supplémentaires temporaires
    pool_timeout=30,        # secondes avant timeout d'obtention
    pool_recycle=1800,      # recycler les connexions toutes les 30 min
    pool_pre_ping=True,     # vérifier la connexion avant utilisation
    echo=False,             # mettre True pour déboguer les requêtes SQL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dépendance FastAPI — injectée dans les endpoints qui utilisent la DB."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    """
    Crée toutes les tables ORM si elles n'existent pas encore.
    Appelé au démarrage de l'application.
    """
    try:
        # Importer les modèles pour que Base.metadata les connaisse
        from app.models import utilisateur, reclamation, audit_log  # noqa: F401
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        # Ne pas bloquer le démarrage si PostgreSQL est indisponible
        from app.core.logging_config import logger
        logger.warning("PostgreSQL indisponible au démarrage — tables non créées : {}", exc)


def check_db_connection() -> bool:
    """Vérifie que la connexion PostgreSQL est active."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

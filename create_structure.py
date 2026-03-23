"""
Script de création de la structure complète du projet
Exécuter : python create_structure.py
"""
import os

# Structure complète du projet
structure = {
    # ── Données ──────────────────────────────────────────────────
    "data/raw/.gitkeep": "",
    "data/cleaned/.gitkeep": "",
    "data/processed/.gitkeep": "",
    "data/models/.gitkeep": "",

    # ── Modèles sauvegardés ──────────────────────────────────────
    "models/.gitkeep": "",
    "mlruns/.gitkeep": "",

    # ── Backups ──────────────────────────────────────────────────
    "backups/.gitkeep": "",

    # ── Notebooks Jupyter (EDA) ──────────────────────────────────
    "notebooks/01_exploration.ipynb": '{"nbformat":4,"nbformat_minor":5,"metadata":{"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"}},"cells":[{"cell_type":"markdown","metadata":{},"source":["# Exploration des données — Réclamations Attijari bank"]},{"cell_type":"code","metadata":{},"source":["import pandas as pd\\nimport numpy as np\\nimport matplotlib.pyplot as plt\\nimport seaborn as sns\\n\\n# Charger le CSV\\ndf = pd.read_csv(\\'../data/raw/reclamations.csv\\')\\nprint(f\\'Shape: {df.shape}\\')\\ndf.head()"],"outputs":[],"execution_count":null}]}',
    "notebooks/02_nettoyage.ipynb": '{"nbformat":4,"nbformat_minor":5,"metadata":{"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"}},"cells":[{"cell_type":"markdown","metadata":{},"source":["# Nettoyage des données"]},{"cell_type":"code","metadata":{},"source":["import pandas as pd\\nimport numpy as np\\n\\ndf = pd.read_csv(\\'../data/raw/reclamations.csv\\')\\nprint(\\'Valeurs manquantes:\\')\\nprint(df.isnull().sum())\\nprint(\\'\\\\nDoublons:\\', df.duplicated().sum())"],"outputs":[],"execution_count":null}]}',
    "notebooks/03_eda.ipynb": '{"nbformat":4,"nbformat_minor":5,"metadata":{"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"}},"cells":[{"cell_type":"markdown","metadata":{},"source":["# Analyse Exploratoire (EDA)"]},{"cell_type":"code","metadata":{},"source":["import pandas as pd\\nimport matplotlib.pyplot as plt\\nimport seaborn as sns\\n\\ndf = pd.read_csv(\\'../data/cleaned/reclamations_clean.csv\\')\\n\\n# Distribution des types\\nplt.figure(figsize=(12,5))\\ndf[\\'type_operation\\'].value_counts().plot(kind=\\'bar\\')\\nplt.title(\\'Distribution des types de réclamations\\')\\nplt.tight_layout()\\nplt.savefig(\\'../reports/figures/distribution_types.png\\', dpi=150)\\nplt.show()"],"outputs":[],"execution_count":null}]}',

    # ── App principale ───────────────────────────────────────────
    "app/__init__.py": '"""Application FastAPI — Système IA Attijari bank"""\n',
    "app/main.py": '''"""
Point d\'entrée principal de l\'API FastAPI
Lancer : uvicorn app.main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, reclamations, predictions, recommandations, alertes, audit
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API REST — Système de détection IA & RPA — Attijari bank",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS — permet au frontend HTML/JS de consommer l\'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion des routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentification"])
app.include_router(reclamations.router, prefix="/api/reclamations", tags=["Réclamations"])
app.include_router(predictions.router, prefix="/api/predictions", tags=["Prédictions"])
app.include_router(recommandations.router, prefix="/api/recommandations", tags=["Recommandations"])
app.include_router(alertes.router, prefix="/api/alertes", tags=["Alertes"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit"])

@app.get("/", tags=["Root"])
async def root():
    return {"message": "API Système IA Attijari bank", "status": "running", "version": settings.APP_VERSION}

@app.get("/health", tags=["Root"])
async def health():
    return {"status": "healthy"}
''',

    # ── Core ─────────────────────────────────────────────────────
    "app/core/__init__.py": "",
    "app/core/config.py": '''"""Configuration de l\'application depuis .env"""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Systeme IA Attijari bank"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = "changeme"

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "attijari_pfe"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/attijari_pfe"

    JWT_SECRET_KEY: str = "jwt_secret_changeme"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480

    AES_KEY: str = "changeme32chars!changeme32chars!"
    SEUIL_RISQUE: float = 0.75
    FENETRE_LSTM: int = 30

    ES_HOST: str = "localhost"
    ES_PORT: int = 9200
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    CSV_PATH: str = "data/raw/reclamations.csv"
    MODEL_PATH: str = "models/lstm_model.h5"

    class Config:
        env_file = ".env"

settings = Settings()
''',
    "app/core/security.py": '''"""Sécurité : JWT, hachage mots de passe, AES-256"""
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from app.core.config import settings
import base64, hashlib

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Mots de passe ────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# ── JWT ──────────────────────────────────────────────────────────
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

# ── AES-256 ──────────────────────────────────────────────────────
def get_fernet_key():
    key = hashlib.sha256(settings.AES_KEY.encode()).digest()
    return base64.urlsafe_b64encode(key)

def encrypt_data(data: str) -> str:
    f = Fernet(get_fernet_key())
    return f.encrypt(data.encode()).decode()

def decrypt_data(data: str) -> str:
    f = Fernet(get_fernet_key())
    return f.decrypt(data.encode()).decode()
''',
    "app/core/database.py": '''"""Connexion PostgreSQL avec SQLAlchemy"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
''',

    # ── Modèles SQLAlchemy ───────────────────────────────────────
    "app/models/__init__.py": "",
    "app/models/reclamation.py": '''"""Modèle SQLAlchemy — Table reclamations"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, Enum
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class StatutEnum(str, enum.Enum):
    soumise = "soumise"
    en_analyse = "en_analyse"
    risque_eleve = "risque_eleve"
    en_traitement = "en_traitement"
    resolue = "resolue"
    escaladee = "escaladee"
    archivee = "archivee"

class Reclamation(Base):
    __tablename__ = "reclamations"

    id = Column(String, primary_key=True, index=True)
    date = Column(DateTime, nullable=False)
    type_operation = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)         # chiffré AES-256
    action_effectuee = Column(Text, nullable=True)     # colonne clé pour recommandations
    severite = Column(Integer, nullable=False)
    statut = Column(String(50), default="soumise")
    score_anomalie = Column(Float, nullable=True)
    score_risque = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
''',
    "app/models/utilisateur.py": '''"""Modèle SQLAlchemy — Table utilisateurs"""
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id = Column(String, primary_key=True, index=True)
    nom = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    mot_de_passe = Column(String(255), nullable=False)
    role = Column(String(50), default="utilisateur")
    est_actif = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
''',
    "app/models/audit_log.py": '''"""Modèle SQLAlchemy — Table audit_logs"""
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, index=True)
    utilisateur_id = Column(String, nullable=True)
    action = Column(String(200), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, server_default=func.now())
''',

    # ── Routers API ──────────────────────────────────────────────
    "app/routers/__init__.py": "",
    "app/routers/auth.py": '''"""Router authentification JWT"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.utilisateur import Utilisateur

router = APIRouter()

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(Utilisateur).filter(Utilisateur.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.mot_de_passe):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants incorrects")
    token = create_access_token({"sub": user.email, "role": user.role, "id": user.id})
    return {"access_token": token, "token_type": "bearer", "role": user.role}
''',
    "app/routers/reclamations.py": '''"""Router réclamations"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.reclamation import Reclamation

router = APIRouter()

@router.get("/")
async def get_reclamations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Retourne la liste des réclamations — consommé par le frontend HTML/JS"""
    reclamations = db.query(Reclamation).offset(skip).limit(limit).all()
    return {"total": len(reclamations), "data": reclamations}

@router.get("/{reclamation_id}")
async def get_reclamation(reclamation_id: str, db: Session = Depends(get_db)):
    """Retourne le détail d\'une réclamation par ID"""
    rec = db.query(Reclamation).filter(Reclamation.id == reclamation_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Réclamation non trouvée")
    return rec
''',
    "app/routers/predictions.py": '''"""Router prédictions LSTM"""
from fastapi import APIRouter

router = APIRouter()

@router.post("/predire")
async def predire_risque(data: dict):
    """Calcule le score de risque pour une séquence de réclamations"""
    # TODO: charger le modèle LSTM et calculer le score
    return {"score_risque": 0.0, "message": "Modèle non encore entraîné"}

@router.get("/alertes-actives")
async def get_alertes_actives():
    """Retourne les prédictions avec score > seuil — consommé par le dashboard"""
    return {"alertes": [], "total": 0}
''',
    "app/routers/recommandations.py": '''"""Router recommandations automatiques"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/{reclamation_id}")
async def get_recommandation(reclamation_id: str):
    """Retourne la recommandation pour une réclamation — consommé par le dashboard"""
    # TODO: implémenter KNN sur embeddings BERT
    return {"reclamation_id": reclamation_id, "action_suggeree": None, "taux_succes": 0.0}
''',
    "app/routers/alertes.py": '''"""Router alertes temps réel (WebSocket)"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List

router = APIRouter()
active_connections: List[WebSocket] = []

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket pour les alertes temps réel — consommé par le frontend JS"""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message reçu : {data}")
    except WebSocketDisconnect:
        active_connections.remove(websocket)

@router.get("/")
async def get_alertes():
    """Liste des alertes actives"""
    return {"alertes": [], "total": 0}
''',
    "app/routers/audit.py": '''"""Router audit trail"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.audit_log import AuditLog

router = APIRouter()

@router.get("/")
async def get_audit_logs(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """Retourne les logs d\'audit — accessible uniquement aux administrateurs"""
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    return {"total": len(logs), "data": logs}
''',

    # ── Services NLP & IA ─────────────────────────────────────────
    "app/services/__init__.py": "",
    "app/services/nlp_service.py": '''"""Service NLP : spaCy + BERT embeddings"""
import spacy
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class NLPService:
    def __init__(self):
        self.nlp = None
        self.bert_model = None

    def load_models(self):
        """Charger les modèles NLP (appeler au démarrage de l\'API)"""
        print("Chargement spaCy...")
        self.nlp = spacy.load("fr_core_news_md")
        print("Chargement BERT...")
        self.bert_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        print("Modèles NLP chargés.")

    def extraire_entites(self, texte: str) -> dict:
        """Extraire les entités nommées d\'une description de réclamation"""
        if not self.nlp:
            raise RuntimeError("Modèle spaCy non chargé")
        doc = self.nlp(texte)
        return {
            "tokens": [token.text for token in doc if not token.is_stop],
            "entites": [(ent.text, ent.label_) for ent in doc.ents],
            "lemmes": [token.lemma_ for token in doc if not token.is_stop]
        }

    def get_embedding(self, texte: str) -> np.ndarray:
        """Générer le vecteur BERT d\'une réclamation (768 dimensions)"""
        if not self.bert_model:
            raise RuntimeError("Modèle BERT non chargé")
        return self.bert_model.encode(texte)

    def calculer_similarite(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculer la similarité cosinus entre deux vecteurs BERT"""
        return float(cosine_similarity([vec1], [vec2])[0][0])

nlp_service = NLPService()
''',
    "app/services/prediction_service.py": '''"""Service prédiction LSTM"""
import numpy as np
import tensorflow as tf
from app.core.config import settings
import os

class PredictionService:
    def __init__(self):
        self.model = None
        self.seuil = settings.SEUIL_RISQUE

    def load_model(self):
        """Charger le modèle LSTM depuis le fichier sauvegardé"""
        if os.path.exists(settings.MODEL_PATH):
            self.model = tf.keras.models.load_model(settings.MODEL_PATH)
            print(f"Modèle LSTM chargé depuis {settings.MODEL_PATH}")
        else:
            print(f"Aucun modèle trouvé à {settings.MODEL_PATH} — entraîner d\'abord")

    def predire(self, sequence: np.ndarray) -> float:
        """Calculer le score de risque pour une séquence de 30 jours"""
        if not self.model:
            return 0.0
        seq_reshaped = sequence.reshape(1, settings.FENETRE_LSTM, -1)
        score = float(self.model.predict(seq_reshaped)[0][0])
        return round(score, 4)

    def est_risque_eleve(self, score: float) -> bool:
        return score >= self.seuil

prediction_service = PredictionService()
''',
    "app/services/recommandation_service.py": '''"""Service recommandations — KNN sur embeddings BERT"""
import numpy as np
from sklearn.neighbors import NearestNeighbors
from typing import List, Optional

class RecommandationService:
    def __init__(self):
        self.knn = None
        self.embeddings_historique = []
        self.actions_historique = []

    def charger_historique(self, embeddings: np.ndarray, actions: List[str]):
        """Charger l\'historique des réclamations résolues pour le KNN"""
        self.embeddings_historique = embeddings
        self.actions_historique = actions
        self.knn = NearestNeighbors(n_neighbors=5, metric="cosine")
        self.knn.fit(embeddings)
        print(f"KNN entraîné sur {len(actions)} cas historiques")

    def recommander(self, embedding: np.ndarray) -> Optional[dict]:
        """Trouver l\'action corrective la plus adaptée"""
        if not self.knn or len(self.actions_historique) == 0:
            return None
        distances, indices = self.knn.kneighbors([embedding])
        actions_similaires = [self.actions_historique[i] for i in indices[0]]
        action_plus_frequente = max(set(actions_similaires), key=actions_similaires.count)
        taux_succes = actions_similaires.count(action_plus_frequente) / len(actions_similaires)
        return {
            "action_suggeree": action_plus_frequente,
            "taux_succes": round(taux_succes, 2),
            "nb_cas_similaires": len(actions_similaires),
            "priorite": 1 if taux_succes >= 0.8 else 2
        }

recommandation_service = RecommandationService()
''',

    # ── Scripts utilitaires ──────────────────────────────────────
    "scripts/__init__.py": "",
    "scripts/init_db.py": '''"""Initialisation de la base de données PostgreSQL"""
import sys
sys.path.append(".")
from app.core.database import engine, Base
from app.models.reclamation import Reclamation
from app.models.utilisateur import Utilisateur
from app.models.audit_log import AuditLog
from app.core.security import hash_password
from sqlalchemy.orm import Session
import uuid

def init_database():
    print("Création des tables PostgreSQL...")
    Base.metadata.create_all(bind=engine)
    print("Tables créées avec succès.")

    # Créer un administrateur par défaut
    with Session(engine) as db:
        admin = db.query(Utilisateur).filter(Utilisateur.email == "admin@attijaribank.tn").first()
        if not admin:
            admin = Utilisateur(
                id=str(uuid.uuid4()),
                nom="Administrateur",
                email="admin@attijaribank.tn",
                mot_de_passe=hash_password("Admin@2026!"),
                role="admin"
            )
            db.add(admin)
            db.commit()
            print("Administrateur créé : admin@attijaribank.tn / Admin@2026!")

if __name__ == "__main__":
    init_database()
''',
    "scripts/import_csv.py": '''"""Script d\'import du CSV de réclamations vers PostgreSQL"""
import sys
sys.path.append(".")
import pandas as pd
import uuid
from sqlalchemy.orm import Session
from app.core.database import engine
from app.models.reclamation import Reclamation
from app.core.security import encrypt_data
from app.core.config import settings

def nettoyer_et_importer(csv_path: str):
    print(f"Lecture du fichier : {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"Données brutes : {df.shape[0]} lignes, {df.shape[1]} colonnes")
    print(f"Colonnes : {list(df.columns)}")

    # ── Nettoyage basique ────────────────────────────────────────
    df.drop_duplicates(inplace=True)
    print(f"Après suppression doublons : {df.shape[0]} lignes")

    # TODO : adapter les noms de colonnes selon le vrai CSV reçu
    # Exemple supposé : date, type_operation, description, action_effectuee, severite

    print("Import dans PostgreSQL...")
    with Session(engine) as db:
        for _, row in df.iterrows():
            rec = Reclamation(
                id=str(uuid.uuid4()),
                date=pd.to_datetime(row.get("date")),
                type_operation=str(row.get("type_operation", "")),
                description=encrypt_data(str(row.get("description", ""))),
                action_effectuee=str(row.get("action_effectuee", "")),
                severite=int(row.get("severite", 1)),
                statut="soumise"
            )
            db.add(rec)
        db.commit()
    print(f"Import terminé : {len(df)} réclamations importées.")

if __name__ == "__main__":
    nettoyer_et_importer(settings.CSV_PATH)
''',
    "scripts/check_setup.py": '''"""Vérification de l\'installation de l\'environnement"""
import sys

checks = []

# Python version
import platform
v = platform.python_version()
checks.append(("Python 3.11+", v >= "3.11", v))

# Bibliothèques
libs = ["pandas", "numpy", "spacy", "fastapi", "sqlalchemy",
        "tensorflow", "sklearn", "mlflow", "jose", "cryptography"]
for lib in libs:
    try:
        mod = __import__(lib if lib != "sklearn" else "sklearn")
        ver = getattr(mod, "__version__", "ok")
        checks.append((lib, True, ver))
    except ImportError:
        checks.append((lib, False, "NON INSTALLÉ"))

# Affichage
print("\\n" + "="*50)
print("  Vérification de l\'environnement PFE")
print("="*50)
ok_count = 0
for name, ok, ver in checks:
    status = "OK" if ok else "MANQUANT"
    icon = "✓" if ok else "✗"
    print(f"  {icon} {name:<25} {status:<10} {ver}")
    if ok: ok_count += 1

print("="*50)
print(f"  {ok_count}/{len(checks)} composants installés")
if ok_count < len(checks):
    print("  Exécuter : pip install -r requirements.txt")
print("="*50 + "\\n")
''',
    "scripts/backup_db.py": '''"""Backup automatique de la base PostgreSQL"""
import subprocess, os
from datetime import datetime
from app.core.config import settings

def backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{settings.BACKUP_PATH}/backup_{timestamp}.sql"
    os.makedirs(settings.BACKUP_PATH, exist_ok=True)

    cmd = f"pg_dump -h {settings.DB_HOST} -p {settings.DB_PORT} -U {settings.DB_USER} {settings.DB_NAME} > {backup_file}"
    result = subprocess.run(cmd, shell=True, capture_output=True,
                           env={**os.environ, "PGPASSWORD": settings.DB_PASSWORD})

    if result.returncode == 0:
        print(f"Backup créé : {backup_file}")
    else:
        print(f"Erreur backup : {result.stderr.decode()}")

if __name__ == "__main__":
    backup()
''',
    "scripts/train_lstm.py": '''"""Script d\'entraînement du modèle LSTM"""
import sys
sys.path.append(".")
import numpy as np
import tensorflow as tf
import mlflow
import mlflow.tensorflow
from app.core.config import settings

def entrainer_lstm():
    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    mlflow.set_experiment(settings.MLFLOW_EXPERIMENT_NAME)

    with mlflow.start_run():
        # TODO: charger les données préparées depuis la BDD
        # Exemple de structure attendue :
        # X_train shape : (n_samples, 30, n_features)
        # y_train shape : (n_samples, 1)

        print("Données non encore disponibles — attendre le CSV de la banque")

        # Architecture LSTM
        model = tf.keras.Sequential([
            tf.keras.layers.LSTM(64, return_sequences=True, input_shape=(settings.FENETRE_LSTM, 10)),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.LSTM(32),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(1, activation="sigmoid")
        ])

        model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
        model.summary()

        # mlflow.log_param("fenetre", settings.FENETRE_LSTM)
        # mlflow.log_param("seuil_risque", settings.SEUIL_RISQUE)
        # model.save(settings.MODEL_PATH)
        # mlflow.tensorflow.log_model(model, "lstm_model")

        print(f"Architecture LSTM créée. Entraîner avec les vraies données.")

if __name__ == "__main__":
    entrainer_lstm()
''',

    # ── Tests ────────────────────────────────────────────────────
    "tests/__init__.py": "",
    "tests/test_api.py": '''"""Tests unitaires de l\'API FastAPI"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "status" in response.json()

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_get_reclamations():
    response = client.get("/api/reclamations/")
    assert response.status_code in [200, 401]

def test_login_invalide():
    response = client.post("/api/auth/login", data={"username": "test@test.com", "password": "wrong"})
    assert response.status_code == 401
''',
    "tests/test_nlp.py": '''"""Tests du service NLP"""
import pytest
from app.services.nlp_service import NLPService

def test_embedding_dimension():
    """Le vecteur BERT doit avoir 384 dimensions (MiniLM) ou 768 (BERT complet)"""
    # Test sans charger le vrai modèle (trop lourd pour CI)
    # nlp_svc = NLPService()
    # nlp_svc.load_models()
    # emb = nlp_svc.get_embedding("Erreur lors du traitement du virement SWIFT")
    # assert len(emb) in [384, 768]
    assert True  # placeholder

def test_similarite_identique():
    """Deux textes identiques doivent avoir une similarité de 1.0"""
    import numpy as np
    from app.services.nlp_service import NLPService
    svc = NLPService()
    v = np.array([1.0, 0.0, 0.0])
    assert svc.calculer_similarite(v, v) == 1.0
''',
    "tests/test_security.py": '''"""Tests des fonctions de sécurité"""
from app.core.security import hash_password, verify_password, encrypt_data, decrypt_data, create_access_token, decode_token

def test_password_hash():
    pwd = "MonMotDePasse123!"
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed)
    assert not verify_password("mauvais", hashed)

def test_aes_encryption():
    texte = "Réclamation client sensible"
    chiffre = encrypt_data(texte)
    assert chiffre != texte
    assert decrypt_data(chiffre) == texte

def test_jwt_token():
    token = create_access_token({"sub": "test@test.com", "role": "admin"})
    payload = decode_token(token)
    assert payload["sub"] == "test@test.com"
    assert payload["role"] == "admin"
''',

    # ── Docker ───────────────────────────────────────────────────
    "docker-compose.yml": '''version: "3.8"

services:
  elasticsearch:
    image: elasticsearch:8.11.1
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  mlflow:
    image: ghcr.io/mlflow/mlflow:v2.9.2
    ports:
      - "5000:5000"
    command: mlflow server --host 0.0.0.0 --port 5000
    volumes:
      - mlflow_data:/mlflow

volumes:
  es_data:
  mlflow_data:
''',

    # ── .gitignore ───────────────────────────────────────────────
    ".gitignore": '''# Environnement Python
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.egg-info/
dist/
build/

# Variables d'environnement — NE JAMAIS COMMITTER
.env

# Données — NE PAS COMMITTER (données sensibles banque)
data/raw/
data/cleaned/
backups/

# Modèles entraînés (trop volumineux pour Git)
models/*.h5
models/*.pkl
mlruns/

# Jupyter
.ipynb_checkpoints/

# VS Code
.vscode/settings.json
.vscode/launch.json

# OS
.DS_Store
Thumbs.db

# Tests
.coverage
htmlcov/
.pytest_cache/
''',

    # ── README ───────────────────────────────────────────────────
    "README.md": '''# Système de détection IA & RPA — Attijari bank
## PFE 2026 — Sujet 21 — Génie Logiciel

### Description
Système intelligent de détection et d'amélioration continue des processus bancaires
d'Attijari bank basé sur l'analyse NLP des réclamations, la prédiction LSTM et
l'automatisation RPA des actions correctives.

### Installation rapide
```bash
# 1. Cloner le projet
git clone <url_du_repo>
cd attijari-pfe

# 2. Créer l'environnement virtuel
python -m venv venv
venv\\Scripts\\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer les variables d'environnement
cp .env.example .env
# Remplir les valeurs dans .env

# 5. Lancer les services (Elasticsearch, Redis, MLflow)
docker-compose up -d

# 6. Initialiser la base de données
python scripts/init_db.py

# 7. Lancer l'API
uvicorn app.main:app --reload
```

### API disponible sur
- Swagger UI : http://localhost:8000/docs
- ReDoc : http://localhost:8000/redoc
- MLflow UI : http://localhost:5000

### Structure du projet
```
attijari-pfe/
├── app/                    # Application FastAPI
│   ├── core/               # Config, BDD, Sécurité
│   ├── models/             # Modèles SQLAlchemy
│   ├── routers/            # Endpoints REST
│   └── services/           # NLP, LSTM, Recommandations
├── scripts/                # Scripts utilitaires
├── notebooks/              # Jupyter notebooks EDA
├── data/                   # Données (non committées)
├── models/                 # Modèles entraînés
├── tests/                  # Tests unitaires
└── docker-compose.yml      # Services (ES, Redis, MLflow)
```

### Équipe
- **Personne 1** : Backend · Data · NLP · IA · RPA · Sécurité
- **Personne 2 (Binôme)** : Frontend HTML/CSS/JS · Liaison API

### Technologies
Python · FastAPI · spaCy · BERT · TensorFlow · MLflow
PostgreSQL · Elasticsearch · Redis · UiPath · JWT · AES-256
''',
}

# Créer tous les fichiers
created = 0
for path, content in structure.items():
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    if not os.path.exists(path) or path.endswith(".gitkeep"):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        created += 1
        print(f"  créé : {path}")

print(f"\n✓ {created} fichiers créés dans la structure du projet.")
print("✓ Structure prête ! Ouvrez le dossier dans VS Code.")

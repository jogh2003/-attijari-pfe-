"""
auth.py — Authentification JWT complète
PFE Attijari bank — Sujet 21
"""
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.logging_config import logger

load_dotenv()

# ── Configuration ─────────────────────────────────────────────
SECRET_KEY     = os.getenv("JWT_SECRET_KEY", "AttijariPFE2026SecretKeyTresLongueEtSecurisee!")
ALGORITHM      = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
router        = APIRouter()

# ── Blacklist des tokens révoqués (in-memory) ─────────────────
# En production : remplacer par Redis (clé : REDIS_HOST dans .env)
_TOKEN_BLACKLIST: set[str] = set()


# ── Utilisateurs par défaut (fallback si DB indisponible) ─────
_RAW_USERS = [
    {"id": "user-001", "nom": "Administrateur",  "email": "admin@attijaribank.tn",            "password": "Admin@2026!",  "role": "admin"},
    {"id": "user-002", "nom": "Responsable IT",  "email": "responsable.it@attijaribank.tn",   "password": "Resp@2026!",   "role": "responsable_it"},
    {"id": "user-003", "nom": "Meriam",          "email": "meriam@attijaribank.tn",            "password": "Stage@2026!",  "role": "utilisateur"},
    {"id": "user-rpa", "nom": "Robot UiPath",    "email": "robot@attijaribank.tn",             "password": "Robot@2026!",  "role": "responsable_it"},
]

USERS: dict[str, dict] = {
    u["email"]: {**u, "mot_de_passe": pwd_context.hash(u["password"])}
    for u in _RAW_USERS
}


# ── Schémas ────────────────────────────────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    nom: str


class UserInfo(BaseModel):
    id: str
    nom: str
    email: str
    role: str


# ── Helpers JWT ───────────────────────────────────────────────
def creer_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MINUTES)
    payload["jti"] = uuid.uuid4().hex  # ID unique — garantit que chaque login génère un token distinct
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decoder_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# ── Authentification — DB d'abord, fallback en mémoire ────────
def _auth_user(email: str, password: str) -> Optional[dict]:
    """Authentifie un utilisateur. Essaie PostgreSQL, puis dict en mémoire."""
    # Tentative via DB
    try:
        from app.core.database import SessionLocal
        from app.models.utilisateur import Utilisateur

        db = SessionLocal()
        try:
            user_db = db.query(Utilisateur).filter(
                Utilisateur.email == email,
                Utilisateur.est_actif == True,
            ).first()
            if user_db and pwd_context.verify(password, user_db.mot_de_passe):
                return {
                    "id":    user_db.id,
                    "nom":   user_db.nom,
                    "email": user_db.email,
                    "role":  user_db.role,
                }
        finally:
            db.close()
    except Exception:
        pass  # DB indisponible — fallback en mémoire

    # Fallback in-memory
    user = USERS.get(email)
    if user and pwd_context.verify(password, user["mot_de_passe"]):
        return {"id": user["id"], "nom": user["nom"], "email": user["email"], "role": user["role"]}

    return None


# ── Dépendances ───────────────────────────────────────────────
def verifier_token(token: str = Depends(oauth2_scheme)) -> dict:
    """Middleware JWT — protège tous les endpoints sécurisés."""
    # Vérifier si le token a été révoqué (logout)
    if token in _TOKEN_BLACKLIST:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token révoqué — veuillez vous reconnecter",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decoder_token(token)
        if not payload.get("sub"):
            raise HTTPException(status_code=401, detail="Token invalide")
        return payload
    except JWTError as exc:
        logger.warning("Token invalide ou expiré : {}", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expiré ou invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )


def admin_requis(payload: dict = Depends(verifier_token)) -> dict:
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès admin uniquement")
    return payload


def responsable_requis(payload: dict = Depends(verifier_token)) -> dict:
    if payload.get("role") not in ["admin", "responsable_it"]:
        raise HTTPException(status_code=403, detail="Accès responsable IT requis")
    return payload


# ── POST /auth/login ──────────────────────────────────────────
@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Connexion — obtenir un token JWT",
)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authentification pour les utilisateurs et le robot UiPath.

    **Comptes disponibles :**
    - admin@attijaribank.tn / Admin@2026!
    - responsable.it@attijaribank.tn / Resp@2026!
    - meriam@attijaribank.tn / Stage@2026!
    - robot@attijaribank.tn / Robot@2026! ← utilisé par UiPath
    """
    user = _auth_user(form_data.username, form_data.password)

    if not user:
        logger.warning("Tentative de connexion échouée pour : {}", form_data.username)
        raise HTTPException(status_code=401, detail="Identifiants incorrects")

    token = creer_token({
        "sub":  user["email"],
        "role": user["role"],
        "id":   user["id"],
        "nom":  user["nom"],
    })

    ip = request.client.host if request.client else "0.0.0.0"
    _audit_async(user["email"], user["role"], "LOGIN", f"Connexion réussie — rôle {user['role']}", ip)

    logger.info("Connexion réussie : {} ({})", user["email"], user["role"])

    return {
        "access_token": token,
        "token_type":   "bearer",
        "role":         user["role"],
        "nom":          user["nom"],
    }


# ── GET /auth/me ──────────────────────────────────────────────
@router.get("/me", response_model=UserInfo, summary="Infos utilisateur connecté")
async def get_me(payload: dict = Depends(verifier_token)):
    return {
        "id":    payload.get("id", ""),
        "nom":   payload.get("nom", ""),
        "email": payload.get("sub", ""),
        "role":  payload.get("role", ""),
    }


# ── POST /auth/logout ─────────────────────────────────────────
@router.post("/logout", summary="Déconnexion — invalide le token JWT côté serveur")
async def logout(
    request: Request,
    token: str = Depends(oauth2_scheme),
    payload: dict = Depends(verifier_token),
):
    """
    Révoque le token JWT côté serveur (blacklist in-memory).
    Toute requête ultérieure avec ce token retourne 401.
    """
    _TOKEN_BLACKLIST.add(token)

    email = payload.get("sub", "inconnu")
    ip    = request.client.host if request.client else "0.0.0.0"
    _audit_async(email, payload.get("role", ""), "LOGOUT", "Déconnexion — token révoqué", ip)
    logger.info("Déconnexion : {} — token révoqué", email)
    return {"message": f"Au revoir {payload.get('nom')} — token révoqué"}


# ── Audit non-bloquant ────────────────────────────────────────
def _audit_async(utilisateur: str, role: str, action: str, details: str, ip: str) -> None:
    """Enregistre une action d'audit sans bloquer le endpoint."""
    try:
        from app.core.audit import log_action
        log_action(utilisateur=utilisateur, role=role, action=action, details=details, ip=ip)
    except Exception as exc:
        logger.warning("Audit non enregistré : {}", exc)

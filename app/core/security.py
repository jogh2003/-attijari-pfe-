import os
import base64
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "7d9f8e2a1b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 480))
AES_KEY_STRING = os.getenv("AES_KEY", "attijari_pfe_2026_security_key_32")

# --- HACHAGE (bcrypt) ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# --- JWT TOKENS ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- CHIFFREMENT AES-256 (Données bancaires) ---
def get_fernet_key() -> bytes:
    key_hash = hashlib.sha256(AES_KEY_STRING.encode()).digest()
    return base64.urlsafe_b64encode(key_hash)

def encrypt_data(data: str) -> str:
    if not data: return ""
    f = Fernet(get_fernet_key())
    return f.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    if not encrypted_data: return ""
    try:
        f = Fernet(get_fernet_key())
        return f.decrypt(encrypted_data.encode()).decode()
    except Exception:
        return encrypted_data
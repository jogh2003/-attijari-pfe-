"""Securite : JWT, hachage mots de passe, AES-256"""
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
import base64, hashlib

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "jwt_secret_changeme"
ALGORITHM = "HS256"
AES_KEY = "changeme32chars!changeme32chars!"

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expire_minutes: int = 480) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

def get_fernet_key(key: str = AES_KEY):
    raw = hashlib.sha256(key.encode()).digest()
    return base64.urlsafe_b64encode(raw)

def encrypt_data(data: str) -> str:
    f = Fernet(get_fernet_key())
    return f.encrypt(data.encode()).decode()

def decrypt_data(data: str) -> str:
    f = Fernet(get_fernet_key())
    return f.decrypt(data.encode()).decode()

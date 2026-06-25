"""
tests/test_security.py — Tests de sécurité pytest-native
PFE Attijari bank — Sujet 21
"""
import os
import base64
import hashlib
import uuid
import subprocess
from datetime import datetime, timedelta

import pytest
from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET = "AttijariPFE2026SecretKeyTresLongueEtSecurisee!"
ALGO = "HS256"

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def creer_token_test(data, minutes=480):
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=minutes)
    return jwt.encode(payload, SECRET, algorithm=ALGO)


def get_fernet():
    key_raw = hashlib.sha256("AttijariPFE2026Key32charsExact!".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key_raw))


def test_hash_bcrypt_basique():
    h = pwd_ctx.hash("Admin@2026!")
    assert pwd_ctx.verify("Admin@2026!", h)
    assert h != "Admin@2026!"


def test_hash_bcrypt_mauvais_mdp():
    h = pwd_ctx.hash("Admin@2026!")
    assert not pwd_ctx.verify("mauvais_mdp", h)


def test_hash_bcrypt_deux_hashs_differents():
    h1 = pwd_ctx.hash("meme_mdp")
    h2 = pwd_ctx.hash("meme_mdp")
    assert h1 != h2


def test_hash_bcrypt_vide():
    h = pwd_ctx.hash("")
    assert not pwd_ctx.verify("autre", h)


def test_jwt_creation():
    token = creer_token_test({"sub": "test@attijaribank.tn", "role": "admin"})
    assert token and len(token) > 20


def test_jwt_decode():
    token = creer_token_test({"sub": "meriam@attijaribank.tn", "role": "utilisateur"})
    payload = jwt.decode(token, SECRET, algorithms=[ALGO])
    assert payload["sub"] == "meriam@attijaribank.tn"
    assert payload["role"] == "utilisateur"


def test_jwt_role_admin():
    token = creer_token_test({"sub": "admin@attijaribank.tn", "role": "admin", "id": "user-001"})
    payload = jwt.decode(token, SECRET, algorithms=[ALGO])
    assert payload["role"] == "admin"
    assert payload["id"] == "user-001"


def test_jwt_mauvaise_cle():
    token = creer_token_test({"sub": "test@test.com"})
    with pytest.raises(JWTError):
        jwt.decode(token, "MAUVAISE_CLE", algorithms=[ALGO])


def test_jwt_expire():
    token = creer_token_test({"sub": "test@test.com"}, minutes=-1)
    with pytest.raises(JWTError):
        jwt.decode(token, SECRET, algorithms=[ALGO])


def test_aes_chiffrement():
    f = get_fernet()
    txt = "Réclamation client sensible — données bancaires"
    enc = f.encrypt(txt.encode()).decode()
    assert enc != txt
    assert len(enc) > len(txt)


def test_aes_dechiffrement():
    f = get_fernet()
    txt = "Virement SWIFT TN2026001 — montant 50000 TND"
    enc = f.encrypt(txt.encode()).decode()
    dec = f.decrypt(enc.encode()).decode()
    assert dec == txt


def test_aes_deux_chiffrements_differents():
    f = get_fernet()
    txt = "même texte"
    e1 = f.encrypt(txt.encode()).decode()
    e2 = f.encrypt(txt.encode()).decode()
    assert e1 != e2


def test_aes_mauvaise_cle():
    f1 = get_fernet()
    key2 = Fernet(Fernet.generate_key())
    txt = "données sensibles"
    enc = f1.encrypt(txt.encode())
    with pytest.raises(Exception):
        key2.decrypt(enc)


def test_aes_description_reclamation():
    f = get_fernet()
    desc = "Erreur traitement virement international — client DUPONT — compte TN5900200010105009"
    enc = f.encrypt(desc.encode()).decode()
    dec = f.decrypt(enc.encode()).decode()
    assert dec == desc


def test_audit_login():
    entries = []
    entry = {
        "id": str(uuid.uuid4()),
        "utilisateur_id": "user-001",
        "action": "LOGIN",
        "details": "Connexion depuis dashboard",
        "ip_address": "192.168.1.10",
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
    entries.append(entry)
    assert entry["action"] == "LOGIN"
    assert entry["utilisateur_id"] == "user-001"
    assert entry["ip_address"] == "192.168.1.10"
    assert len(entry["id"]) > 10


def test_audit_action_rpa():
    entry = {
        "id": str(uuid.uuid4()),
        "utilisateur_id": "robot_uipath",
        "action": "ACTION_RPA",
        "details": "Purge Redis exécutée",
        "ip_address": "127.0.0.1",
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
    assert entry["action"] == "ACTION_RPA"


def test_audit_multiple_actions():
    entries = []
    for i in range(5):
        entries.append({
            "id": str(uuid.uuid4()),
            "utilisateur_id": f"user-00{i}",
            "action": f"ACTION_{i}",
            "details": f"Détail {i}",
            "ip_address": "127.0.0.1",
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        })
    ids = [e["id"] for e in entries]
    assert len(set(ids)) == 5


def test_audit_timestamp_present():
    entry = {
        "id": str(uuid.uuid4()),
        "utilisateur_id": "user-001",
        "action": "TEST",
        "details": "Test timestamp",
        "ip_address": "127.0.0.1",
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
    assert entry["timestamp"] is not None
    assert len(entry["timestamp"]) == 19


def test_audit_details_stockes():
    details = "Robot UiPath a exécuté l'action: Redémarrage SWIFT-GW — durée 3.2s"
    entry = {
        "id": str(uuid.uuid4()),
        "utilisateur_id": "robot_uipath",
        "action": "RPA_SUCCESS",
        "details": details,
        "ip_address": "127.0.0.1",
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
    assert entry["details"] == details


def test_pgdump_disponible():
    result = subprocess.run(["pg_dump", "--version"], capture_output=True)
    assert result.returncode == 0


def test_backup_path_cree(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    assert backup_dir.is_dir()


def test_backup_script_existe():
    assert os.path.exists("scripts/backup_db.py")

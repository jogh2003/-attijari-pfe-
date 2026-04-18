"""
test_security.py — Tests complets sécurité
PFE Attijari bank — Sujet 21

Exécuter : python tests/test_security.py
"""
import sys, os, base64, hashlib, uuid
from datetime import datetime

sys.path.insert(0, ".")

# Fix encodage Windows (cp1252 ne supporte pas les caractères Unicode étendus)
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ════════════════════════════════════════════════════════════
# COULEURS TERMINAL
# ════════════════════════════════════════════════════════════
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

resultats = []

def test(nom, fn):
    try:
        fn()
        resultats.append((nom, True, None))
        print(f"  {GREEN}✓{RESET} {nom}")
    except Exception as e:
        resultats.append((nom, False, str(e)))
        print(f"  {RED}✗{RESET} {nom}")
        print(f"    {RED}→ {e}{RESET}")

# ════════════════════════════════════════════════════════════
# 1. TESTS HACHAGE MOT DE PASSE (bcrypt)
# ════════════════════════════════════════════════════════════
print(f"\n{BOLD}{BLUE}═══ 1. Hachage mot de passe (bcrypt) ═══{RESET}")

from passlib.context import CryptContext
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def test_hash_basique():
    h = pwd_ctx.hash("Admin@2026!")
    assert pwd_ctx.verify("Admin@2026!", h), "Vérification bcrypt échouée"
    assert h != "Admin@2026!", "Hash identique au mot de passe — erreur !"

def test_hash_mauvais_mdp():
    h = pwd_ctx.hash("Admin@2026!")
    assert not pwd_ctx.verify("mauvais_mdp", h), "Mauvais mot de passe accepté !"

def test_deux_hash_differents():
    h1 = pwd_ctx.hash("meme_mdp")
    h2 = pwd_ctx.hash("meme_mdp")
    assert h1 != h2, "Deux hashs identiques pour le même mot de passe (pas de salt) !"

def test_hash_vide():
    h = pwd_ctx.hash("")
    assert not pwd_ctx.verify("autre", h)

test("Hash bcrypt basique",           test_hash_basique)
test("Rejet mauvais mot de passe",    test_hash_mauvais_mdp)
test("Deux hashs différents (salt)",  test_deux_hash_differents)
test("Hash chaîne vide",              test_hash_vide)

# ════════════════════════════════════════════════════════════
# 2. TESTS JWT
# ════════════════════════════════════════════════════════════
print(f"\n{BOLD}{BLUE}═══ 2. Tokens JWT ═══{RESET}")

from jose import jwt, JWTError
from datetime import timedelta

SECRET  = "AttijariPFE2026SecretKeyTresLongueEtSecurisee!"
ALGO    = "HS256"

def creer_token_test(data, minutes=480):
    from datetime import datetime
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=minutes)
    return jwt.encode(payload, SECRET, algorithm=ALGO)

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
    try:
        jwt.decode(token, "MAUVAISE_CLE", algorithms=[ALGO])
        raise AssertionError("Token accepté avec mauvaise clé !")
    except JWTError:
        pass  # Comportement attendu

def test_jwt_expire():
    token = creer_token_test({"sub": "test@test.com"}, minutes=-1)
    try:
        jwt.decode(token, SECRET, algorithms=[ALGO])
        raise AssertionError("Token expiré accepté !")
    except JWTError:
        pass  # Comportement attendu

test("Création token JWT",             test_jwt_creation)
test("Décodage et contenu JWT",        test_jwt_decode)
test("Role admin dans le token",       test_jwt_role_admin)
test("Rejet avec mauvaise clé",        test_jwt_mauvaise_cle)
test("Rejet token expiré",             test_jwt_expire)

# ════════════════════════════════════════════════════════════
# 3. TESTS CHIFFREMENT AES-256
# ════════════════════════════════════════════════════════════
print(f"\n{BOLD}{BLUE}═══ 3. Chiffrement AES-256 ═══{RESET}")

from cryptography.fernet import Fernet

def get_fernet():
    key_raw = hashlib.sha256("AttijariPFE2026Key32charsExact!".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key_raw))

def test_aes_chiffrement():
    f   = get_fernet()
    txt = "Réclamation client sensible — données bancaires"
    enc = f.encrypt(txt.encode()).decode()
    assert enc != txt
    assert len(enc) > len(txt)

def test_aes_dechiffrement():
    f   = get_fernet()
    txt = "Virement SWIFT TN2026001 — montant 50000 TND"
    enc = f.encrypt(txt.encode()).decode()
    dec = f.decrypt(enc.encode()).decode()
    assert dec == txt

def test_aes_deux_chiffrements_differents():
    f   = get_fernet()
    txt = "même texte"
    e1  = f.encrypt(txt.encode()).decode()
    e2  = f.encrypt(txt.encode()).decode()
    assert e1 != e2  # IV différent à chaque chiffrement

def test_aes_mauvaise_cle():
    f1  = get_fernet()
    key2 = Fernet(Fernet.generate_key())
    txt  = "données sensibles"
    enc  = f1.encrypt(txt.encode())
    try:
        key2.decrypt(enc)
        raise AssertionError("Déchiffrement accepté avec mauvaise clé !")
    except Exception:
        pass  # Comportement attendu

def test_aes_description_reclamation():
    f   = get_fernet()
    desc = "Erreur traitement virement international — client DUPONT — compte TN5900200010105009"
    enc  = f.encrypt(desc.encode()).decode()
    dec  = f.decrypt(enc.encode()).decode()
    assert dec == desc

test("Chiffrement produit texte différent",    test_aes_chiffrement)
test("Déchiffrement retourne texte original",  test_aes_dechiffrement)
test("Deux chiffrements différents (IV)",      test_aes_deux_chiffrements_differents)
test("Rejet avec mauvaise clé AES",            test_aes_mauvaise_cle)
test("Chiffrement description réclamation",    test_aes_description_reclamation)

# ════════════════════════════════════════════════════════════
# 4. TESTS AUDIT TRAIL
# ════════════════════════════════════════════════════════════
print(f"\n{BOLD}{BLUE}═══ 4. Audit Trail ═══{RESET}")

# Simulation de l'audit trail sans connexion BDD
audit_trail_test = []

def enregistrer_audit(utilisateur_id, action, details, ip="127.0.0.1"):
    """Simule l'enregistrement dans la table audit_logs"""
    entry = {
        "id":             str(uuid.uuid4()),
        "utilisateur_id": utilisateur_id,
        "action":         action,
        "details":        details,
        "ip_address":     ip,
        "timestamp":      datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    }
    audit_trail_test.append(entry)
    return entry

def test_audit_login():
    audit_trail_test.clear()
    entry = enregistrer_audit("user-001", "LOGIN", "Connexion depuis dashboard", "192.168.1.10")
    assert entry["action"] == "LOGIN"
    assert entry["utilisateur_id"] == "user-001"
    assert entry["ip_address"] == "192.168.1.10"
    assert len(entry["id"]) > 10

def test_audit_action_rpa():
    audit_trail_test.clear()
    enregistrer_audit("robot_uipath", "ACTION_RPA", "Purge Redis exécutée", "127.0.0.1")
    assert len(audit_trail_test) == 1
    assert audit_trail_test[0]["action"] == "ACTION_RPA"

def test_audit_multiple_actions():
    audit_trail_test.clear()
    for i in range(5):
        enregistrer_audit(f"user-00{i}", f"ACTION_{i}", f"Détail {i}")
    assert len(audit_trail_test) == 5
    ids = [e["id"] for e in audit_trail_test]
    assert len(set(ids)) == 5  # Tous les IDs sont uniques

def test_audit_timestamp_present():
    entry = enregistrer_audit("user-001", "TEST", "Test timestamp")
    assert entry["timestamp"] is not None
    assert len(entry["timestamp"]) == 19  # Format YYYY-MM-DDTHH:MM:SS

def test_audit_details_stockes():
    details = "Robot UiPath a exécuté l'action: Redémarrage SWIFT-GW — durée 3.2s"
    entry   = enregistrer_audit("robot_uipath", "RPA_SUCCESS", details)
    assert entry["details"] == details

test("Enregistrement action LOGIN",       test_audit_login)
test("Enregistrement action RPA",         test_audit_action_rpa)
test("5 actions avec IDs uniques",        test_audit_multiple_actions)
test("Timestamp présent et formaté",      test_audit_timestamp_present)
test("Détails stockés correctement",      test_audit_details_stockes)

# ════════════════════════════════════════════════════════════
# 5. TEST BACKUP pg_dump
# ════════════════════════════════════════════════════════════
print(f"\n{BOLD}{BLUE}═══ 5. Backup pg_dump ═══{RESET}")

import subprocess

def test_pgdump_disponible():
    result = subprocess.run(["pg_dump", "--version"], capture_output=True)
    assert result.returncode == 0, "pg_dump non trouvé — vérifier le PATH PostgreSQL"

def test_backup_path_cree():
    os.makedirs("backups", exist_ok=True)
    assert os.path.isdir("backups"), "Dossier backups non créé"

def test_backup_script_existe():
    assert os.path.exists("scripts/backup_db.py"), \
        "scripts/backup_db.py manquant — créer ce fichier"

test("pg_dump disponible dans le PATH",  test_pgdump_disponible)
test("Dossier backups/ créé",            test_backup_path_cree)
test("Script backup_db.py existe",       test_backup_script_existe)

# ════════════════════════════════════════════════════════════
# RÉSUMÉ FINAL
# ════════════════════════════════════════════════════════════
total  = len(resultats)
ok     = sum(1 for _, s, _ in resultats if s)
echecs = total - ok
pct    = round(ok / total * 100) if total > 0 else 0

print(f"\n{BOLD}{'═'*50}{RESET}")
print(f"{BOLD}  RÉSULTATS — Tests sécurité PFE Attijari bank{RESET}")
print(f"{'═'*50}")
print(f"  {GREEN}✓ Réussis  : {ok}{RESET}")
print(f"  {RED}✗ Échoués  : {echecs}{RESET}")
print(f"  Total      : {total}")
print(f"  Couverture : {pct}%")
print(f"{'═'*50}")

if echecs > 0:
    print(f"\n{YELLOW}Tests échoués :{RESET}")
    for nom, statut, err in resultats:
        if not statut:
            print(f"  {RED}✗{RESET} {nom}")
            print(f"    → {err}")

if pct == 100:
    print(f"\n{GREEN}{BOLD}  ✓ SÉCURITÉ 100% VALIDÉE — Prêt pour la soutenance !{RESET}")
elif pct >= 80:
    print(f"\n{YELLOW}{BOLD}  ~ Sécurité {pct}% — Corriger les tests échoués{RESET}")
else:
    print(f"\n{RED}{BOLD}  ✗ Sécurité {pct}% — Vérifier l'installation des bibliothèques{RESET}")
    print(f"  Exécuter : pip install passlib[bcrypt] python-jose cryptography")

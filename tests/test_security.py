"""Tests securite"""
import sys
sys.path.insert(0, ".")
from app.core.security import hash_password, verify_password, encrypt_data, decrypt_data, create_access_token, decode_token

def test_password():
    pwd = "MonMotDePasse123!"
    h = hash_password(pwd)
    assert verify_password(pwd, h)
    assert not verify_password("mauvais", h)

def test_aes():
    texte = "Reclamation client sensible"
    enc = encrypt_data(texte)
    assert enc != texte
    assert decrypt_data(enc) == texte

def test_jwt():
    token = create_access_token({"sub": "test@test.com", "role": "admin"})
    payload = decode_token(token)
    assert payload["sub"] == "test@test.com"

if __name__ == "__main__":
    test_password(); print("test_password OK")
    test_aes(); print("test_aes OK")
    test_jwt(); print("test_jwt OK")
    print("Tous les tests passes !")

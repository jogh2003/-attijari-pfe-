"""
conftest.py — Fixtures pytest communes
PFE Attijari bank — Sujet 21

Exécuter : pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


# ── Client HTTP de test ───────────────────────────────────────
@pytest.fixture(scope="session")
def client():
    """Client FastAPI TestClient — réutilisé sur toute la session de tests."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ── Token admin (session) ─────────────────────────────────────
@pytest.fixture(scope="session")
def auth_admin(client):
    """Headers avec token JWT admin — partagé sur toute la session."""
    response = client.post(
        "/auth/login",
        data={"username": "admin@attijaribank.tn", "password": "Admin@2026!"},
    )
    assert response.status_code == 200, f"Login admin échoué : {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Token admin frais (function) — pour les tests de logout ───
@pytest.fixture(scope="function")
def auth_admin_fresh(client):
    """Token admin frais — à utiliser quand le test révoque le token."""
    response = client.post(
        "/auth/login",
        data={"username": "admin@attijaribank.tn", "password": "Admin@2026!"},
    )
    assert response.status_code == 200, f"Login admin frais échoué : {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Token responsable IT ──────────────────────────────────────
@pytest.fixture(scope="session")
def auth_responsable(client):
    """Headers avec token JWT responsable IT."""
    response = client.post(
        "/auth/login",
        data={"username": "responsable.it@attijaribank.tn", "password": "Resp@2026!"},
    )
    assert response.status_code == 200, f"Login responsable échoué : {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Token robot UiPath ────────────────────────────────────────
@pytest.fixture(scope="session")
def auth_robot(client):
    """Headers avec token JWT robot UiPath."""
    response = client.post(
        "/auth/login",
        data={"username": "robot@attijaribank.tn", "password": "Robot@2026!"},
    )
    assert response.status_code == 200, f"Login robot échoué : {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

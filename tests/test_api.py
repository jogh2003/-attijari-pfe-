"""
test_api.py — Tests d'intégration complets
PFE Attijari bank — Sujet 21

Exécuter : pytest tests/test_api.py -v
Avec couverture : pytest tests/ --cov=app --cov-report=term-missing -v
"""
import pytest


# ════════════════════════════════════════════════════════════
# 1. TESTS SYSTÈME
# ════════════════════════════════════════════════════════════

class TestSysteme:

    def test_root_endpoint(self, client):
        """GET / retourne les infos de l'API."""
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert "version" in data
        assert data["version"] == "1.0.0"
        assert "statut" in data

    def test_health_endpoint(self, client):
        """GET /health retourne l'état du système."""
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert "status" in data
        assert data["status"] in ("healthy", "degraded")

    def test_docs_disponibles(self, client):
        """GET /docs retourne la page Swagger."""
        r = client.get("/docs")
        assert r.status_code == 200

    def test_redoc_disponible(self, client):
        """GET /redoc retourne la page ReDoc."""
        r = client.get("/redoc")
        assert r.status_code == 200


# ════════════════════════════════════════════════════════════
# 2. TESTS AUTHENTIFICATION
# ════════════════════════════════════════════════════════════

class TestAuthentification:

    def test_login_admin_succes(self, client):
        """Connexion admin avec identifiants corrects."""
        r = client.post(
            "/auth/login",
            data={"username": "admin@attijaribank.tn", "password": "Admin@2026!"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "admin"
        assert data["nom"] == "Administrateur"

    def test_login_responsable_succes(self, client):
        """Connexion responsable IT."""
        r = client.post(
            "/auth/login",
            data={"username": "responsable.it@attijaribank.tn", "password": "Resp@2026!"},
        )
        assert r.status_code == 200
        assert r.json()["role"] == "responsable_it"

    def test_login_robot_uipath_succes(self, client):
        """Connexion robot UiPath."""
        r = client.post(
            "/auth/login",
            data={"username": "robot@attijaribank.tn", "password": "Robot@2026!"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["nom"] == "Robot UiPath"

    def test_login_mauvais_mot_de_passe(self, client):
        """Connexion avec mauvais mot de passe → 401."""
        r = client.post(
            "/auth/login",
            data={"username": "admin@attijaribank.tn", "password": "mauvais"},
        )
        assert r.status_code == 401

    def test_login_utilisateur_inconnu(self, client):
        """Connexion avec email inconnu → 401."""
        r = client.post(
            "/auth/login",
            data={"username": "inconnu@test.com", "password": "test"},
        )
        assert r.status_code == 401

    def test_get_me_authentifie(self, client, auth_admin):
        """GET /auth/me retourne les infos de l'utilisateur connecté."""
        r = client.get("/auth/me", headers=auth_admin)
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == "admin@attijaribank.tn"
        assert data["role"] == "admin"
        assert "id" in data

    def test_get_me_sans_token(self, client):
        """GET /auth/me sans token → 401."""
        r = client.get("/auth/me")
        assert r.status_code == 401

    def test_get_me_token_invalide(self, client):
        """GET /auth/me avec token invalide → 401."""
        r = client.get("/auth/me", headers={"Authorization": "Bearer faux_token"})
        assert r.status_code == 401

    def test_logout(self, client, auth_admin_fresh):
        """POST /auth/logout révoque le token JWT côté serveur."""
        r = client.post("/auth/logout", headers=auth_admin_fresh)
        assert r.status_code == 200
        assert "message" in r.json()
        # Vérifier que le token est bien révoqué
        r2 = client.get("/auth/me", headers=auth_admin_fresh)
        assert r2.status_code == 401


# ════════════════════════════════════════════════════════════
# 3. TESTS RÉCLAMATIONS
# ════════════════════════════════════════════════════════════

class TestReclamations:

    def test_get_reclamations_liste(self, client, auth_admin):
        """GET /reclamations retourne la liste des tickets."""
        r = client.get("/reclamations/", headers=auth_admin)
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_get_reclamations_pagination(self, client, auth_admin):
        """Pagination : limit et offset fonctionnent."""
        r = client.get("/reclamations/?limit=10&offset=0", headers=auth_admin)
        assert r.status_code == 200
        data = r.json()
        assert len(data["data"]) <= 10

    def test_get_reclamations_filtre_statut(self, client, auth_admin):
        """Filtre par statut."""
        r = client.get("/reclamations/?statut=resolue&limit=5", headers=auth_admin)
        assert r.status_code == 200

    def test_get_reclamations_filtre_severite(self, client, auth_admin):
        """Filtre par sévérité minimum."""
        r = client.get("/reclamations/?severite_min=1&limit=5", headers=auth_admin)
        assert r.status_code == 200

    def test_get_reclamations_sans_auth(self, client):
        """GET /reclamations sans token → 401."""
        r = client.get("/reclamations/")
        assert r.status_code == 401

    def test_get_stats_reclamations(self, client, auth_admin):
        """GET /reclamations/stats retourne les statistiques."""
        r = client.get("/reclamations/stats", headers=auth_admin)
        assert r.status_code == 200
        data = r.json()
        assert "total_tickets" in data
        assert "groupes" in data

    def test_get_reclamation_introuvable(self, client, auth_admin):
        """GET /reclamations/INEXISTANT → 404."""
        r = client.get("/reclamations/ID_INEXISTANT_XYZ", headers=auth_admin)
        assert r.status_code == 404

    def test_analyser_reclamation_nlp(self, client, auth_admin):
        """POST /reclamations/analyser retourne un score d'anomalie."""
        r = client.post(
            "/reclamations/analyser",
            json={
                "description": "Blocage firewall — compromission détectée sur serveur SWIFT",
                "type_operation": "Sécurité Opérationnelle",
                "severite": 1,
            },
            headers=auth_admin,
        )
        assert r.status_code == 200
        data = r.json()
        assert "score_anomalie" in data
        assert data["score_anomalie"] >= 0.5
        assert data["niveau"] in ("CRITIQUE", "SURVEILLANCE", "NORMAL")
        assert "alerte_declenchee" in data

    def test_analyser_reclamation_normal(self, client, auth_admin):
        """POST /reclamations/analyser — ticket normal."""
        r = client.post(
            "/reclamations/analyser",
            json={
                "description": "Demande de changement de bureau",
                "type_operation": "Stock",
                "severite": 4,
            },
            headers=auth_admin,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["score_anomalie"] < 0.75


# ════════════════════════════════════════════════════════════
# 4. TESTS ALERTES (UiPath)
# ════════════════════════════════════════════════════════════

class TestAlertes:

    def test_get_alertes_defaut(self, client, auth_robot):
        """GET /api/alertes retourne les alertes avec seuil 0.75."""
        r = client.get("/api/alertes/", headers=auth_robot)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        for alerte in data:
            assert alerte["score_risque"] >= 0.75
            assert "action_recommandee" in alerte
            assert alerte["priorite"] in (1, 2)

    def test_get_alertes_seuil_eleve(self, client, auth_robot):
        """GET /api/alertes?seuil=0.90 — uniquement les critiques."""
        r = client.get("/api/alertes/?seuil=0.90", headers=auth_robot)
        assert r.status_code == 200
        for alerte in r.json():
            assert alerte["score_risque"] >= 0.90

    def test_get_alertes_seuil_invalide(self, client, auth_robot):
        """Seuil > 1 → erreur de validation."""
        r = client.get("/api/alertes/?seuil=1.5", headers=auth_robot)
        assert r.status_code == 422

    def test_get_alertes_seuil_negatif(self, client, auth_robot):
        """Seuil < 0 → erreur de validation."""
        r = client.get("/api/alertes/?seuil=-0.1", headers=auth_robot)
        assert r.status_code == 422

    def test_get_alertes_sans_auth(self, client):
        """GET /api/alertes sans token → 401."""
        r = client.get("/api/alertes/")
        assert r.status_code == 401

    def test_get_alertes_stats(self, client, auth_admin):
        """GET /api/alertes/stats retourne les statistiques."""
        r = client.get("/api/alertes/stats", headers=auth_admin)
        assert r.status_code == 200
        data = r.json()
        assert "alertes_critiques" in data
        assert "tickets_total" in data

    def test_cloturer_alerte(self, client, auth_robot):
        """POST /api/alertes/{id}/cloturer retourne la confirmation."""
        r = client.post(
            "/api/alertes/REC-TEST-001/cloturer",
            json={"action_effectuee": "Mise à jour firewall", "statut_final": "resolue"},
            headers=auth_robot,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["statut_final"] == "resolue"
        assert "apprentissage" in data

    def test_cloturer_alerte_statut_invalide(self, client, auth_robot):
        """Statut final invalide → 400."""
        r = client.post(
            "/api/alertes/REC-TEST-001/cloturer",
            json={"action_effectuee": "test", "statut_final": "invalide_xyz"},
            headers=auth_robot,
        )
        assert r.status_code == 400


# ════════════════════════════════════════════════════════════
# 5. TESTS PRÉDICTIONS LSTM
# ════════════════════════════════════════════════════════════

class TestPredictions:

    def test_get_predictions_tous_groupes(self, client, auth_admin):
        """GET /api/predictions retourne tous les groupes."""
        r = client.get("/api/predictions/", headers=auth_admin)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0
        for pred in data:
            assert "score_risque" in pred
            assert "type_operation" in pred
            assert pred["niveau"] in ("CRITIQUE", "SURVEILLANCE", "NORMAL")

    def test_get_predictions_alertes_seulement(self, client, auth_admin):
        """GET /api/predictions?alertes_seulmt=true — uniquement les alertes."""
        r = client.get("/api/predictions/?alertes_seulmt=true", headers=auth_admin)
        assert r.status_code == 200
        for pred in r.json():
            assert pred["est_alerte"] is True
            assert pred["score_risque"] >= 0.75

    def test_predire_ticket(self, client, auth_admin):
        """POST /api/predictions/predire calcule un score."""
        r = client.post(
            "/api/predictions/predire",
            json={"type_operation": "Sécurité Opérationnelle", "severite": 1},
            headers=auth_admin,
        )
        assert r.status_code == 200
        data = r.json()
        assert "score_risque" in data
        assert data["score_risque"] > 0.0
        assert data["est_alerte"] is True

    def test_predire_ticket_normal(self, client, auth_admin):
        """POST /api/predictions/predire — groupe à faible risque."""
        r = client.post(
            "/api/predictions/predire",
            json={"type_operation": "Stock", "severite": 4},
            headers=auth_admin,
        )
        assert r.status_code == 200
        assert r.json()["score_risque"] < 0.75

    def test_predictions_dashboard(self, client, auth_admin):
        """GET /api/predictions/dashboard retourne les données Chart.js."""
        r = client.get("/api/predictions/dashboard", headers=auth_admin)
        assert r.status_code == 200
        data = r.json()
        assert "labels" in data
        assert "scores_risque" in data
        assert len(data["labels"]) == len(data["scores_risque"])

    def test_predictions_modele_info(self, client, auth_admin):
        """GET /api/predictions/modele retourne les infos du modèle LSTM."""
        r = client.get("/api/predictions/modele", headers=auth_admin)
        assert r.status_code == 200
        data = r.json()
        assert "version" in data
        assert "architecture" in data


# ════════════════════════════════════════════════════════════
# 6. TESTS RECOMMANDATIONS KNN
# ════════════════════════════════════════════════════════════

class TestRecommandations:

    def test_get_recommandations(self, client, auth_admin):
        """GET /api/recommandations retourne des recommandations."""
        r = client.get("/api/recommandations/", headers=auth_admin)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        for reco in data:
            assert "action_suggeree" in reco
            assert "taux_succes" in reco
            assert 0.0 <= reco["taux_succes"] <= 1.0

    def test_analyser_recommandation(self, client, auth_admin):
        """POST /api/recommandations/analyser retourne une recommandation KNN."""
        r = client.post(
            "/api/recommandations/analyser",
            json={
                "texte": "Problème accès SWIFT — timeout connexion",
                "groupe": "SWIFT",
                "categorie": "Erreur connexion",
            },
            headers=auth_admin,
        )
        assert r.status_code == 200
        data = r.json()
        assert "action_suggeree" in data
        assert "taux_succes" in data
        assert "priorite" in data

    def test_get_recommandation_par_id(self, client, auth_admin):
        """GET /api/recommandations/{id} retourne une recommandation."""
        r = client.get("/api/recommandations/REC-TEST-001", headers=auth_admin)
        assert r.status_code == 200
        data = r.json()
        assert data["reclamation_id"] == "REC-TEST-001"

    def test_valider_recommandation(self, client, auth_responsable):
        """POST /api/recommandations/{id}/valider — validation."""
        r = client.post(
            "/api/recommandations/RECO-001/valider",
            json={"decision": "valider", "commentaire": "Action approuvée"},
            headers=auth_responsable,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["statut"] == "validee"

    def test_rejeter_recommandation(self, client, auth_responsable):
        """POST /api/recommandations/{id}/valider — rejet."""
        r = client.post(
            "/api/recommandations/RECO-002/valider",
            json={"decision": "rejeter"},
            headers=auth_responsable,
        )
        assert r.status_code == 200
        assert r.json()["statut"] == "rejetee"

    def test_valider_decision_invalide(self, client, auth_responsable):
        """Decision invalide → 400."""
        r = client.post(
            "/api/recommandations/RECO-003/valider",
            json={"decision": "ignorer"},
            headers=auth_responsable,
        )
        assert r.status_code == 400


# ════════════════════════════════════════════════════════════
# 7. TESTS CONTRÔLE D'ACCÈS (RBAC)
# ════════════════════════════════════════════════════════════

class TestControleAcces:

    def test_audit_accessible_admin(self, client, auth_admin):
        """GET /api/audit accessible par admin."""
        r = client.get("/api/audit/", headers=auth_admin)
        assert r.status_code == 200

    def test_audit_accessible_responsable(self, client, auth_responsable):
        """GET /api/audit accessible par responsable IT."""
        r = client.get("/api/audit/", headers=auth_responsable)
        assert r.status_code == 200

    def test_audit_stats_accessible(self, client, auth_admin):
        """GET /api/audit/stats accessible."""
        r = client.get("/api/audit/stats", headers=auth_admin)
        assert r.status_code == 200
        data = r.json()
        assert "total_actions" in data
        assert "connexions" in data

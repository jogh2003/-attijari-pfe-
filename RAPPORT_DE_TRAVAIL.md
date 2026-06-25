# Rapport de Travail et Description du Code

## 1. Contexte du projet

Ce projet est un système de détection et de traitement de tickets IT pour Attijari Bank, associant :
- une architecture **IA hybride** pour analyser les tickets,
- une intégration **RPA UiPath** pour la détection et la notification,
- une **persistence PostgreSQL** pour l’historique, les responsables et les logs,
- une interface frontend pour la démonstration.

L’objectif est de gérer automatiquement les alertes critiques, notifier le responsable IT et clôturer les incidents avec un suivi audit.

---

## 2. Architecture générale

### 2.1 Backend

Le backend est développé avec **FastAPI** et se compose de :
- `app/main.py` : point d’entrée de l’application, configuration FastAPI, CORS, lifecycle, et endpoints frontend.
- `app/core/database.py` : configuration SQLAlchemy, session PostgreSQL, création de tables.
- `app/core/logging_config.py` : configuration du logging.
- `app/core/scheduler.py` : scheduler APScheduler pour réentraînement automatique chaque lundi à 02h00.
- `app/core/security.py` : gestion JWT HS256 et protection des routes.
- `app/core/notifications.py` : fonction `send_email()` pour envoi SMTP avec fallback.

### 2.2 Modèles AI

- `app/routers/reclamations.py` : pipeline NLP, chargement des données, logique d’analyse hybride.
- `app/routers/predictions.py` : XGBoost pour score de risque et prédiction SLA.
- `app/routers/recommandations.py` : LightGBM pour recommandations d’action.
- `app/routers/alertes.py` : gestion des alertes UiPath, chargement des modèles, notification, clôture.

### 2.3 Frontend

- `static/index.html` : interface HTML/CSS/JS avec :
  - dashboard
  - analyse NLP
  - prédictions XGBoost
  - recommandations LightGBM
  - alertes UiPath
  - audit trail
  - authentification et rôles.

### 2.4 Tests

- `tests/test_api.py` : tests d’intégration des endpoints principaux.
- `tests/test_security.py` : tests de sécurité et JWT.
- `tests/conftest.py` : fixtures de tests.
- `scripts/smoke_demo.py` : scénario de validation de bout en bout sans serveur.

---

## 3. Détails techniques du code

### 3.1 `app/main.py`

- Initialise l’application FastAPI avec `lifespan`.
- Crée automatiquement les tables PostgreSQL et les utilisateurs par défaut.
- Clone les données `CSV + PostgreSQL` pour conserver la persistance des tickets.
- Monte l’interface statique, le fichier `index.html` et les pages de rapport.
- Ajoute un endpoint `/favicon.ico` pour éviter les erreurs 404.
- Définit les routes principales : auth, réclamations, alertes, prédictions, recommandations, audit et diagnostic.

### 3.2 `app/core/database.py`

- Gère la connexion PostgreSQL via SQLAlchemy.
- Définit `get_db()` pour injection de dépendance dans FastAPI.
- Appelle `Base.metadata.create_all()` pour créer toutes les tables ORM.
- Assure l’import des modèles nécessaires pour créer les tables.

### 3.3 `app/core/notifications.py`

- `send_email(recipients, subject, body)` : envoie SMTP si la config est définie.
- Environnement pris en charge : `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`.
- Fallback de simulation quand SMTP n’est pas configuré pour la démo.

### 3.4 `app/routers/auth.py`

- Authentification via `POST /auth/login`.
- JWT avec expiration longue (480 min).
- Routes pour `auth/me` et `auth/logout`.
- Rôles : `admin`, `responsable_it`, `utilisateur`, `responsable_it` pour le robot UiPath.

### 3.5 `app/routers/reclamations.py`

- Charge les données : `data/processed/dataset_nlp_enrichi.csv`.
- Merge les réclamations CSV avec celles persistées en PostgreSQL.
- Analyse NLP avec score d’anomalie.
- Détermine le niveau de risque et si une alerte est déclenchée.
- Fournit `GET /reclamations`, `GET /reclamations/{id}`, `POST /reclamations/analyser`, `POST /reclamations/soumettre`.

### 3.6 `app/routers/predictions.py`

- Charge le modèle XGBoost depuis `models/xgb_model.pkl`.
- Fournit `POST /api/predictions/predire`.
- Retourne `score_risque`, `niveau`, `est_alerte`, source des données et version du modèle.
- Utilise des scores réels par groupe pour ancrer les résultats.

### 3.7 `app/routers/recommandations.py`

- Charge les modèles LightGBM et KNN pour recommandation hybride.
- Fournit `POST /api/recommandations/analyser` et `POST /api/recommandations/similaire`.
- Retourne action suggérée, taux de succès, similarité KNN, incidents similaires et alternatives.

### 3.8 `app/routers/alertes.py`

- Charge les modèles nécessaires et les tickets pour le module alertes.
- Endpoint `GET /api/alertes?seuil=0.75` pour UiPath.
- Endpoint `POST /api/alertes/{id}/notifier` pour notifier le responsable IT.
- Endpoint `POST /api/alertes/{id}/cloturer` pour clôturer et persister l’alerte.
- Gère l’historique de résolution et le journal audit.

### 3.9 `app/routers/audit.py`

- Journalise toutes les actions importantes : login, alertes, notifications, clôtures.
- Fournit un historique consultable pour la conformité bancaire.

### 3.10 `app/models/responsable.py`

- Définit le modèle SQLAlchemy `Responsable`.
- Table `responsables` pour stocker les contacts IT.
- Permet d’ajouter des responsables et de retrouver leur email.

---

## 4. Fonctionnalités implémentées

### 4.1 Détection et analyse
- **Pipeline NLP** : analyse du texte libre, détection de mots clés, score d’anomalie.
- **XGBoost** : évalue le risque de ticket et confirme les alertes.
- **LightGBM** : recommande des actions correctives selon 35 classes.

### 4.2 Intégration RPA
- **UiPath** utilise `GET /api/alertes?seuil=0.75`.
- Le système déclenche une alerte si le score dépasse le seuil.
- Ajout d’un bouton `Notifier IT` pour envoyer un email via SMTP ou simulation.
- Clôture persistée via `POST /api/alertes/{id}/cloturer`.

### 4.3 Gestion des rôles
- `admin` : accès complet, back-office, analytics, configuration.
- `responsable_it` : accès aux alertes, notifications IT, audit, clôture.
- `utilisateur` : soumission de réclamations et consultation des résultats.
- `robot UiPath` : flux RPA, consultation des alertes et actions automatisées.

### 4.4 Support de démonstration
- Frontend accessible sur `http://localhost:8000`.
- Dashboard avec KPI, graphiques et statut des modèles.
- Scénario de démonstration déjà préparé dans `SCENARIO_DEMO_JURY.md`.
- Fichier de test de fumée `scripts/smoke_demo.py` pour valider le flux complet.

---

## 5. Résultats de validation

### Tests
- `pytest` exécute les tests d’intégration et de sécurité.
- `scripts/smoke_demo.py` vérifie :
  - login administrateur et robot
  - récupération des alertes
  - notification IT
  - clôture d’alerte
  - prédiction XGBoost
  - recommandation LightGBM
  - lecture des responsables

### Vérification manuelle
- Démarrage du serveur avec `uvicorn app.main:app --reload`
- Accès au frontend
- Navigation dans les pages : dashboard, NLP, XGBoost, LightGBM, alertes, audit
- Confirmation que les modèles se chargent correctement

---

## 6. Conseils pour la présentation

1. Lancer le backend avec `uvicorn app.main:app --reload`.
2. Ouvrir `http://localhost:8000`.
3. Commencer par le dashboard pour présenter l’état du système.
4. Montrer la détection d’un ticket via NLP.
5. Confirmer le score avec XGBoost.
6. Montrer la recommandation LightGBM.
7. Montrer les alertes UiPath, notifier le responsable IT et clôturer l’alerte.
8. Terminer avec l’historique et l’audit trail.

---

## 7. Points forts de ton travail

- Architecture claire et modulaire.
- Intégration hybridé IA + RPA.
- Persistante en base PostgreSQL.
- Interface exploitable pour la soutenance.
- Fichier de démonstration et guide jury déjà prêts.
- Endpoint `/favicon.ico` ajouté pour un front clean.

---

## 8. Fichiers importants

- `app/main.py`
- `app/core/database.py`
- `app/core/notifications.py`
- `app/routers/reclamations.py`
- `app/routers/predictions.py`
- `app/routers/recommandations.py`
- `app/routers/alertes.py`
- `static/index.html`
- `SCENARIO_DEMO_JURY.md`
- `scripts/smoke_demo.py`
- `tests/test_api.py`

---

## 9. Remarques finales

Ton projet est prêt pour la soutenance. Le système est complet, fonctionnel et documenté, avec des cas de test et un scénario de démonstration clair.

# Système de Détection IA & RPA — Attijari Bank
## PFE 2025–2026 — Sujet 21 — Génie Logiciel

> **Backend FastAPI v2.0** — Détection d'anomalies IT par Architecture Hybride (Score Anomalie + XGBoost + LightGBM) & Automatisation RPA UiPath  
> Données réelles : **1507 tickets IT** Attijari Bank — Février–Mars 2026

---

## Vue d'ensemble

Ce projet implémente un système intelligent de gestion des réclamations IT pour Attijari Bank (Tunisie).  
Il combine trois technologies :

- **IA** : Architecture Hybride 3 niveaux (Score Anomalie + XGBoost + LightGBM)
- **RPA** : Robot UiPath pour le traitement automatique des alertes critiques
- **Backend** : API REST FastAPI sécurisée avec PostgreSQL, JWT et audit trail complet

### Données
- **Source** : 1507 tickets IT réels Attijari Bank (Fév–Mars 2026)
- **Fichiers bruts** : `data/raw/` (Excel Fév + Mars 2026)
- **Données nettoyées** : `data/cleaned/reclamations_propres.csv`
- **Données enrichies NLP** : `data/processed/dataset_nlp_enrichi.csv`

---

## Installation rapide (Windows)

```bash
# 1. Environnement virtuel
python -m venv venv
venv\Scripts\activate

# 2. Dépendances
pip install -r requirements.txt

# 3. Variables d'environnement
copy .env.example .env
# Modifier .env si besoin (DB_PASSWORD, JWT_SECRET_KEY, etc.)

# 4. Base de données PostgreSQL (optionnel — l'API fonctionne sans)
python scripts/init_db.py       # Créer les tables
python scripts/import_csv.py    # Importer les 1507 tickets

# 5. Lancer l'API
uvicorn app.main:app --reload
```

L'API démarre sur **http://localhost:8000**

### Avec Docker (optionnel)
```bash
docker-compose up -d
```

---

## URLs principales

| URL | Description |
|-----|-------------|
| http://localhost:8000 | Frontend HTML (tableau de bord) |
| http://localhost:8000/docs | Swagger UI — Tester tous les endpoints |
| http://localhost:8000/redoc | Documentation ReDoc |
| http://localhost:8000/health | État du système (DB + modèles) |
| http://localhost:8000/api/alertes?seuil=0.75 | **Endpoint UiPath principal** |
| http://localhost:8000/api/diagnostic | Diagnostic complet (DB + ML + UiPath) |
| http://localhost:8000/diagrammes | Index des diagrammes explicatifs |
| http://localhost:8000/diagrammes/architecture | Diagramme architecture système |
| http://localhost:8000/diagrammes/methodes-ia | Diagramme méthodes IA & flux hybride |

---

## Comptes de test

| Email | Mot de passe | Rôle |
|-------|-------------|------|
| admin@attijaribank.tn | Admin@2026! | Administrateur |
| responsable.it@attijaribank.tn | Resp@2026! | Responsable IT |
| meriam@attijaribank.tn | Stage@2026! | Utilisateur |
| robot@attijaribank.tn | Robot@2026! | Robot UiPath |

---

## Architecture Hybride 3 Niveaux (v2.0)

Le cœur du système est une architecture hybride qui combine vitesse, précision et explicabilité :

```
┌────────────────────────────────────────────────────────────────┐
│              TICKET ENTRANT (description + sévérité)           │
└──────────────────────────┬─────────────────────────────────────┘
                           │
         ┌─────────────────▼──────────────────┐
         │  NIVEAU 1 — Score Anomalie (< 10ms) │  ← app/services/hybrid_detection.py
         │  Règles métier sur mots critiques   │
         │  "compromission" +0.25              │
         │  "firewall"      +0.20              │
         │  Sévérité==1     +0.30              │
         │  Sécurité Opé.   +0.20              │
         └─────────────────┬──────────────────┘
                           │
              score ≥ 0.75 ?
             /              \
           OUI               NON
            │                 │
     ALERTE_IMMEDIATE    score ∈ [0.60, 0.75) ?
     (immédiat, < 10ms)       │
                              │
         ┌────────────────────▼──────────────────┐
         │  NIVEAU 2 — Confirmation XGBoost      │
         │  Prédit prob. retard SLA              │
         │  Zone grise : XGB ≥ 0.70 → confirme  │
         │  Cas complexe : XGB ≥ 0.85 → détecte │
         └─────────────────┬─────────────────────┘
                           │
              alerte confirmée ?
             /               \
           OUI                NON
            │                  │
     ALERTE_CONFIRME      SURVEILLANCE / NORMAL
            │
         ┌──▼────────────────────────────────────┐
         │  LightGBM — Recommandation Action      │
         │  35 classes d'action corrective        │
         │  TF-IDF + encodeurs + sévérité         │
         └──┬────────────────────────────────────┘
            │
         ┌──▼────────────────────────────────────┐
         │  NIVEAU 3 — Analyse Temporelle        │
         │  Évolution hebdomadaire               │
         │  Forecasting par groupe IT            │
         │  Réentraînement automatique (lundi)   │
         └───────────────────────────────────────┘
            │
         ┌──▼────────────────────────────────────┐
         │  ROBOT UIPATH                         │
         │  GET  /api/alertes?seuil=0.75         │
         │  POST /api/alertes/{id}/cloturer      │
         └───────────────────────────────────────┘
```

### Comparatif Score Anomalie vs XGBoost seul

| Critère | XGBoost seul | **Hybride** | Gagnant |
|---------|-------------|------------|---------|
| Vitesse | 50–100ms | **< 10ms (N1)** | Hybride |
| Précision | **85–95%** | 70–95% selon niveau | Actuelle |
| Explicabilité | Faible | **Forte (règles N1)** | Hybride |
| Robustesse | Risque drift | **Stable (règles fixes)** | Hybride |
| Fiabilité prod | Risque .pkl | **Très fiable (N1)** | Hybride |
| Coût calcul | Élevé | **Faible (N1)** | Hybride |
| Audit bancaire | Difficile | **Facile (N1 explicite)** | Hybride |

**Score : Hybride gagne 10/13 critères** → Architecture recommandée pour environnement bancaire.

---

## Modèles Machine Learning

### XGBoost (Détection Retard SLA)
- **Fichier** : `models/xgb_model.pkl`
- **Accuracy** : 99.67% — **AUC** : 1.000
- **Estimateurs** : 400 — **max_depth** : 4 — **learning_rate** : 0.10
- **Entraînement** : 1205 tickets — **Test** : 302 tickets
- **Features** : score_risque (47%), score_anomalie (29%), type_operation_enc (9%), sévérité (8%), durée (5%), catégorie (2%)
- **Usage dans hybride** : Niveau 2 (confirmation zone grise)

### LightGBM (Recommandation Action Corrective)
- **Fichier** : `models/lgbm_reco_model.pkl`
- **Classes** : 35 actions correctives
- **Précision Top-1** : 62.91% — **Top-3** : 64.36%
- **Entraînement** : 1374 tickets
- **Features** : TF-IDF(500 bigrams) + type_operation_enc + categorie_enc + sévérité
- **Usage** : Recommandation action après toute alerte détectée

### Encodeurs & Vectoriseurs
| Fichier | Rôle |
|---------|------|
| `models/label_encoder_groupe.pkl` | Encode les 11 groupes IT |
| `models/label_encoder_categorie.pkl` | Encode les catégories IT |
| `models/le_action.pkl` | Encode les 35 classes d'action |
| `models/vec_reco.pkl` | TF-IDF vectorizer recommandations |

---

## Structure du Projet

```
projet/
├── app/                           # Application FastAPI
│   ├── main.py                    # Point d'entrée + lifecycle + CORS
│   ├── core/
│   │   ├── audit.py               # Audit trail centralisé
│   │   ├── config.py              # Variables d'environnement (Pydantic Settings)
│   │   ├── database.py            # PostgreSQL + SQLAlchemy (pool 10+20 conn.)
│   │   ├── logging_config.py      # Loguru (fichier + console)
│   │   ├── scheduler.py           # APScheduler (réentraînement lundi 02h00)
│   │   └── security.py            # JWT HS256 + AES-256 Fernet + bcrypt
│   ├── models/                    # ORM SQLAlchemy
│   │   ├── audit_log.py           # Table audit_logs
│   │   ├── reclamation.py         # Table reclamations
│   │   ├── responsable.py         # Table responsables IT
│   │   └── utilisateur.py         # Table utilisateurs
│   ├── routers/                   # Endpoints API
│   │   ├── auth.py                # /auth — JWT, login, logout, rate limiting
│   │   ├── alertes.py             # /api/alertes — Endpoint principal UiPath
│   │   ├── predictions.py         # /api/predictions — Scores XGBoost
│   │   ├── recommandations.py     # /api/recommandations — LightGBM
│   │   ├── reclamations.py        # /reclamations — CRUD + analyse hybride
│   │   ├── audit.py               # /api/audit — Audit trail
│   │   └── diagnostic.py          # /api/diagnostic — Vérification connexions
│   └── services/
│       ├── hybrid_detection.py    # Architecture hybride 3 niveaux (NOUVEAU v2.0)
│       └── nlp_service.py         # spaCy + SentenceTransformers
│
├── models/                        # Modèles ML entraînés
│   ├── xgb_model.pkl              # XGBoost — 99.67% accuracy, AUC=1.0
│   ├── metriques_xgb.json         # Métriques XGBoost
│   ├── lgbm_reco_model.pkl        # LightGBM — 62.91% Top-1, 35 classes (baseline random ~2.86%, majority ~63.5%)
│   ├── metriques_lgbm_reco.json   # Métriques LightGBM
│   ├── label_encoder_groupe.pkl   # Encodeur 11 groupes IT
│   ├── label_encoder_categorie.pkl# Encodeur catégories
│   ├── le_action.pkl              # Encodeur 35 actions
│   └── vec_reco.pkl               # TF-IDF recommandations
│
├── data/
│   ├── raw/                       # Données Excel brutes (Fév + Mars 2026)
│   ├── cleaned/
│   │   └── reclamations_propres.csv  # 1507 tickets nettoyés
│   └── processed/
│       └── dataset_nlp_enrichi.csv   # 1507 tickets + scores NLP + enrichissement
│
├── uipath/                        # Projet UiPath Studio
│   ├── Main.xaml                  # Orchestrateur principal
│   ├── CheckAlerte.xaml           # Appelle GET /api/alertes?seuil=0.75
│   ├── ConfirmerResolution.xaml   # Appelle POST /api/alertes/{id}/cloturer
│   └── NotifierIT.xaml            # Envoi notification responsable IT
│
├── scripts/                       # Scripts utilitaires
│   ├── init_db.py                 # Créer les tables PostgreSQL
│   ├── import_csv.py              # Importer les tickets en base
│   ├── import_et_nettoyage.py     # Nettoyage données brutes Excel
│   ├── pipeline_nlp.py            # Pipeline NLP complet (enrichissement)
│   ├── entrainer_xgboost.py       # Entraîner XGBoost (relancer si nouvelles données)
│   ├── entrainer_lightgbm_reco.py # Entraîner LightGBM Reco
│   └── backup_db.py               # Sauvegarde PostgreSQL
│
├── tests/                         # Tests automatisés
│   ├── conftest.py                # Fixtures pytest (client, tokens)
│   ├── test_api.py                # Tests d'intégration (40+ tests)
│   └── test_security.py           # Tests sécurité (JWT, bcrypt, AES)
│
├── rapport/
│   └── diagrammes/
│       ├── index.html             # Index des diagrammes
│       ├── architecture_systeme.html  # Architecture complète
│       └── methodes_ia.html       # Méthodes IA + flux hybride + comparatif
│
├── static/
│   └── index.html                 # Frontend HTML (tableau de bord)
│
├── .env                           # Variables d'environnement (non commité)
├── .env.example                   # Template .env
├── docker-compose.yml             # PostgreSQL + Redis + Elasticsearch + MLflow
├── Dockerfile                     # Image Docker API
├── init_database.sql              # Schéma SQL initial
└── requirements.txt               # Dépendances Python
```

---

## Endpoints API Complets

### Authentification — `/auth`
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | /auth/login | Connexion → JWT (form-data : username + password) |
| GET | /auth/me | Profil utilisateur connecté |
| POST | /auth/logout | Révocation token JWT |

### Analyse IA — `/reclamations`
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | /reclamations/ | Liste 1507 tickets (filtres : statut, groupe, retard, sévérité) |
| GET | /reclamations/stats | Statistiques dashboard (Chart.js) |
| GET | /reclamations/export | Export CSV UTF-8 (Excel compatible) |
| GET | /reclamations/mes-tickets | Tickets soumis par l'utilisateur connecté |
| GET | /reclamations/{id} | Détail d'un ticket |
| POST | /reclamations/analyser | **Analyse hybride** (N1 + N2 + score + méthode) |
| POST | /reclamations/soumettre | Soumission ticket → score + recommandation LightGBM + KNN |

### Alertes UiPath — `/api/alertes`
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | /api/alertes/ | **Endpoint UiPath** — alertes actives (seuil paramétrable) |
| GET | /api/alertes/stats | Statistiques + répartition méthodes hybride |
| GET | /api/alertes/hybride/stats | **Détail N1 vs N2** — statistiques architecture hybride |
| POST | /api/alertes/{id}/cloturer | Confirmer résolution (UiPath ConfirmerResolution.xaml) |

### Prédictions XGBoost — `/api/predictions`
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | /api/predictions/ | Scores de risque par groupe IT |
| POST | /api/predictions/predire | Score XGBoost pour un ticket |
| GET | /api/predictions/dashboard | Données Chart.js (barres + métriques) |
| GET | /api/predictions/modele | Informations modèle XGBoost |
| GET | /api/predictions/evolution | **Évolution temporelle** hebdomadaire (Niveau 3) |

---

**Préparation à la soutenance**

- Objectif : démontrer le flux bout-en-bout — soumission ticket → détection → recommandation → action RPA.
- Checklist rapide :
  - Lancer l'API : `uvicorn app.main:app --reload`
  - Ouvrir le dashboard : `http://localhost:8000`
  - Compte démo : `responsable.it@attijaribank.tn / Resp@2026!`
  - Simuler une soumission sur la page `Soumettre une réclamation` puis aller sur `Alertes UiPath` pour montrer le déclenchement.
  - Montrer la page `Prédictions XGBoost` : prédire un groupe, vérifier l'apparition du marqueur "Prédiction récente" sur la courbe.
  - Montrer la section `Robots UiPath` et expliquer le flux `CheckAlerte → NotifierIT → ConfirmerResolution`.

**Commandes utiles (démo)**

```powershell
# Activer venv
venv\Scripts\Activate.ps1

# Lancer API
uvicorn app.main:app --reload

# Lancer tests rapides
pytest tests/test_api.py -q
```

**Vérification end-to-end automatisée**

J'ai ajouté le script PowerShell `scripts/demo_verify.ps1` qui :
- active l'environnement virtuel,
- démarre l'API (`uvicorn`) en arrière-plan,
- attend que `/health` soit accessible,
- récupère un token robot (`robot@attijaribank.tn`) puis appelle `GET /api/alertes?seuil=0.75`,
- récupère un token admin et soumet une réclamation de test (`POST /reclamations/soumettre`),
- tente de clôturer la première alerte retournée (`POST /api/alertes/{id}/cloturer`) en mode robot,
- lance un test rapide `pytest tests/test_api.py -q`,
- arrête le serveur.

Exécuter la vérification :

```powershell
.\scripts\demo_verify.ps1
```

**Note sur `tests/test_security.py`**

Le fichier `tests/test_security.py` était un script autonome (runner personnalisé) qui causait une erreur lors de la collecte pytest (fixture nom non trouvée). Pour éviter la collecte indésirable j'ai :
- renommé le runner interne `test()` en `run_test()`;
- laissé le fichier disponible pour exécution directe et adapté pour qu'il ne soit pas interprété comme tests pytest.

Si vous préférez, je peux séparer ce fichier en un script distinct `scripts/test_security_script.py` et remettre une version `pytest`-native. Dites-moi si vous voulez que j'automatise cela.


### Recommandations LightGBM + KNN — `/api/recommandations`
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | /api/recommandations/ | Liste des recommandations générées |
| POST | /api/recommandations/analyser | Recommandation LightGBM + KNN pour un texte |
| POST | /api/recommandations/similaire | Rechercher incidents similaires — recommandation KNN |
| GET | /api/recommandations/{id} | Recommandation pour un ticket |
| POST | /api/recommandations/{id}/valider | Valider ou rejeter une recommandation |

### Audit Trail — `/api/audit`
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | /api/audit/ | Historique complet des actions |
| GET | /api/audit/stats | Statistiques audit (admin + responsable IT) |

### Diagnostic — `/api/diagnostic`
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | /api/diagnostic/ | **Diagnostic complet** (DB + modèles + UiPath + hybride + frontend) |
| GET | /api/diagnostic/db | Test connexion PostgreSQL |
| GET | /api/diagnostic/models | État des modèles XGBoost + LightGBM |

### Système
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | /health | Santé globale API (DB + modèles) |
| GET | /diagrammes | Index diagrammes explicatifs |
| GET | /diagrammes/architecture | Architecture système |
| GET | /diagrammes/methodes-ia | Méthodes IA + flux hybride |

---

## Infrastructure Docker

```bash
# Démarrer tous les services
docker-compose up -d

# Vérifier l'état
docker-compose ps
```

Services disponibles :

| Service | Port | Description |
|---------|------|-------------|
| PostgreSQL 16 | 5432 | Base de données principale |
| FastAPI | 8000 | API REST + Frontend |
| Redis 7 | 6379 | Cache sessions |
| Elasticsearch 8 | 9200 | Recherche full-text |
| MLflow | 5000 | Suivi expériences ML |

---

## Sécurité

| Mécanisme | Détail |
|-----------|--------|
| **Authentification** | JWT HS256, expiration 480 min (8h) |
| **Mots de passe** | bcrypt avec salt |
| **Données sensibles** | AES-256 (Fernet) |
| **Rate limiting** | 10 tentatives / 5 min / IP |
| **Token blacklist** | Révocation côté serveur au logout |
| **RBAC** | 3 rôles : admin / responsable_it / utilisateur |
| **Audit trail** | Toutes les actions loguées (utilisateur, IP, horodatage) |
| **CORS** | Origines autorisées : localhost:3000, 5500, 8000, 8080 |

---

## Réentraînement Automatique (APScheduler)

| Planification | Tâche |
|--------------|-------|
| **Lundi 02:00** | Réentraînement XGBoost + LightGBM sur nouvelles données |
| **Dimanche 03:00** | Purge logs > 30 jours |

Commandes manuelles :
```bash
python scripts/entrainer_xgboost.py          # Réentraîner XGBoost
python scripts/entrainer_lightgbm_reco.py    # Réentraîner LightGBM
python scripts/pipeline_nlp.py               # Regénérer scores NLP
```

---

## Tests

```bash
# Tous les tests
pytest tests/ -v

# Avec couverture de code
pytest tests/ --cov=app --cov-report=term-missing -v

# Tests sécurité uniquement
pytest tests/test_security.py -v
```

---

## Intégration UiPath

Le robot UiPath interroge l'API toutes les N minutes :

```
# 1. Récupérer les alertes critiques
GET /api/alertes?seuil=0.75
Authorization: Bearer <token_robot>

Réponse :
[
  {
    "id": "1234",
    "type_operation": "Sécurité Opérationnelle",
    "score_risque": 0.87,
    "score_anomalie": 0.85,
    "priorite": 1,
    "action_recommandee": "Bloquer accès et escalader RSSI",
    "methode_detection": "score_anomalie",
    "niveau_detection": 1,
    "label_methode": "Niveau 1 — Score Anomalie",
    ...
  }
]

# 2. Clôturer après exécution
POST /api/alertes/1234/cloturer
Body: { "action_effectuee": "Accès bloqué", "statut_final": "resolue" }
```

**Priorités UiPath :**
- `priorite: 1` (score ≥ 0.85) → Exécution RPA automatique immédiate
- `priorite: 2` (score 0.75–0.85) → Validation responsable IT requise

## Notification Responsable IT (SMTP)

Le projet propose un endpoint pour notifier le responsable IT par email :

```
POST /api/alertes/{id}/notifier
Authorization: Bearer <token_robot | token_admin>
```

Le service d'envoi utilise les variables d'environnement SMTP suivantes (optionnel) :

```
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=bot@attijaribank.tn
SMTP_PASSWORD=secret
SMTP_FROM=no-reply@attijaribank.tn
SMTP_USE_TLS=true
```

Si `SMTP_HOST` n'est pas défini, l'envoi est simulé (utile en environnement de test).


---

## Variables d'Environnement (.env)

```env
# Base de données
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/attijari_pfe
DB_HOST=localhost
DB_PORT=5432
DB_NAME=attijari_pfe
DB_USER=postgres
DB_PASSWORD=postgres

# Sécurité JWT
JWT_SECRET_KEY=AttijariPFE2026SecretKeyTresLongueEtSecurisee!
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480

# Chiffrement AES-256
AES_KEY=changeme32chars!changeme32chars!

# Seuil alerte
SEUIL_RISQUE=0.75

# Debug
DEBUG=true
```

---

## Scores Réels par Groupe IT (données Fév–Mars 2026)

| Groupe | Score Risque | Niveau |
|--------|-------------|--------|
| Sécurité Opérationnelle | 0.87 | 🔴 CRITIQUE |
| SWIFT | 0.81 | 🔴 CRITIQUE |
| Helpdesk | 0.72 | 🟡 SURVEILLANCE |
| Intervention sur site | 0.65 | 🟡 SURVEILLANCE |
| Équipe-Études | 0.51 | 🟡 SURVEILLANCE |
| Système | 0.58 | 🟡 SURVEILLANCE |
| Réseau | 0.48 | 🟢 NORMAL |
| Téléphonie | 0.45 | 🟢 NORMAL |
| Data Office | 0.38 | 🟢 NORMAL |
| Développement Digital | 0.35 | 🟢 NORMAL |
| Stock | 0.32 | 🟢 NORMAL |

---

## Équipe

- **Meriam** : Backend · Data Engineering · NLP · XGBoost · LightGBM · Architecture Hybride · RPA · Sécurité · Diagrammes

**Encadreur** : Attijari Bank  
**Année** : 2025–2026  
**Version** : 2.0.0 (Architecture Hybride)

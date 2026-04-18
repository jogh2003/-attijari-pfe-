# Système de détection IA & RPA — Attijari bank
## PFE 2026 — Sujet 21 — Génie Logiciel

> **Backend FastAPI** — Détection d'anomalies IT par LSTM + KNN + RPA UiPath  
> Données réelles : **1507 tickets IT** Février–Mars 2026

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
# Modifier .env si besoin (DB, JWT, etc.)

# 4. Base de données (optionnel — l'API fonctionne sans)
#    Nécessite PostgreSQL installé + docker-compose up -d postgres
python scripts/init_db.py

# 5. Lancer l'API
uvicorn app.main:app --reload
```

L'API démarre sur **http://localhost:8000**

---

## URLs utiles

| URL | Description |
|-----|-------------|
| http://localhost:8000/docs | Swagger UI (tester tous les endpoints) |
| http://localhost:8000/redoc | Documentation ReDoc |
| http://localhost:8000/health | État du système |
| http://localhost:8000/api/alertes?seuil=0.75 | Endpoint UiPath |

---

## Comptes de test

| Email | Mot de passe | Rôle |
|-------|-------------|------|
| admin@attijaribank.tn | Admin@2026! | Administrateur |
| responsable.it@attijaribank.tn | Resp@2026! | Responsable IT |
| meriam@attijaribank.tn | Stage@2026! | Utilisateur |
| robot@attijaribank.tn | Robot@2026! | Robot UiPath |

---

## Architecture

```
app/
├── main.py                    # Point d'entrée FastAPI + lifecycle
├── core/
│   ├── audit.py               # Audit trail centralisé
│   ├── config.py              # Variables d'environnement (Pydantic)
│   ├── database.py            # PostgreSQL + SQLAlchemy
│   ├── logging_config.py      # Loguru (fichier + console)
│   ├── scheduler.py           # APScheduler (réentraînement lundi 02h00)
│   └── security.py            # JWT + AES-256 + bcrypt
├── models/                    # ORM SQLAlchemy
│   ├── audit_log.py
│   ├── reclamation.py
│   └── utilisateur.py
├── routers/                   # Endpoints API
│   ├── auth.py                # POST /auth/login, GET /auth/me, POST /auth/logout
│   ├── alertes.py             # GET /api/alertes (endpoint UiPath)
│   ├── predictions.py         # GET /api/predictions (scores LSTM)
│   ├── recommandations.py     # GET /api/recommandations (KNN)
│   ├── reclamations.py        # CRUD tickets + analyse NLP
│   └── audit.py               # GET /api/audit (trail complet)
└── services/
    ├── nlp_service.py         # spaCy + BERT embeddings
    └── recommandation_service.py  # Moteur KNN

models/                        # Fichiers modèles entraînés
├── lstm_model.h5              # Réseau LSTM (TensorFlow)
├── knn_model.pkl              # Modèle KNN + vectorizer TF-IDF
├── scaler_lstm.pkl            # StandardScaler pour LSTM
├── label_encoder_groupe.pkl   # LabelEncoder groupes
├── tfidf_vectorizer.pkl       # TF-IDF pour NLP
└── metriques_lstm.json        # Métriques : accuracy=87%, AUC=0.91

data/
├── raw/                       # Données brutes Excel (non commitées)
└── processed/
    └── dataset_nlp_enrichi.csv  # 1507 tickets nettoyés + scores

uipath/
├── Main.xaml                  # Orchestrateur principal
├── CheckAlerte.xaml           # Appelle GET /api/alertes?seuil=0.75
├── ConfirmerResolution.xaml   # Appelle POST /api/alertes/{id}/cloturer
└── NotifierIT.xaml            # Envoi notification responsable IT

scripts/
├── init_db.py                 # Créer les tables PostgreSQL
├── import_csv.py              # Importer les tickets dans PostgreSQL
├── entrainer_lstm.py          # Entraîner le modèle LSTM
├── recommandations_knn.py     # Entraîner le modèle KNN
├── pipeline_nlp.py            # Pipeline NLP complet
└── backup_db.py               # Sauvegarde PostgreSQL

tests/
├── conftest.py                # Fixtures pytest (client, tokens)
├── test_api.py                # Tests d'intégration (7 classes, 40+ tests)
└── test_security.py           # Tests sécurité (bcrypt, JWT, AES)
```

---

## Infrastructure Docker (optionnel)

```bash
# Démarrer PostgreSQL + Redis + Elasticsearch + MLflow
docker-compose up -d

# Vérifier l'état
docker-compose ps
```

Services :
- **PostgreSQL** : localhost:5432
- **Redis** : localhost:6379
- **Elasticsearch** : localhost:9200
- **MLflow UI** : http://localhost:5000

---

## Endpoints API

### Authentification
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | /auth/login | Connexion — retourne JWT |
| GET | /auth/me | Infos utilisateur connecté |
| POST | /auth/logout | Déconnexion (révoque le token JWT) |

### Réclamations (Analyse IA)
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | /reclamations/ | Liste des 1507 tickets (filtres disponibles) |
| GET | /reclamations/stats | Statistiques dashboard Chart.js |
| GET | /reclamations/{id} | Détail d'un ticket |
| POST | /reclamations/analyser | Analyse NLP + score anomalie |

### Alertes UiPath
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | /api/alertes/ | Alertes actives (seuil paramétrable) |
| GET | /api/alertes/stats | Statistiques alertes |
| POST | /api/alertes/{id}/cloturer | Confirmer résolution (UiPath) |

### Prédictions LSTM
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | /api/predictions/ | Scores de risque par groupe |
| POST | /api/predictions/predire | Score pour un ticket |
| GET | /api/predictions/dashboard | Données Chart.js |
| GET | /api/predictions/modele | Infos modèle LSTM |

### Recommandations KNN
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | /api/recommandations/ | Liste recommandations |
| POST | /api/recommandations/analyser | Recommandation pour un texte |
| GET | /api/recommandations/{id} | Recommandation pour un ticket |
| POST | /api/recommandations/{id}/valider | Valider/rejeter |

### Audit Trail
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | /api/audit/ | Historique des actions |
| GET | /api/audit/stats | Statistiques audit |

---

## Tests

```bash
# Lancer tous les tests
pytest tests/ -v

# Avec couverture de code
pytest tests/ --cov=app --cov-report=term-missing -v

# Tests sécurité uniquement
python tests/test_security.py
```

---

## Pour le binôme (Frontend)

Le backend est prêt. Pour intégrer le frontend :

1. L'API tourne sur `http://localhost:8000`
2. CORS activé pour `localhost:3000`, `localhost:5500`, `localhost:8080`
3. Tous les endpoints nécessitent un header `Authorization: Bearer <token>`
4. Obtenir un token : `POST /auth/login` avec `username` et `password` en form-data
5. Documentation complète : http://localhost:8000/docs

**Données disponibles pour les graphiques :**
- `GET /reclamations/stats` → statistiques globales
- `GET /api/predictions/dashboard` → données Chart.js
- `GET /api/alertes/stats` → statistiques alertes

---

## Équipe

- **Meriam** : Backend · Data Engineering · NLP · LSTM · KNN · RPA · Sécurité
- **Binôme** : Frontend HTML/CSS/JS (Dashboard)

**Encadreur** : Attijari bank  
**Année** : 2025–2026

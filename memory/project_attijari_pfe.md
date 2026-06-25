---
name: Projet PFE Attijari bank — Sujet 21
description: Système IA & RPA pour détection d'anomalies sur tickets IT — FastAPI + LSTM + KNN + UiPath
type: project
---

Projet de fin d'études (PFE) développé pour Attijari bank Tunisie.
Détecte les anomalies sur 1507 tickets IT réels (Février–Mars 2026) et déclenche des actions RPA via UiPath.

**Why:** PFE académique, présentation soutenance à venir.
**How to apply:** Garder le code simple, orienté démonstration. Les données sont réelles (confidentielles).

## Stack technique
- **Backend** : FastAPI + Uvicorn
- **ML** : LSTM (TensorFlow) + KNN (scikit-learn) + TF-IDF + BERT (sentence-transformers)
- **NLP** : spaCy + BERT embeddings
- **DB** : PostgreSQL (SQLAlchemy) — schema dans `scripts/init_db.py`
- **Sécurité** : JWT (python-jose) + AES-256 (Fernet) + bcrypt
- **RPA** : UiPath — endpoint principal `GET /api/alertes?seuil=0.75`
- **Config** : python-dotenv + pydantic-settings

## Structure clé
- `app/main.py` — Point d'entrée FastAPI, 6 routers
- `app/routers/alertes.py` — Endpoint UiPath CheckAlerte.xaml
- `app/routers/auth.py` — JWT auth, 4 utilisateurs en mémoire
- `app/core/config.py` — Settings depuis .env (pydantic-settings)
- `app/core/database.py` — Connexion PostgreSQL via DATABASE_URL env var
- `models/` — knn_model.pkl, lstm_model.h5, scaler, label_encoder
- `data/cleaned/reclamations_propres.csv` — 1507 tickets nettoyés
- `data/processed/dataset_nlp_enrichi.csv` — enrichi NLP (NER + scores)

## Démarrage
```
python scripts/init_db.py        # Créer les tables PostgreSQL
python scripts/import_csv.py     # Importer 1507 tickets
uvicorn app.main:app --reload    # Lancer l'API
```
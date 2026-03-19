# Système de détection IA & RPA — Attijari bank
## PFE 2026 — Sujet 21 — Génie Logiciel

### Démarrage rapide
```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env          # puis remplir .env
docker-compose up -d          # Elasticsearch + Redis + MLflow
python scripts/init_db.py     # créer les tables
uvicorn app.main:app --reload # lancer l'API
```

### URLs
- API Swagger : http://localhost:8000/docs
- MLflow UI   : http://localhost:5000

### Équipe
- **Vous** : Backend · Data · NLP · LSTM · RPA · Sécurité
- **Binôme** : Frontend HTML/CSS/JS

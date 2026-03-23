#!/bin/bash
# ============================================================
# Script d'installation — PFE Attijari bank — Sujet 21
# Exécuter dans le terminal VS Code : bash setup.sh
# ============================================================

echo "======================================"
echo "  Setup PFE Attijari bank — Sujet 21 "
echo "======================================"

# 1. Créer l'environnement virtuel Python
echo "[1/6] Création de l'environnement virtuel Python..."
python -m venv venv
source venv/bin/activate  # Linux/Mac
# Pour Windows : venv\Scripts\activate

# 2. Installer les dépendances
echo "[2/6] Installation des bibliothèques Python..."
pip install --upgrade pip
pip install -r requirements.txt

# 3. Télécharger les modèles spaCy
echo "[3/6] Téléchargement des modèles spaCy..."
python -m spacy download fr_core_news_md
python -m spacy download en_core_web_md

# 4. Créer le fichier .env
echo "[4/6] Création du fichier .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  -> .env créé depuis .env.example — pensez à le remplir !"
fi

# 5. Créer la base de données PostgreSQL
echo "[5/6] Initialisation de la base de données..."
python scripts/init_db.py

# 6. Vérification finale
echo "[6/6] Vérification de l'installation..."
python scripts/check_setup.py

echo ""
echo "======================================"
echo "  Installation terminée !"
echo "  Lancer l'API : uvicorn app.main:app --reload"
echo "  Lancer MLflow : mlflow ui"
echo "  Lancer Jupyter : jupyter notebook"
echo "======================================"

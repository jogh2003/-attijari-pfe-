"""
entrainer_knn.py - Entraînement KNN de similarité
Sortie : models/knn_model.pkl (dict avec keys: knn, vectorizer, df)
"""
import os
import pickle
import sys
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

DATA_PATHS = [
    "data/processed/dataset_nlp_enrichi.csv",
    "data/processed/dataset_nlp.csv",
    "data/cleaned/reclamations_propres.csv",
]
OUT = "models/knn_model.pkl"

os.makedirs("models", exist_ok=True)


def charger_donnees():
    for p in DATA_PATHS:
        if os.path.exists(p):
            try:
                df = pd.read_csv(p, on_bad_lines='skip')
                print(f"[DATA] {len(df)} tickets chargés depuis {p}")
                return df
            except Exception as e:
                print(f"[ERR] Lecture {p} : {e}")
    print("[ERREUR] Aucun fichier de données pour KNN", file=sys.stderr)
    sys.exit(1)


def preparer_texte(df):
    df = df.copy()
    # Construire un texte combiné similaire à celui utilisé ailleurs
    df['texte_combined'] = (
        df.get('description', pd.Series('')).fillna('').astype(str) + ' ' +
        df.get('objet', pd.Series('')).fillna('').astype(str) + ' ' +
        df.get('type_operation', pd.Series('')).fillna('').astype(str) + ' ' +
        df.get('categorie', pd.Series('')).fillna('').astype(str)
    ).str.strip()
    # Garantir colonnes nécessaires
    if 'action_effectuee' not in df.columns:
        df['action_effectuee'] = df.get('action_label', '')
    return df


if __name__ == '__main__':
    df = charger_donnees()
    df = preparer_texte(df)
    textes = df['texte_combined'].fillna('').astype(str).tolist()

    print("[VEC] Entraînement TF-IDF pour KNN...")
    vec = TfidfVectorizer(max_features=500, ngram_range=(1,2), min_df=2)
    X = vec.fit_transform(textes)
    print(f"[VEC] Vocabulaire={len(vec.vocabulary_)} features")

    n_neighbors = min(10, X.shape[0] - 1) if X.shape[0] > 1 else 1
    print(f"[KNN] Entraînement KNN (n_neighbors={n_neighbors})")
    knn = NearestNeighbors(n_neighbors=n_neighbors, metric='cosine', n_jobs=-1)
    knn.fit(X)

    bundle = {
        'vectorizer': vec,
        'knn': knn,
        'df': df.reset_index(drop=True),
    }

    pickle.dump(bundle, open(OUT, 'wb'))
    print(f"[SAVE] KNN bundle sauvegardé -> {OUT}")
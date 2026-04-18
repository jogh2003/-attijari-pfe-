"""
recommandations_knn.py — Moteur de recommandations KNN sur données réelles
PFE Attijari bank — Sujet 21

Utilise les embeddings BERT et la colonne 'action_effectuee' (= Résolution)
pour recommander l'action corrective la plus adaptée à un nouveau ticket.
"""
import pandas as pd
import numpy as np
import os
import json
import pickle
from collections import Counter
from sklearn.neighbors import NearestNeighbors
from sklearn.feature_extraction.text import TfidfVectorizer

os.makedirs("models", exist_ok=True)

def charger_donnees_et_embeddings():
    """Charge le dataset NLP et les embeddings BERT"""
    nlp_path  = "data/processed/dataset_nlp_enrichi.csv"
    emb_path  = "data/processed/embeddings_bert.npy"
    clean_path = "data/cleaned/reclamations_propres.csv"

    if os.path.exists(nlp_path):
        df = pd.read_csv(nlp_path, on_bad_lines='skip')
    elif os.path.exists(clean_path):
        df = pd.read_csv(clean_path, on_bad_lines='skip')
    else:
        print("ERREUR : dataset introuvable.")
        exit(1)

    # Sécurité : convertir les actions en chaînes de caractères pour éviter l'erreur 'float'
    df['action_effectuee'] = df['action_effectuee'].fillna("Action non spécifiée").astype(str)
    print(f"Dataset chargé : {len(df)} tickets")

    # Initialiser le vectorizer pour le fallback ou la sauvegarde
    textes = (df['description'].fillna('') + ' ' + df['type_operation'].fillna('')).tolist()
    vec = TfidfVectorizer(max_features=128, min_df=1)

    if os.path.exists(emb_path):
        embeddings = np.load(emb_path)
        vec.fit(textes) # On entraîne pour avoir le vocabulaire dans le .pkl
        print(f"Embeddings chargés : {embeddings.shape}")
    else:
        print("Embeddings non trouvés — génération TF-IDF fallback...")
        embeddings = vec.fit_transform(textes).toarray().astype(np.float32)
        np.save(emb_path, embeddings)
        print(f"Embeddings TF-IDF générés : {embeddings.shape}")

    return df, embeddings, vec

def construire_et_sauvegarder_knn(df, embeddings, k=5):
    """Construit le modèle KNN sur les embeddings"""
    print(f"\nConstruction du modèle KNN (k={k})...")

    knn = NearestNeighbors(
        n_neighbors=k,
        metric='cosine',
        algorithm='brute'
    )
    knn.fit(embeddings)
    return knn

def recommander(texte_requete, knn, df, vec, k=5):
    """Recommande une action corrective"""
    vecteur = vec.transform([texte_requete]).toarray()
    distances, indices = knn.kneighbors(vecteur)
    
    actions_similaires = [df.iloc[i]['action_effectuee'] for i in indices[0]]
    compteur = Counter(actions_similaires)
    action_principale = compteur.most_common(1)[0][0]
    taux_succes = compteur.most_common(1)[0][1] / k

    return {
        "action_suggeree": action_principale,
        "taux_succes": round(taux_succes, 2),
        "nb_cas_similaires": k,
        "priorite": 1 if taux_succes >= 0.7 else 2
    }

def analyser_actions_disponibles(df):
    """Analyse les actions pour les logs"""
    print("\n" + "=" * 60)
    print("  ANALYSE DES ACTIONS CORRECTIVES DISPONIBLES")
    print("=" * 60)
    actions = df[df['action_effectuee'] != "Action non spécifiée"]['action_effectuee']
    compteur = Counter(actions.tolist())
    print(f"  Actions distinctes : {len(compteur)}")
    print("\n  Top 5 actions :")
    for action, count in compteur.most_common(5):
        pct = count / len(df) * 100
        print(f"    {count:5d} ({pct:.1f}%)  {str(action)[:70]}")

# ── MAIN ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  Moteur KNN — Recommandations — Attijari bank 2026")
    print("=" * 60)

    # 1. Charger les données et le vectorizer
    df, embeddings, vec = charger_donnees_et_embeddings()

    # 2. Analyse visuelle
    analyser_actions_disponibles(df)

    # 3. Entraîner le modèle
    knn = construire_et_sauvegarder_knn(df, embeddings, k=5)

    # 4. SAUVEGARDE STRICTE (pour verifier_et_entrainer.py)
    modele_a_sauvegarder = {
        'knn': knn,           # Modèle entraîné
        'vectorizer': vec,    # Vectorizer pour transformer les inputs de l'API
        'df': df              # Dataframe pour mapper les index aux textes
    }

    with open('models/knn_model.pkl', 'wb') as f:
        pickle.dump(modele_a_sauvegarder, f)

    print("\n✓ Modèle KNN sauvegardé avec succès avec les clés ['knn', 'vectorizer', 'df']")

    # 5. Tests rapides
    print("\nTEST RAPIDE :")
    test_ticket = "Problème d'accès au portail e-banking"
    resultat = recommander(test_ticket, knn, df, vec)
    print(f"Ticket: {test_ticket}\nSuggéré: {resultat['action_suggeree']}")

    print("\n" + "=" * 60)
    print("  KNN TERMINÉ — PRÊT POUR L'API")
    print("=" * 60)
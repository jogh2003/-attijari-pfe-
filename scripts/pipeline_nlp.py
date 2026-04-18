"""
pipeline_nlp.py — Pipeline NLP complet sur données réelles Attijari bank
PFE Sujet 21

Traitement : Objet + Description → spaCy NER → BERT embeddings → score anomalie
Exécuter   : python scripts/pipeline_nlp.py
"""
import pandas as pd
import numpy as np
import os
import json
import pickle
from datetime import datetime

os.makedirs("data/processed", exist_ok=True)
os.makedirs("models", exist_ok=True)

def charger_donnees():
    path = "data/cleaned/reclamations_propres.csv"
    if not os.path.exists(path):
        print("ERREUR : lancer d'abord import_et_nettoyage.py")
        exit(1)
    df = pd.read_csv(path, on_bad_lines='skip')
    print(f"Données chargées : {len(df)} tickets")
    return df

def charger_spacy():
    """Charge le modèle spaCy français"""
    import spacy
    try:
        nlp = spacy.load("fr_core_news_md")
        print("  Modèle spaCy fr_core_news_md chargé")
    except OSError:
        print("  Téléchargement modèle spaCy...")
        os.system("python -m spacy download fr_core_news_md")
        nlp = spacy.load("fr_core_news_md")
    return nlp

def extraire_entites(texte: str, nlp) -> dict:
    """
    Extrait les entités nommées d'un texte de ticket IT
    Adapté au vocabulaire réel Attijari bank :
    - Systèmes : SWIFT, Amplitude, IDC, Outlook, VPN
    - Erreurs  : blocage, timeout, problème, anomalie
    - Lieux    : agence, région
    """
    if not texte or len(texte) < 3:
        return {"tokens": [], "entites": [], "systemes": [], "erreurs": []}

    doc = nlp(texte[:500])  # Limiter à 500 chars pour performance

    # Entités NER standard
    entites = [(ent.text, ent.label_) for ent in doc.ents]

    # Tokens importants (sans stopwords ni ponctuation)
    tokens = [t.lemma_.lower() for t in doc
              if not t.is_stop and not t.is_punct and len(t.text) > 2]

    # Systèmes bancaires détectés
    systemes_connus = [
        "swift", "amplitude", "idc", "outlook", "vpn", "firewall",
        "editique", "nmr", "tanit", "réseau", "serveur", "application",
        "imprimante", "western union", "digital", "messagerie"
    ]
    texte_lower = texte.lower()
    systemes = [s for s in systemes_connus if s in texte_lower]

    # Types d'erreurs détectés
    erreurs_connus = [
        "problème", "blocage", "erreur", "anomalie", "panne",
        "authentification", "accès", "timeout", "spam", "compromission"
    ]
    erreurs = [e for e in erreurs_connus if e in texte_lower]

    return {
        "tokens": tokens[:15],
        "entites": entites[:10],
        "systemes": systemes[:5],
        "erreurs": erreurs[:5]
    }

def calculer_score_anomalie_simple(row) -> float:
    """
    Calcule un score d'anomalie basé sur des règles métier
    (utilisé avant que le modèle LSTM soit entraîné)

    Facteurs :
    - Priorité : Haute = +0.3, Moyenne = +0.1
    - En retard SLA : +0.25
    - Groupe Sécurité : +0.2
    - Présence d'erreurs critiques dans le texte : +0.15
    - Durée de résolution longue : +0.1
    """
    score = 0.2  # Base

    # Priorité
    if row.get('severite') == 1:    score += 0.30
    elif row.get('severite') == 2:  score += 0.10

    # En retard SLA
    if row.get('en_retard') == True:  score += 0.25

    # Groupe sécurité = plus critique
    groupe = str(row.get('type_operation', '')).lower()
    if 'sécurité' in groupe or 'securite' in groupe:
        score += 0.20
    elif 'swift' in groupe:
        score += 0.15

    # Durée de résolution longue (> 60 min = 1h)
    duree = float(row.get('duree_resolution_min', 0) or 0)
    if duree > 120:    score += 0.10
    elif duree > 300:  score += 0.20

    # Erreurs critiques dans l'objet
    objet = str(row.get('objet', '')).lower()
    mots_critiques = ['compromission', 'blocage', 'spam', 'authentification', 'accès']
    if any(m in objet for m in mots_critiques):
        score += 0.10

    return round(min(score, 0.99), 3)

def generer_embeddings_bert(textes: list) -> np.ndarray:
    """Génère les embeddings BERT pour une liste de textes"""
    try:
        from sentence_transformers import SentenceTransformer
        print("  Chargement modèle BERT (paraphrase-multilingual-MiniLM-L12-v2)...")
        model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        print(f"  Génération embeddings pour {len(textes)} textes...")
        embeddings = model.encode(textes, batch_size=64, show_progress_bar=True)
        print(f"  Embeddings générés : shape {embeddings.shape}")
        return embeddings
    except ImportError:
        print("  sentence-transformers non disponible — pip install sentence-transformers")
        print("  Utilisation d'embeddings TF-IDF comme fallback...")
        from sklearn.feature_extraction.text import TfidfVectorizer
        vec = TfidfVectorizer(max_features=128, min_df=2)
        return vec.fit_transform(textes).toarray().astype(np.float32)
    except Exception as e:
        print(f"  Erreur BERT : {e} — utilisation TF-IDF")
        from sklearn.feature_extraction.text import TfidfVectorizer
        vec = TfidfVectorizer(max_features=128, min_df=2)
        return vec.fit_transform(textes).toarray().astype(np.float32)

def calculer_similarite_cosinus(v1: np.ndarray, v2: np.ndarray) -> float:
    """Similarité cosinus entre deux vecteurs"""
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(v1, v2) / (norm1 * norm2))

def traiter_pipeline_nlp():
    print("=" * 60)
    print("  Pipeline NLP — Attijari bank 2026")
    print("=" * 60)

    df = charger_donnees()

    # ── 1. Préparer le texte combiné ─────────────────────────
    print("\n[1/5] Préparation des textes...")
    df['texte_complet'] = (df['objet'].fillna('') + ' ' +
                           df['categorie'].fillna('') + ' ' +
                           df['sous_categorie'].fillna(''))
    df['texte_complet'] = df['texte_complet'].str.strip()
    print(f"  Textes préparés : {len(df)}")
    print(f"  Longueur moyenne : {df['texte_complet'].str.len().mean():.0f} chars")

    # ── 2. Extraction entités spaCy ──────────────────────────
    print("\n[2/5] Extraction entités NER avec spaCy...")
    try:
        nlp = charger_spacy()
        resultats_nlp = []
        for i, row in df.iterrows():
            result = extraire_entites(row['texte_complet'], nlp)
            resultats_nlp.append(result)
            if i % 200 == 0:
                print(f"  Traité : {i}/{len(df)}")

        df['tokens']   = [r['tokens'] for r in resultats_nlp]
        df['entites']  = [r['entites'] for r in resultats_nlp]
        df['systemes'] = [r['systemes'] for r in resultats_nlp]
        df['erreurs']  = [r['erreurs'] for r in resultats_nlp]
        print(f"  Extraction NER terminée")

    except Exception as e:
        print(f"  spaCy non disponible ({e}) — utilisation extraction par règles")
        df['tokens']   = df['texte_complet'].str.lower().str.split()
        df['systemes'] = df['texte_complet'].apply(lambda t: [
            s for s in ['swift','amplitude','firewall','vpn','outlook']
            if s in str(t).lower()
        ])
        df['erreurs']  = df['texte_complet'].apply(lambda t: [
            e for e in ['problème','blocage','erreur','spam']
            if e in str(t).lower()
        ])

    # ── 3. Score d'anomalie ───────────────────────────────────
    print("\n[3/5] Calcul des scores d'anomalie...")
    df['score_anomalie'] = df.apply(calculer_score_anomalie_simple, axis=1)
    print(f"  Score moyen     : {df['score_anomalie'].mean():.3f}")
    print(f"  Score max       : {df['score_anomalie'].max():.3f}")
    print(f"  Tickets à risque (≥0.75) : {(df['score_anomalie'] >= 0.75).sum()}")
    print(f"  Tickets surveillance (0.50-0.75) : {((df['score_anomalie'] >= 0.50) & (df['score_anomalie'] < 0.75)).sum()}")

    # ── 4. Embeddings BERT ────────────────────────────────────
    print("\n[4/5] Génération des embeddings BERT...")
    textes = df['texte_complet'].tolist()
    embeddings = generer_embeddings_bert(textes)

    # Sauvegarder les embeddings
    np.save("data/processed/embeddings_bert.npy", embeddings)
    print(f"  Embeddings sauvegardés : data/processed/embeddings_bert.npy")
    print(f"  Shape : {embeddings.shape}")

    # ── 5. Sauvegarde dataset enrichi ────────────────────────
    print("\n[5/5] Sauvegarde du dataset enrichi...")
    df_sortie = df.copy()

    # Convertir les listes en JSON pour stockage CSV
    for col in ['tokens', 'entites', 'systemes', 'erreurs']:
        if col in df_sortie.columns:
            df_sortie[col] = df_sortie[col].apply(
                lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, list) else str(x)
            )

    # Mettre à jour le score dans le dataset propre
    df_sortie.to_csv("data/processed/dataset_nlp.csv", index=False, encoding='utf-8')
    print(f"  Sauvegardé : data/processed/dataset_nlp.csv")

    # Sauvegarder la liste des IDs et scores pour le LSTM
    df[['id', 'date', 'type_operation', 'severite', 'en_retard',
        'duree_resolution_min', 'score_anomalie', 'statut']].to_csv(
        "data/processed/features_lstm.csv", index=False
    )
    print(f"  Features LSTM sauvegardées : data/processed/features_lstm.csv")

    print("\n" + "=" * 60)
    print("  RÉSULTATS NLP")
    print("=" * 60)
    print(f"  Tickets analysés       : {len(df)}")
    print(f"  Score anomalie moyen   : {df['score_anomalie'].mean():.3f}")
    print(f"  Tickets RISQUE ÉLEVÉ   : {(df['score_anomalie'] >= 0.75).sum()}")
    print(f"  Tickets SURVEILLANCE   : {((df['score_anomalie'] >= 0.50) & (df['score_anomalie'] < 0.75)).sum()}")
    print(f"  Tickets NORMAL         : {(df['score_anomalie'] < 0.50).sum()}")
    print(f"  Embeddings shape       : {embeddings.shape}")
    print("=" * 60)
    print("\nProchaine étape : python scripts/entrainer_lstm.py")

    return df, embeddings

if __name__ == "__main__":
    df, embeddings = traiter_pipeline_nlp()

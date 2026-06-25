"""
entrainer_lightgbm_reco.py - Recommandations LightGBM (remplace KNN)
PFE Attijari bank - Sujet 21

Approche : classification multi-classes supervisee
  - Input  : TF-IDF(description + objet + type_operation) + features encodees
  - Output : action corrective predite (parmi les top actions reelles)

Lancer : python scripts/entrainer_lightgbm_reco.py
Sortie : models/lgbm_reco_model.pkl
         models/metriques_lgbm_reco.json
         models/le_action.pkl
         models/vec_reco.pkl
"""
import json
import os
import pickle
import re
import sys
from collections import Counter
from datetime import datetime

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import (accuracy_score, classification_report,
                             top_k_accuracy_score)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import hstack, csr_matrix

os.makedirs("models", exist_ok=True)

DATA_PATHS   = [
    "data/processed/dataset_nlp_enrichi.csv",
    "data/cleaned/reclamations_propres.csv",
]
MODEL_OUT    = "models/lgbm_reco_model.pkl"
METRICS_OUT  = "models/metriques_lgbm_reco.json"
LE_ACTION    = "models/le_action.pkl"
VEC_RECO     = "models/vec_reco.pkl"
MIN_SAMPLES  = 3    # garder les actions avec au moins 3 occurrences
TOP_K_EVAL   = 3    # top-3 accuracy


# ── 1. Chargement donnees ────────────────────────────────────
def charger_donnees():
    for path in DATA_PATHS:
        if os.path.exists(path):
            df = pd.read_csv(path, on_bad_lines="skip")
            print(f"[DATA] {len(df)} tickets charges depuis {path}")
            return df
    print("[ERREUR] Aucun fichier trouve", file=sys.stderr)
    sys.exit(1)


# ── 2. Preparation des features ──────────────────────────────
def preparer_features(df):
    df = df.copy()

    # Nettoyer les actions
    df["action_effectuee"] = df["action_effectuee"].fillna("").astype(str).str.strip()

    # Neutraliser les réponses génériques qui ne doivent pas devenir des recommandations
    def normaliser_action_generique(action: str) -> str:
        text = action.strip()
        text_lower = text.lower()
        if re.match(r'^(nécessaire fait|necessaire fait)(\s.*)?$', text_lower):
            return "Autre - escalade support"
        if re.match(r"^(ok|oui|bien reçu|reçu|d'accord|ok merci|merci)$", text_lower):
            return "Autre - escalade support"
        return text

    df["action_effectuee"] = df["action_effectuee"].apply(normaliser_action_generique)
    df = df[df["action_effectuee"].str.len() > 5].copy()

    # Normaliser les actions peu frequentes -> "Autre"
    compteur = Counter(df["action_effectuee"].tolist())
    actions_frequentes = {a for a, n in compteur.items() if n >= MIN_SAMPLES}
    df["action_label"] = df["action_effectuee"].apply(
        lambda a: a if a in actions_frequentes else "Autre - escalade support"
    )

    nb_classes = df["action_label"].nunique()
    print(f"[CLASSES] {nb_classes} classes d'action "
          f"(min_samples={MIN_SAMPLES}, total={len(df)} tickets)")
    print(f"[CLASSES] Top 5 actions :")
    action_label_counts = Counter(df["action_label"].tolist())
    for a, n in action_label_counts.most_common(5):
        print(f"          {n:5d}x  {a[:65]}")
    if nb_classes > 0:
        top_action, top_count = action_label_counts.most_common(1)[0]
        print(f"[BASELINE] Random ~{100.0/nb_classes:.2f}% | Majority '{top_action[:40]}' ~{top_count/len(df)*100:.1f}%")

    # Texte combine : description + objet + type_operation + categorie
    df["texte_combined"] = (
        df.get("description",  pd.Series("")).fillna("").astype(str) + " " +
        df.get("objet",        pd.Series("")).fillna("").astype(str) + " " +
        df.get("type_operation", pd.Series("")).fillna("").astype(str) + " " +
        df.get("categorie",    pd.Series("")).fillna("").astype(str)
    ).str.strip()

    # TF-IDF sur le texte combine (500 features)
    vec = TfidfVectorizer(
        max_features=500,
        min_df=2,
        ngram_range=(1, 2),   # unigrams + bigrams
        sublinear_tf=True,    # log(TF) pour les grands corpus
    )
    X_tfidf = vec.fit_transform(df["texte_combined"])
    pickle.dump(vec, open(VEC_RECO, "wb"))
    print(f"[TF-IDF] Vocabulaire={len(vec.vocabulary_)} features -> {VEC_RECO}")

    # Features categoriques supplementaires
    le_groupe = LabelEncoder()
    le_cat    = LabelEncoder()
    df["type_op_enc"] = le_groupe.fit_transform(df["type_operation"].fillna("Inconnu").astype(str))
    df["cat_enc"]     = le_cat.fit_transform(df.get("categorie", pd.Series("Autre")).fillna("Autre").astype(str))
    df["severite"]    = df.get("severite", pd.Series(2)).fillna(2).astype(int)

    X_extra = csr_matrix(df[["type_op_enc", "cat_enc", "severite"]].values)
    X = hstack([X_tfidf, X_extra])

    # Encoder les labels d'action
    le_action = LabelEncoder()
    y = le_action.fit_transform(df["action_label"])
    pickle.dump(le_action, open(LE_ACTION, "wb"))
    print(f"[LABELS] {len(le_action.classes_)} classes -> {LE_ACTION}")

    return X, y, vec, le_action, len(df)


# ── 3. Entrainement LightGBM ─────────────────────────────────
def entrainer(X, y, le_action):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"[SPLIT] Train={X_train.shape[0]}  Test={X_test.shape[0]}")

    model = LGBMClassifier(
        n_estimators=300,
        learning_rate=0.1,
        max_depth=8,
        num_leaves=63,
        min_child_samples=5,
        subsample=0.8,
        colsample_bytree=0.8,
        is_unbalance=True,          # gestion desequilibre de classes
        objective="multiclass",
        num_class=len(le_action.classes_),
        metric="multi_logloss",
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )

    print("[TRAIN] Entrainement LightGBM multi-classes...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        callbacks=[],
    )

    # Evaluation
    y_pred   = model.predict(X_test)
    y_proba  = model.predict_proba(X_test)

    acc    = accuracy_score(y_test, y_pred)
    top3   = top_k_accuracy_score(y_test, y_proba, k=min(TOP_K_EVAL, len(le_action.classes_)),
                                  labels=list(range(len(le_action.classes_))))

    print(f"\n[RESULTATS]")
    print(f"  Accuracy Top-1 : {acc*100:.2f}%")
    print(f"  Accuracy Top-3 : {top3*100:.2f}%")

    # Rapport sur les classes les plus frequentes
    classes_frequentes = [c for c in le_action.classes_
                          if c != "Autre - escalade support"][:10]
    idx_freq = [list(le_action.classes_).index(c) for c in classes_frequentes]
    masque   = np.isin(y_test, idx_freq)
    if masque.sum() > 0:
        acc_freq = accuracy_score(y_test[masque], y_pred[masque])
        print(f"  Accuracy (top actions hors Autre) : {acc_freq*100:.2f}%")

    # Rapport simplifie (evite les problemes d'encodage console Windows)
    print(f"\n[RAPPORT PAR CLASSE]")
    labels_idx = sorted(set(y_test))
    for idx in labels_idx[:10]:
        nom   = le_action.classes_[idx][:45].encode('ascii', 'replace').decode()
        mask  = y_test == idx
        if mask.sum() > 0:
            prec = (y_pred[mask] == idx).sum() / max((y_pred == idx).sum(), 1)
            rec  = (y_pred[mask] == idx).sum() / mask.sum()
            print(f"  [{mask.sum():4d}]  P={prec:.2f}  R={rec:.2f}  {nom}")

    return model, acc, top3


# ── 4. Sauvegarde ─────────────────────────────────────────────
def sauvegarder(model, vec, le_action, acc, top3, n_tickets):
    bundle = {
        "model":     model,
        "vectorizer": vec,
        "le_action": le_action,
    }
    pickle.dump(bundle, open(MODEL_OUT, "wb"))
    print(f"\n[SAVE] Modele sauvegarde -> {MODEL_OUT}")

    metriques = {
        "date_entrainement": datetime.now().isoformat(),
        "modele":            "LightGBM",
        "accuracy_top1":     round(acc, 4),
        "accuracy_top3":     round(top3, 4),
        "n_tickets":         n_tickets,
        "n_classes":         len(le_action.classes_),
        "min_samples_classe": MIN_SAMPLES,
        "features":          "TF-IDF(500) + type_operation_enc + categorie_enc + severite",
        "ngram_range":       "(1,2)",
        "source":            "Donnees reelles Attijari bank Feb-Mars 2026",
    }
    json.dump(metriques, open(METRICS_OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"[SAVE] Metriques -> {METRICS_OUT}")
    return metriques


# ── Main ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  ENTRAINEMENT LIGHTGBM RECOMMANDATIONS - Attijari bank")
    print("=" * 60)

    df = charger_donnees()
    X, y, vec, le_action, n_tickets = preparer_features(df)
    model, acc, top3 = entrainer(X, y, le_action)
    metriques = sauvegarder(model, vec, le_action, acc, top3, n_tickets)

    print("\n" + "=" * 60)
    print(f"  LightGBM entraine - Top1={acc*100:.1f}%  Top3={top3*100:.1f}%")
    print(f"  Modele -> {MODEL_OUT}")
    print("=" * 60)

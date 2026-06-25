"""
entrainer_xgboost.py - Entraînement XGBoost (remplace LSTM)
PFE Attijari bank - Sujet 21

Lancer : python scripts/entrainer_xgboost.py
Sortie : models/xgb_model.pkl + models/metriques_xgb.json
"""
import json
import os
import pickle
import sys
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, roc_auc_score)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

# ── Chemins ───────────────────────────────────────────────────
DATA_PATHS = [
    "data/processed/dataset_nlp_enrichi.csv",
    "data/cleaned/reclamations_propres.csv",
]
MODEL_OUT    = "models/xgb_model.pkl"
METRICS_OUT  = "models/metriques_xgb.json"
LE_GROUPE    = "models/label_encoder_groupe.pkl"
LE_CAT       = "models/label_encoder_categorie.pkl"

os.makedirs("models", exist_ok=True)


# ── 1. Chargement données ────────────────────────────────────
def charger_donnees() -> pd.DataFrame:
    for path in DATA_PATHS:
        if os.path.exists(path):
            df = pd.read_csv(path, on_bad_lines="skip")
            print(f"[DATA] {len(df)} tickets chargés depuis {path}")
            return df
    print("[ERREUR] Aucun fichier de données trouvé", file=sys.stderr)
    sys.exit(1)


# ── 2. Préparation des features ──────────────────────────────
def preparer_features(df: pd.DataFrame):
    """
    Features : severite, duree_resolution_min, score_anomalie,
               score_risque, type_operation_enc, categorie_enc
    Target   : en_retard (0/1)
    """
    df = df.copy()

    # Supprimer les lignes sans cible
    df = df.dropna(subset=["en_retard"])
    df["en_retard"] = df["en_retard"].astype(int)

    # Valeurs manquantes
    df["severite"]            = df["severite"].fillna(2).astype(int)
    df["duree_resolution_min"] = df["duree_resolution_min"].fillna(df["duree_resolution_min"].median())
    df["score_anomalie"]      = df["score_anomalie"].fillna(0.0)
    df["score_risque"]        = df["score_risque"].fillna(0.0)
    df["type_operation"]      = df["type_operation"].fillna("Inconnu").astype(str)
    df["categorie"]           = df["categorie"].fillna("Autre").astype(str)

    # Encodage type_operation
    le_groupe = LabelEncoder()
    df["type_operation_enc"] = le_groupe.fit_transform(df["type_operation"])
    pickle.dump(le_groupe, open(LE_GROUPE, "wb"))
    print(f"[ENCODE] {len(le_groupe.classes_)} groupes encodés -> {LE_GROUPE}")

    # Encodage categorie
    le_cat = LabelEncoder()
    df["categorie_enc"] = le_cat.fit_transform(df["categorie"])
    pickle.dump(le_cat, open(LE_CAT, "wb"))
    print(f"[ENCODE] {len(le_cat.classes_)} catégories encodées -> {LE_CAT}")

    features = [
        "severite",
        "duree_resolution_min",
        "score_anomalie",
        "score_risque",
        "type_operation_enc",
        "categorie_enc",
    ]
    X = df[features].values
    y = df["en_retard"].values

    print(f"[FEATURES] Shape X={X.shape}  |  Retards : {y.sum()}/{len(y)} ({y.mean()*100:.1f}%)")
    return X, y, features


# ── 3. Entraînement XGBoost ──────────────────────────────────
def entrainer(X, y, features):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"[SPLIT] Train={len(X_train)}  Test={len(X_test)}")

    # Calcul scale_pos_weight pour déséquilibre de classes
    neg, pos = (y_train == 0).sum(), (y_train == 1).sum()
    scale_pw  = round(neg / pos, 2) if pos > 0 else 1.0
    print(f"[CLASS] scale_pos_weight={scale_pw}  (négatifs={neg}, positifs={pos})")

    # Grille d'hyperparamètres (rapide - 3-fold CV)
    param_grid = {
        "n_estimators":     [200, 400],
        "max_depth":        [4, 6],
        "learning_rate":    [0.05, 0.1],
        "subsample":        [0.8],
        "colsample_bytree": [0.8],
    }

    base_model = XGBClassifier(
        objective="binary:logistic",
        eval_metric="auc",
        scale_pos_weight=scale_pw,
        use_label_encoder=False,
        random_state=42,
        n_jobs=-1,
    )

    print("[GRID] Recherche des meilleurs hyperparamètres (GridSearchCV 3-fold)…")
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    grid_search = GridSearchCV(
        base_model,
        param_grid,
        cv=cv,
        scoring="roc_auc",
        n_jobs=-1,
        verbose=0,
    )
    grid_search.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    model = grid_search.best_estimator_
    best_params = grid_search.best_params_
    print(f"[GRID] Meilleurs params : {best_params}")
    print(f"[GRID] Meilleur AUC CV  : {grid_search.best_score_:.4f}")

    # Évaluation sur le test set
    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)

    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)

    print(f"\n[RÉSULTATS]")
    print(f"  Accuracy  : {acc*100:.2f}%")
    print(f"  AUC-ROC   : {auc:.4f}")
    print(f"\n[RAPPORT]\n{classification_report(y_test, y_pred, target_names=['Normal','Retard'])}")
    print(f"[CONFUSION]\n{confusion_matrix(y_test, y_pred)}")

    # Importance des features
    importances = dict(zip(features, model.feature_importances_.tolist()))
    print(f"\n[IMPORTANCE FEATURES]")
    for feat, imp in sorted(importances.items(), key=lambda x: -x[1]):
        print(f"  {feat:<25} {imp:.4f}")

    return model, acc, auc, best_params, importances


# ── 4. Sauvegarde ─────────────────────────────────────────────
def sauvegarder(model, acc, auc, best_params, importances, features, n_train, n_test):
    pickle.dump(model, open(MODEL_OUT, "wb"))
    print(f"\n[SAVE] Modèle sauvegardé -> {MODEL_OUT}")

    metriques = {
        "date_entrainement":  datetime.now().isoformat(),
        "modele":             "XGBoost",
        "accuracy":           round(acc, 4),
        "auc":                round(auc, 4),
        "n_train":            int(n_train),
        "n_test":             int(n_test),
        "features":           features,
        "best_params":        best_params,
        "feature_importances": importances,
        "source":             "Données réelles Attijari bank Fév-Mars 2026",
    }
    json.dump(metriques, open(METRICS_OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"[SAVE] Métriques sauvegardées -> {METRICS_OUT}")
    return metriques


# ── Main ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  ENTRAINEMENT XGBOOST - PFE Attijari bank")
    print("=" * 55)

    df = charger_donnees()
    X, y, features = preparer_features(df)
    model, acc, auc, best_params, importances = entrainer(X, y, features)
    n_train = int(len(X) * 0.8)
    n_test  = len(X) - n_train
    metriques = sauvegarder(model, acc, auc, best_params, importances, features, n_train, n_test)

    print("\n" + "=" * 55)
    print(f"  XGBoost entraine - Accuracy={acc*100:.1f}%  AUC={auc:.3f}")
    print(f"  Modele -> {MODEL_OUT}")
    print("=" * 55)

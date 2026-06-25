"""Evaluation ML sur réclamations synthétiques sans modifier la base.

Ce script :
- charge data/cleaned/reclamations_propres.csv
- génère des réclamations similaires en mémoire
- évalue les modèles de détection, de prédiction et de recommandation
- exécute des inférences LightGBM + KNN + XGBoost sur des tickets synthétiques
"""
import os
import random
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))

from scripts.comparative_testing import load_data, run_nlp_detection, run_xgboost_prediction, run_recommendation, prepare_reco_dataset
from app.routers.predictions import _score_xgboost, PredictionRequest
from app.routers.recommandations import recommander_lgbm, recommander_knn

SYNTHETIC_SIZE = 1507
DATA_PATH = "data/cleaned/reclamations_propres.csv"
AUGMENTED_PATH = "data/cleaned/reclamations_propres_augmente.csv"
REPORT_DIR = ROOT / "reports"
REPORT_PATH = REPORT_DIR / "evaluation_tickets_synthetiques.md"

PHRASE_MODIFIERS = [
    "Demande urgente, impact service immédiat.",
    "Incident similaire déjà signalé hier.",
    "Bloquage critique du processus métier.",
    "Le problème persiste malgré plusieurs relances.",
    "Urgent : intervention requise avant la fin de la journée.",
    "Ticket prioritaire — l'activité client est impactée.",
    "Requête traitée en priorité par l'équipe IT.",
    "Souci continu sur le service, besoin d'une action rapide.",
]


def generate_similar_reclamations(df: pd.DataFrame, n: int = SYNTHETIC_SIZE, seed: int = 42) -> pd.DataFrame:
    """Génère un DataFrame synthétique à partir des tickets existants."""
    if n <= 0:
        return pd.DataFrame(columns=df.columns)

    random.seed(seed)
    valid_df, _ = prepare_reco_dataset(df)
    if len(valid_df) >= 10:
        sampled = valid_df.sample(n=n, replace=True, random_state=seed).copy()
    else:
        sampled = df.sample(n=n, replace=True, random_state=seed).copy()

    max_demande_id = 0
    if "id_demande_orig" in df.columns:
        try:
            max_demande_id = int(pd.to_numeric(df["id_demande_orig"], errors="coerce").max())
        except Exception:
            max_demande_id = 0

    synthetic_rows = []
    next_demande_id = max_demande_id + 1

    for _, row in sampled.iterrows():
        row = row.copy()
        objet = str(row.get("objet", ""))
        description = str(row.get("description", ""))
        groupe = str(row.get("type_operation", ""))
        categorie = str(row.get("categorie", ""))

        modifier = random.choice(PHRASE_MODIFIERS)
        if objet.strip():
            objet = f"{objet} — urgent"
        else:
            objet = f"Incident {groupe} - urgence"

        if description.strip():
            description = f"{description} {modifier}"
        else:
            description = f"{categorie} {modifier}"

        try:
            row["duree_resolution_min"] = float(row.get("duree_resolution_min", 240.0) or 240.0) * random.uniform(0.9, 1.1)
        except Exception:
            row["duree_resolution_min"] = float(row.get("duree_resolution_min", 240.0) or 240.0)
        try:
            row["score_anomalie"] = min(max(float(row.get("score_anomalie", 0.0) or 0.0) * random.uniform(0.95, 1.05), 0.0), 0.99)
        except Exception:
            row["score_anomalie"] = float(row.get("score_anomalie", 0.0) or 0.0)
        try:
            row["score_risque"] = min(max(float(row.get("score_risque", 0.0) or 0.0) * random.uniform(0.95, 1.05), 0.0), 0.99)
        except Exception:
            row["score_risque"] = float(row.get("score_risque", 0.0) or 0.0)

        if isinstance(row.get("severite", None), (int, float)):
            row["severite"] = int(min(max(int(row.get("severite", 2) or 2), 1), 4))

        if "id" in row:
            row["id"] = str(uuid.uuid4())
        if "id_demande_orig" in row:
            row["id_demande_orig"] = next_demande_id
            next_demande_id += 1

        row["objet"] = objet
        row["description"] = description
        row["type_operation"] = groupe
        row["categorie"] = categorie
        synthetic_rows.append(row)

    synthetic_df = pd.DataFrame(synthetic_rows)
    synthetic_df.reset_index(drop=True, inplace=True)
    return synthetic_df


def save_augmented_dataset(original: pd.DataFrame, synthetic: pd.DataFrame, filename: str) -> pd.DataFrame:
    augmented = pd.concat([original, synthetic], ignore_index=True)
    augmented.to_csv(filename, index=False)
    print(f"\n[EXPORT] Fichier CSV augmenté créé : {filename} ({len(augmented)} lignes)")
    return augmented


def format_metrics_table(results: list[dict], keys: list[str]) -> str:
    header = "| Model | " + " | ".join(k.capitalize() for k in keys) + " |"
    divider = "|---" + "|---" * len(keys) + "|"
    lines = [header, divider]
    for r in results:
        values = [f"{(r.get(k) if r.get(k) is not None else 0.0):.4f}" for k in keys]
        lines.append(f"| {r['model']} | " + " | ".join(values) + " |")
    return "\n".join(lines)


def save_evaluation_report(original_df: pd.DataFrame, synthetic_df: pd.DataFrame, augmented_df: pd.DataFrame,
                           original_nlp: list[dict], augmented_nlp: list[dict],
                           original_pred: list[dict], augmented_pred: list[dict],
                           original_reco: list[dict], augmented_reco: list[dict],
                           production_examples: list[dict]) -> str:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Rapport d'évaluation des tickets synthétiques",
        "",
        f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 1. Résumé",
        f"- Tickets originaux : {len(original_df)}",
        f"- Tickets synthétiques générés : {len(synthetic_df)}",
        f"- Tickets augmentés : {len(augmented_df)}",
        "",
        "## 2. Jeu de données synthétiques",
        "- Les tickets synthétiques sont construits par échantillonnage avec remplacement et enrichis de modificateurs de texte.",
        "- La génération conserve les principales colonnes existantes et ajuste les scores et durées de manière réaliste.",
        "",
        "## 3. Résultats de l'évaluation",
        "",
        "### 3.1 Détection NLP",
        format_metrics_table(original_nlp, ["accuracy", "precision", "recall", "f1", "roc_auc"]),
        "",
        "### 3.2 Prédiction de retard",
        format_metrics_table(original_pred, ["accuracy", "precision", "recall", "f1", "roc_auc"]),
        "",
        "### 3.3 Recommandation",
        format_metrics_table(original_reco, ["top1", "top3"]),
        "",
        "## 4. Résultats sur le jeu augmenté",
        "",
        "### 4.1 Détection NLP",
        format_metrics_table(augmented_nlp, ["accuracy", "precision", "recall", "f1", "roc_auc"]),
        "",
        "### 4.2 Prédiction de retard",
        format_metrics_table(augmented_pred, ["accuracy", "precision", "recall", "f1", "roc_auc"]),
        "",
        "### 4.3 Recommandation",
        format_metrics_table(augmented_reco, ["top1", "top3"]),
        "",
        "## 5. Comparaison Original vs Augmenté",
        "",
        "### 5.1 Détection NLP",
        format_metrics_table([
            {"model": f"{r['model']} (original)", **r} for r in original_nlp
        ] + [
            {"model": f"{r['model']} (augmenté)", **r} for r in augmented_nlp
        ], ["accuracy", "precision", "recall", "f1", "roc_auc"]),
        "",
        "### 5.2 Prédiction de retard",
        format_metrics_table([
            {"model": f"{r['model']} (original)", **r} for r in original_pred
        ] + [
            {"model": f"{r['model']} (augmenté)", **r} for r in augmented_pred
        ], ["accuracy", "precision", "recall", "f1", "roc_auc"]),
        "",
        "### 5.3 Recommandation",
        format_metrics_table([
            {"model": f"{r['model']} (original)", **r} for r in original_reco
        ] + [
            {"model": f"{r['model']} (augmenté)", **r} for r in augmented_reco
        ], ["top1", "top3"]),
        "",
        "## 6. Exemples de tickets synthétiques",
        "",
    ]

    for i, row in synthetic_df.head(5).iterrows():
        description = str(row.get('description'))
        description = description.replace('\n', ' ')[:240]
        lines += [
            f"### Ticket synthétique {i + 1}",
            f"- type_operation : {row.get('type_operation')}",
            f"- categorie : {row.get('categorie')}",
            f"- en_retard : {row.get('en_retard')}",
            f"- objet : {row.get('objet')}",
            f"- description : {description}",
            f"- score_anomalie : {row.get('score_anomalie')}",
            f"- score_risque : {row.get('score_risque')}",
            "",
        ]

    if production_examples:
        lines += ["## 7. Inférences de production sur tickets synthétiques", ""]
        for example in production_examples:
            lines += [
                f"- Ticket {example['ticket_id']} : groupe={example['type_operation']} categorie={example['categorie']} severite={example['severite']}",
                f"  - score_risque={example['score']} version={example['version']}",
                f"  - action_LGBM={example['lgbm_action']}",
                f"  - action_KNN={example['knn_action']}",
                "",
            ]

    lines += [
        "## 8. Conclusions",
        "- L’augmentation a permis de comparer les performances des modèles sur des tickets originaux et synthétiques.",
        "- Le fichier CSV généré est disponible dans `data/cleaned/reclamations_propres_augmente.csv`.",
        "",
    ]

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[REPORT] Rapport d'évaluation créé : {REPORT_PATH}")
    return str(REPORT_PATH)


def print_metric_comparison(title: str, original: list[dict], augmented: list[dict], keys: list[str]) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    print(f"{'Model':30s} | {'Original':>12s} | {'Augmented':>12s} | {'Delta':>8s}")
    print('-' * 72)
    for old, new in zip(original, augmented):
        if old['model'] != new['model']:
            continue
        for key in keys:
            old_val = old.get(key, 0.0) or 0.0
            new_val = new.get(key, 0.0) or 0.0
            delta = new_val - old_val
            print(f"{old['model']:30s} | {old_val:12.4f} | {new_val:12.4f} | {delta:8.4f}  ({key})")
    print()


def sample_preview(df: pd.DataFrame, n: int = 3) -> None:
    print("\n--- Exemples de tickets synthétiques ---")
    for i, row in df.head(n).iterrows():
        print(f"\nTicket {i + 1} — type_operation={row.get('type_operation')} categorie={row.get('categorie')} en_retard={row.get('en_retard')}")
        print(f"Objet: {row.get('objet')}")
        print(f"Description: {str(row.get('description'))[:230]}")
        print(f"Score anomalie: {row.get('score_anomalie')} | Score risque: {row.get('score_risque')} | duree_min: {row.get('duree_resolution_min')}")


def run_production_inference(df: pd.DataFrame, n: int = 5) -> list[dict]:
    print("\n--- Inférences production XGBoost + LightGBM + KNN sur tickets synthétiques ---")
    examples = []
    for i, row in df.head(n).iterrows():
        req = PredictionRequest(
            type_operation=str(row.get("type_operation", "")) or "Helpdesk",
            severite=int(row.get("severite", 2) or 2),
            en_retard_historique=bool(row.get("en_retard", False)),
            duree_moyenne_min=float(row.get("duree_resolution_min", 240.0) or 240.0),
            categorie=str(row.get("categorie", "")) or "Autre",
            texte=str(row.get("description", ""))[:1000],
        )
        score, version = _score_xgboost(req)
        lgbm = recommander_lgbm(req.texte or req.type_operation, req.type_operation, req.categorie or "", req.severite)
        knn = recommander_knn(req.texte or req.type_operation, req.type_operation, req.categorie or "", req.severite)

        example = {
            "ticket_id": i + 1,
            "type_operation": req.type_operation,
            "categorie": req.categorie,
            "severite": req.severite,
            "score": score,
            "version": version,
            "lgbm_action": lgbm["action_suggeree"],
            "knn_similarite": knn["similarite_moyenne"],
            "knn_action": knn["action_suggeree"],
        }
        examples.append(example)

        print(f"\nTicket {example['ticket_id']} — groupe={example['type_operation']} categorie={example['categorie']} severite={example['severite']}")
        print(f" Score risque={example['score']} (version={example['version']}) | action_LGBM={example['lgbm_action'][:120]}")
        print(f" Similarite KNN={example['knn_similarite']} | action_KNN={example['knn_action'][:120]}")

    return examples


def ensure_data_available() -> pd.DataFrame:
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Fichier introuvable : {DATA_PATH}")
    df = load_data()
    print(f"[DATA] {len(df)} tickets chargés depuis {DATA_PATH}")
    return df


if __name__ == "__main__":
    original_df = ensure_data_available()
    print("\n=== EVALUATION BASELINE SUR LES DONNEES EXISTANTES ===")
    original_nlp = run_nlp_detection(original_df)
    original_pred = run_xgboost_prediction(original_df)
    original_reco = run_recommendation(original_df)

    synthetic_df = generate_similar_reclamations(original_df, n=SYNTHETIC_SIZE)
    print(f"\n[GENERATE] {len(synthetic_df)} tickets synthétiques générés à partir des données existantes.")
    sample_preview(synthetic_df, n=4)

    augmented_df = save_augmented_dataset(original_df, synthetic_df, AUGMENTED_PATH)
    print("\n=== EVALUATION SUR LE JEU AUGMENTÉ ===")
    augmented_nlp = run_nlp_detection(augmented_df)
    augmented_pred = run_xgboost_prediction(augmented_df)
    augmented_reco = run_recommendation(augmented_df)

    print_metric_comparison("COMPARAISON NLP - Original vs Augmenté", original_nlp, augmented_nlp, ["accuracy", "precision", "recall", "f1", "roc_auc"])
    print_metric_comparison("COMPARAISON PREDICTION - Original vs Augmenté", original_pred, augmented_pred, ["accuracy", "precision", "recall", "f1", "roc_auc"])
    print_metric_comparison("COMPARAISON RECOMMANDATION - Original vs Augmenté", original_reco, augmented_reco, ["top1", "top3"])

    production_examples = run_production_inference(synthetic_df, n=5)
    save_evaluation_report(
        original_df,
        synthetic_df,
        augmented_df,
        original_nlp,
        augmented_nlp,
        original_pred,
        augmented_pred,
        original_reco,
        augmented_reco,
        production_examples,
    )
    print("\nDone. Aucune base de données ni fichier source n'ont été modifiés.")

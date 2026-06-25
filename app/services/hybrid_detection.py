"""
hybrid_detection.py — Architecture Hybride de Détection (3 Niveaux)
PFE Attijari bank — Sujet 21

NIVEAU 1 — Score Anomalie (< 10ms, règles métier, explicable)
NIVEAU 2 — Confirmation XGBoost (cas complexes / zone grise)
NIVEAU 3 — Analyse temporelle (forecasting, voir /api/predictions/evolution)
"""
from typing import Optional

# ── Mots critiques identifiés dans les données réelles ────────
MOTS_CRITIQUES: dict = {
    "compromission":    0.25,
    "firewall":         0.20,
    "spam":             0.20,
    "blocage":          0.15,
    "western union":    0.15,
    "swift":            0.15,
    "authentification": 0.10,
    "timeout":          0.10,
    "erreur":           0.05,
    "ransomware":       0.30,
    "phishing":         0.25,
    "intrusion":        0.25,
    "piratage":         0.25,
    "violation":        0.20,
    "fuite":            0.20,
    "corruption":       0.15,
    "accès non autorisé": 0.20,
    "crash":            0.10,
}

# Seuils de détection
SEUIL_ALERTE_IMMEDIATE  = 0.75   # Niveau 1 → alerte sans confirmation
SEUIL_ZONE_GRISE_DEBUT  = 0.60   # Niveau 2 → XGBoost confirme
SEUIL_XGB_CONFIRMATION  = 0.70   # prob XGBoost (recalibrée) pour confirmer
SEUIL_XGB_STRICT        = 0.85   # prob XGBoost (recalibrée) même si score_anom < 0.60


def calculer_score_anomalie(description: str, type_operation: str, severite: int) -> float:
    """
    NIVEAU 1 — Score Anomalie par règles métier.
    Calcul direct en < 10ms, couvre 80 % des cas évidents.
    Explicable pour audit réglementaire bancaire.
    """
    score = 0.20  # base

    if severite == 1:
        score += 0.30
    elif severite == 2:
        score += 0.10

    desc_lower = description.lower()
    for mot, boost in MOTS_CRITIQUES.items():
        if mot in desc_lower:
            score += boost

    op_lower = type_operation.lower()
    if "sécurité" in op_lower or "securite" in op_lower:
        score += 0.20
    elif "swift" in op_lower:
        score += 0.15

    return round(min(score, 0.99), 3)


def detecter_hybride(
    description: str,
    type_operation: str,
    categorie: str = "",
    severite: int = 2,
    xgb_model=None,
    le_groupe=None,
) -> dict:
    """
    Architecture Hybride 3 niveaux — meilleur des deux mondes.

    NIVEAU 1 : Score Anomalie (règles) — < 10ms
      → score ≥ 0.75 : ALERTE_IMMEDIATE

    NIVEAU 2 : XGBoost (confirmation ou détection complexe)
      → score_anom ∈ [0.60, 0.75) + XGB ≥ 0.70 : ALERTE_CONFIRME
      → score_anom < 0.60 + XGB ≥ 0.85 : ALERTE_DETECTE_ML

    NIVEAU 3 : Analyse temporelle — voir GET /api/predictions/evolution
    """
    # ── NIVEAU 1 : Score Anomalie (rapide) ───────────────────
    score_anomalie = calculer_score_anomalie(description, type_operation, severite)

    if score_anomalie >= SEUIL_ALERTE_IMMEDIATE:
        return {
            "score_anomalie":    score_anomalie,
            "score_risque":      round(score_anomalie * 0.98, 3),
            "niveau":            "CRITIQUE",
            "alerte_declenchee": True,
            "methode_detection": "score_anomalie",
            "niveau_detection":  1,
            "label_methode":     "Niveau 1 — Score Anomalie",
            "detail":            f"Score anomalie {score_anomalie} ≥ {SEUIL_ALERTE_IMMEDIATE} → alerte immédiate (< 10ms)",
        }

    # ── NIVEAU 2 : Confirmation XGBoost ──────────────────────
    prob_xgb        = None
    prob_xgb_scaled = None

    if xgb_model is not None:
        try:
            groupe_enc = 0
            if le_groupe is not None and type_operation in le_groupe.classes_:
                groupe_enc = int(le_groupe.transform([type_operation])[0])

            features = [[
                severite,
                240.0,           # durée moyenne proxy
                score_anomalie,  # score_anomalie
                score_anomalie,  # score_risque proxy
                groupe_enc,
                0,               # categorie_enc proxy
            ]]
            prob_xgb        = float(xgb_model.predict_proba(features)[0][1])
            prob_xgb_scaled = min(prob_xgb * 4.0, 0.99)
        except Exception:
            prob_xgb = None
            prob_xgb_scaled = None

    # Cas 2a — Zone grise confirmée par XGBoost
    if (
        score_anomalie >= SEUIL_ZONE_GRISE_DEBUT
        and prob_xgb_scaled is not None
        and prob_xgb_scaled >= SEUIL_XGB_CONFIRMATION
    ):
        score_final = round(max(score_anomalie, prob_xgb_scaled * 0.90), 3)
        return {
            "score_anomalie":    score_anomalie,
            "score_risque":      score_final,
            "niveau":            "CRITIQUE",
            "alerte_declenchee": True,
            "methode_detection": "xgboost_confirmation",
            "niveau_detection":  2,
            "label_methode":     "Niveau 2 — XGBoost Confirmation",
            "detail": (
                f"Zone grise score_anom={score_anomalie} confirmée par XGBoost "
                f"(prob={round(prob_xgb, 3)}, recalibrée={round(prob_xgb_scaled, 3)})"
            ),
        }

    # Cas 2b — Cas complexe détecté uniquement par XGBoost
    if (
        score_anomalie < SEUIL_ZONE_GRISE_DEBUT
        and prob_xgb_scaled is not None
        and prob_xgb_scaled >= SEUIL_XGB_STRICT
    ):
        score_final = round(prob_xgb_scaled * 0.85, 3)
        return {
            "score_anomalie":    score_anomalie,
            "score_risque":      score_final,
            "niveau":            "SURVEILLANCE" if score_final < 0.75 else "CRITIQUE",
            "alerte_declenchee": score_final >= 0.75,
            "methode_detection": "xgboost_strict",
            "niveau_detection":  2,
            "label_methode":     "Niveau 2 — XGBoost Strict",
            "detail": (
                f"Cas complexe non détecté par règles (score_anom={score_anomalie}) "
                f"mais identifié par XGBoost (prob={round(prob_xgb, 3)})"
            ),
        }

    # ── Pas d'alerte ─────────────────────────────────────────
    niveau = "SURVEILLANCE" if score_anomalie >= 0.50 else "NORMAL"
    return {
        "score_anomalie":    score_anomalie,
        "score_risque":      round(score_anomalie * 0.95, 3),
        "niveau":            niveau,
        "alerte_declenchee": False,
        "methode_detection": "score_anomalie",
        "niveau_detection":  1,
        "label_methode":     "Niveau 1 — Score Anomalie",
        "detail":            f"Score = {score_anomalie} — en dessous du seuil d'alerte",
    }

"""
recommandations.py — Router recommandations LightGBM (remplace KNN)
PFE Attijari bank — Sujet 21
"""
import json
import os
import pickle
import uuid
from collections import Counter
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.audit import log_action
from app.core.logging_config import logger
from app.routers.auth import verifier_token

router = APIRouter()

# ── Charger les modèles LightGBM + KNN ───────────────────────
LGBM_BUNDLE  = None   # dict : model + vectorizer + le_action
LGBM_METRICS = None
LE_GROUPE    = None   # LabelEncoder groupes (pour encoder type_operation)
LE_CAT       = None   # LabelEncoder catégories
KNN_BUNDLE   = None   # dict : knn + vectorizer + df


def charger_lgbm() -> None:
    global LGBM_BUNDLE, LGBM_METRICS, LE_GROUPE, LE_CAT

    if os.path.exists("models/metriques_lgbm_reco.json"):
        LGBM_METRICS = json.load(open("models/metriques_lgbm_reco.json"))
        logger.info(
            "Metriques LightGBM Reco : Top1={:.1f}%  Top3={:.1f}%  classes={}",
            LGBM_METRICS.get("accuracy_top1", 0) * 100,
            LGBM_METRICS.get("accuracy_top3", 0) * 100,
            LGBM_METRICS.get("n_classes", 0),
        )

    if os.path.exists("models/lgbm_reco_model.pkl"):
        try:
            LGBM_BUNDLE = pickle.load(open("models/lgbm_reco_model.pkl", "rb"))
            n_classes = len(LGBM_BUNDLE["le_action"].classes_)
            logger.info("LightGBM Reco charge : {} classes d'action", n_classes)
        except Exception as exc:
            logger.warning("Erreur chargement LightGBM Reco : {}", exc)

    # Charger les encodeurs pour produire les features extras correctes
    if os.path.exists("models/label_encoder_groupe.pkl"):
        try:
            LE_GROUPE = pickle.load(open("models/label_encoder_groupe.pkl", "rb"))
        except Exception:
            pass
    if os.path.exists("models/label_encoder_categorie.pkl"):
        try:
            LE_CAT = pickle.load(open("models/label_encoder_categorie.pkl", "rb"))
        except Exception:
            pass


def charger_knn() -> None:
    global KNN_BUNDLE
    if os.path.exists("models/knn_model.pkl"):
        try:
            KNN_BUNDLE = pickle.load(open("models/knn_model.pkl", "rb"))
            if isinstance(KNN_BUNDLE, dict) and KNN_BUNDLE.get("df") is not None:
                logger.info("KNN Similarite charge : {} tickets", len(KNN_BUNDLE["df"]))
        except Exception as exc:
            logger.warning("Erreur chargement KNN : {}", exc)

try:
    charger_lgbm()
    charger_knn()
except Exception as exc:
    logger.error("Erreur chargement LightGBM/KNN Reco : {}", exc)


# ── Schémas ───────────────────────────────────────────────────
class RecommandationOut(BaseModel):
    id: str
    reclamation_id: str
    action_suggeree: str
    taux_succes: float
    nb_cas_similaires: int
    priorite: int
    statut_impl: str
    created_at: str


class ValidationRequest(BaseModel):
    decision: str
    commentaire: Optional[str] = None


class AnalyseRequest(BaseModel):
    texte: str
    groupe: Optional[str] = ""
    categorie: Optional[str] = ""
    severite: Optional[int] = 2


class RecommandationSimilaireOut(BaseModel):
    id: str
    reclamation_id: str
    action_suggeree: str
    taux_succes: float
    nb_cas_similaires: int
    similarite_moyenne: float
    incidents_similaires: List[dict]
    statut_impl: str
    created_at: str


# ── Actions invalides (données bruitées du CSV) ───────────────
# 872/1507 tickets ont "Nécessaire fait" — LightGBM l'a appris comme classe dominante
# Ces actions ne sont pas des recommandations IT exploitables
_PREFIXES_INVALIDES = (
    "nécessaire fait", "nf", "ok", "ouverte", "bdd", "traité",
    "en jointure", "merci de me contacter", "agence contacter",
    "provisoire", "r\n", "2264", "2274",
)
_ACTIONS_INVALIDES_EXACTES = {
    "nécessaire fait", "nf.", "nf", "ok", "ouverte", "bdd",
    "r", "traité", "en jointure", ".", "agence contacter",
    "provisoirebdd", "2264", "2274",
}

def _action_est_valide(action: str) -> bool:
    """Retourne True si l'action est une vraie recommandation IT exploitable."""
    a = action.strip().lower()
    if len(a) < 15:
        return False
    if a in _ACTIONS_INVALIDES_EXACTES:
        return False
    if any(a.startswith(p) for p in _PREFIXES_INVALIDES):
        return False
    return True


# ── Recommandations métier par groupe (fallback fiable) ───────
_RECOS_METIER = {
    "Sécurité Opérationnelle": [
        "Analyser les logs du firewall, isoler les IP suspectes et appliquer les règles de blocage",
        "Réinitialiser les credentials compromis et activer l'authentification multi-facteurs",
        "Escalader au CERT interne et lancer une analyse forensique du système impacté",
    ],
    "SWIFT": [
        "Purger le cache Redis monétique et redémarrer le service SWIFT",
        "Vérifier la connectivité réseau vers le hub SWIFT et contacter le prestataire",
        "Relancer le batch de transactions bloquées après vérification des logs Swift Alliance",
    ],
    "Helpdesk": [
        "Réinitialiser le mot de passe utilisateur via l'Active Directory et informer l'utilisateur",
        "Désactiver le compte suspect, analyser les logs d'authentification et notifier le RSSI",
        "Redémarrer la session VPN et vérifier les règles de pare-feu pour l'utilisateur concerné",
    ],
    "Système": [
        "Redémarrer le service Amplitude et vérifier les logs d'application",
        "Libérer l'espace disque, vider les fichiers temporaires et relancer le service",
        "Appliquer le patch correctif disponible et planifier un redémarrage en maintenance",
    ],
    "Réseau": [
        "Vérifier la configuration du switch/routeur et relancer les interfaces réseau impactées",
        "Analyser les trames réseau avec Wireshark et identifier la source de congestion",
        "Contacter le prestataire réseau et ouvrir un ticket d'incident prioritaire",
    ],
    "Téléphonie": [
        "Redémarrer le serveur IPBX et vérifier la configuration des postes téléphoniques",
        "Vérifier la liaison SIP avec l'opérateur et relancer le trunk concerné",
    ],
    "Equipe-Etudes": [
        "Analyser les spécifications techniques et planifier une réunion avec l'équipe projet",
        "Escalader au chef de projet et documenter les impacts sur le planning",
    ],
    "Développement-Digital": [
        "Analyser les logs applicatifs, identifier le bug et déployer un correctif en urgence",
        "Rollback vers la version stable précédente et ouvrir un ticket de bug dans le backlog",
    ],
    "Stock": [
        "Vérifier le stock disponible dans le système et lancer une commande de réapprovisionnement",
        "Contacter le fournisseur et mettre à jour l'inventaire dans le système de gestion",
    ],
    "Data Office": [
        "Vérifier l'intégrité des données et relancer le pipeline ETL après correction",
        "Analyser les logs du datawarehouse et contacter l'équipe Data pour investigation",
    ],
}

def _reco_fallback(groupe: str, texte: str) -> str:
    """Retourne une recommandation métier pertinente basée sur le groupe et les mots-clés."""
    texte_lower = texte.lower()
    recos = _RECOS_METIER.get(groupe, [])

    # Correspondance par mots-clés dans le texte
    mots_cles = {
        "mot de passe": "Réinitialiser le mot de passe utilisateur via l'Active Directory et informer l'utilisateur",
        "password":     "Réinitialiser le mot de passe utilisateur via l'Active Directory et informer l'utilisateur",
        "vpn":          "Redémarrer la session VPN et vérifier les règles de pare-feu pour l'utilisateur concerné",
        "firewall":     "Analyser les logs du firewall, isoler les IP suspectes et appliquer les règles de blocage",
        "swift":        "Purger le cache Redis monétique et redémarrer le service SWIFT",
        "spam":         "Désactiver le compte suspect, analyser les logs d'authentification et notifier le RSSI",
        "authentif":    "Réinitialiser les credentials compromis et activer l'authentification multi-facteurs",
        "réseau":       "Vérifier la configuration du switch/routeur et relancer les interfaces réseau impactées",
        "réseau":       "Vérifier la configuration du switch/routeur et relancer les interfaces réseau impactées",
        "amplitude":    "Redémarrer le service Amplitude et vérifier les logs d'application",
        "accès":        "Vérifier les droits d'accès dans l'Active Directory et réattribuer les permissions",
        "base de données": "Analyser les logs de la base de données et contacter l'administrateur DBA",
        "imprimante":   "Vérifier la connexion réseau de l'imprimante et réinstaller le pilote d'impression",
        "messagerie":   "Redémarrer le service de messagerie Exchange et vérifier la configuration du compte",
    }
    for mot, reco in mots_cles.items():
        if mot in texte_lower:
            return reco

    # Sinon première reco du groupe
    if recos:
        return recos[0]

    return "Analyser le ticket, contacter le groupe IT concerné et appliquer la procédure standard de résolution"


def _combiner_texte(texte: str, groupe: str, categorie: str) -> str:
    return " ".join([part.strip() for part in [texte, groupe, categorie] if part and part.strip()])


def recommander_knn(texte: str, groupe: str = "", categorie: str = "", severite: int = 2, top_n: int = 3) -> dict:
    """
    Recommande une action corrective basée sur les incidents similaires trouvés par KNN.
    Renvoie une action, une liste d'incidents proches et une confiance moyenne.
    """
    if not KNN_BUNDLE:
        return {
            "action_suggeree":   _reco_fallback(groupe, texte),
            "taux_succes":       0.60,
            "nb_cas_similaires": 0,
            "incidents_similaires": [],
            "similarite_moyenne": 0.0,
            "priorite":          2,
        }

    try:
        vec = KNN_BUNDLE["vectorizer"]
        knn = KNN_BUNDLE["knn"]
        df_knn = KNN_BUNDLE["df"]

        texte_combined = _combiner_texte(texte, groupe, categorie)
        X_text = vec.transform([texte_combined])

        distances, indices = knn.kneighbors(X_text, n_neighbors=min(top_n, len(df_knn)))
        distances = distances[0].tolist()
        indices = indices[0].tolist()

        incidents = []
        actions = []
        similarites = []

        for dist, idx in zip(distances, indices):
            row = df_knn.iloc[idx]
            action = str(row.get("action_effectuee", "")).strip()
            similarite = round(max(0.0, 1.0 - float(dist)), 3)
            similarites.append(similarite)
            incidents.append({
                "id": str(row.get("id", "")),
                "type_operation": str(row.get("type_operation", "")),
                "categorie": str(row.get("categorie", "")),
                "description": str(row.get("description", ""))[:200],
                "action_effectuee": action,
                "score_anomalie": float(row.get("score_anomalie") or 0.0),
                "score_risque": float(row.get("score_risque") or 0.0),
                "similarite": similarite,
            })
            if _action_est_valide(action):
                actions.append(action)

        if actions:
            action_principale = Counter(actions).most_common(1)[0][0]
            confiance = round(float(sum(similarites) / len(similarites) if similarites else 0.0), 2)
        else:
            action_principale = _reco_fallback(groupe, texte)
            confiance = 0.60

        return {
            "action_suggeree":   action_principale[:200],
            "taux_succes":       round(confiance, 2),
            "nb_cas_similaires": len(df_knn),
            "incidents_similaires": incidents,
            "similarite_moyenne": round(float(sum(similarites) / len(similarites) if similarites else 0.0), 3),
            "priorite":          1 if confiance >= 0.80 else 2,
        }
    except Exception as exc:
        logger.error("Erreur moteur KNN Reco : {}", exc)
        return {
            "action_suggeree":   _reco_fallback(groupe, texte),
            "taux_succes":       0.0,
            "nb_cas_similaires": 0,
            "incidents_similaires": [],
            "similarite_moyenne": 0.0,
            "priorite":          3,
        }


# ── Moteur LightGBM ───────────────────────────────────────────
def recommander_lgbm(texte: str, groupe: str = "", categorie: str = "", severite: int = 2) -> dict:
    """
    Recommande une action corrective via LightGBM multi-classes.
    Retourne l'action predite + probabilite de confiance + top-3 alternatives.
    Fallback règles métier si modèle absent.
    """
    if not LGBM_BUNDLE:
        return {
            "action_suggeree":   _reco_fallback(groupe, texte),
            "taux_succes":       0.65,
            "nb_cas_similaires": 0,
            "cas_similaires":    _RECOS_METIER.get(groupe, [])[:2],
            "priorite":          2,
        }

    try:
        import numpy as np
        from scipy.sparse import csr_matrix, hstack

        model  = LGBM_BUNDLE["model"]
        vec    = LGBM_BUNDLE["vectorizer"]
        le_act = LGBM_BUNDLE["le_action"]

        texte_combined = f"{texte} {groupe} {categorie}".strip()
        X_text  = vec.transform([texte_combined])

        # Encoder groupe et catégorie avec les vrais LabelEncoders si disponibles
        groupe_enc = 0
        cat_enc    = 0
        if LE_GROUPE is not None and groupe:
            try:
                groupe_enc = int(LE_GROUPE.transform([groupe])[0]) if groupe in LE_GROUPE.classes_ else 0
            except Exception:
                pass
        if LE_CAT is not None and categorie:
            try:
                cat_enc = int(LE_CAT.transform([categorie])[0]) if categorie in LE_CAT.classes_ else 0
            except Exception:
                pass

        X_extra = csr_matrix([[groupe_enc, cat_enc, max(1, min(4, severite))]])
        X       = hstack([X_text, X_extra])

        probas   = model.predict_proba(X)[0]
        top_idx  = probas.argsort()[::-1]  # tous les indices triés par proba décroissante

        # ── Filtrer les actions invalides ────────────────────
        # Chercher la meilleure action VALIDE parmi toutes les classes
        action_principale = None
        confiance         = 0.0
        alternatives      = []

        for idx in top_idx:
            action_candidate = le_act.classes_[idx].strip()
            if _action_est_valide(action_candidate):
                if action_principale is None:
                    action_principale = action_candidate
                    confiance         = float(probas[idx])
                elif len(alternatives) < 2:
                    alternatives.append(action_candidate[:100])
                if len(alternatives) >= 2:
                    break

        # Si aucune action valide trouvée dans LightGBM → fallback métier
        if action_principale is None:
            action_principale = _reco_fallback(groupe, texte)
            confiance         = 0.65
            logger.warning(
                "LightGBM — aucune action valide trouvée (toutes parasites) → fallback métier pour groupe={}",
                groupe
            )

        n_tickets = int(LGBM_METRICS.get("n_tickets", 1374)) if LGBM_METRICS else 1374

        return {
            "action_suggeree":   action_principale[:200],
            "taux_succes":       round(confiance, 2),
            "nb_cas_similaires": n_tickets,
            "cas_similaires":    alternatives,
            "priorite":          1 if confiance >= 0.80 else 2,
        }

    except Exception as exc:
        logger.error("Erreur moteur LightGBM Reco : {}", exc)
        return {
            "action_suggeree":   "Erreur — escalader au support technique",
            "taux_succes":       0.0,
            "nb_cas_similaires": 0,
            "cas_similaires":    [],
            "priorite":          3,
        }


# ── GET /api/recommandations ──────────────────────────────────
@router.get("/", response_model=List[RecommandationOut], summary="Liste des recommandations generees")
async def get_recommandations(
    statut:   Optional[str] = Query(default=None, description="Filtrer par statut"),
    priorite: Optional[int] = Query(default=None, ge=1, le=3, description="Filtrer par priorite"),
    payload: dict = Depends(verifier_token),
):
    """Recommandations LightGBM sur donnees reelles Attijari bank, enrichies par KNN incidents similaires."""
    exemples = [
        ("REC-003", "Demande verification email SPAM",            "Helpdesk",                "Securite et Habilitation SI"),
        ("REC-007", "Blocage indicateurs compromission Firewall", "Securite Operationnelle", "Securite et Habilitation SI"),
        ("REC-012", "Probleme acces Amplitude",                   "Systeme",                 "Amplitude"),
    ]

    result = []
    for rec_id, texte, groupe, cat in exemples:
        r = recommander_lgbm(texte, groupe, cat)
        entry = RecommandationOut(
            id=str(uuid.uuid4()),
            reclamation_id=rec_id,
            action_suggeree=r["action_suggeree"],
            taux_succes=r["taux_succes"],
            nb_cas_similaires=r["nb_cas_similaires"],
            priorite=r["priorite"],
            statut_impl="en_attente",
            created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        )
        if statut and entry.statut_impl != statut:
            continue
        if priorite and entry.priorite != priorite:
            continue
        result.append(entry)

    return result


# ── POST /api/recommandations/analyser ───────────────────────
@router.post("/analyser", summary="Analyser un ticket — recommandation LightGBM + KNN")
async def analyser_et_recommander(req: AnalyseRequest, payload: dict = Depends(verifier_token)):
    """
    Analyse un ticket et retourne la recommandation LightGBM et la suggestion KNN.
    Modele LightGBM entraine sur 1374 tickets Attijari bank — 35 classes d'action.
    """
    r = recommander_lgbm(req.texte, req.groupe or "", req.categorie or "", req.severite or 2)
    k = recommander_knn(req.texte, req.groupe or "", req.categorie or "", req.severite or 2)

    log_action(
        utilisateur=payload.get("sub", "anonyme"),
        role=payload.get("role", ""),
        action="RECOMMANDATION_LGBM_KNN",
        details=(
            f"Action suggeree LightGBM : {r['action_suggeree'][:80]} | confiance={r['taux_succes']} "
            f"| KNN similarite={k['similarite_moyenne']}"
        ),
    )
    logger.info(
        "Recommandation hybride : LightGBM confiance={} KNN similarite={} action={}",
        r["taux_succes"], k["similarite_moyenne"], r["action_suggeree"][:50]
    )

    return {
        "texte_analyse":        req.texte,
        "action_suggeree":      r["action_suggeree"],
        "taux_succes":         r["taux_succes"],
        "nb_cas_similaires":   r["nb_cas_similaires"],
        "cas_similaires":      r["cas_similaires"],
        "action_similaire_knn": k["action_suggeree"],
        "similarite_moyenne":  k["similarite_moyenne"],
        "incidents_similaires": k["incidents_similaires"],
        "priorite":            r["priorite"],
        "source":              "LightGBM + KNN — donnees reelles Attijari bank",
        "timestamp":           datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }


# ── POST /api/recommandations/similaire ───────────────────────
@router.post("/similaire", response_model=RecommandationSimilaireOut, summary="Rechercher incidents similaires — recommandation KNN")
async def rechercher_similaires(req: AnalyseRequest, payload: dict = Depends(verifier_token)):
    """
    Rechercher les incidents similaires et proposer une action corrective à partir de KNN.
    """
    k = recommander_knn(req.texte, req.groupe or "", req.categorie or "", req.severite or 2)

    log_action(
        utilisateur=payload.get("sub", "anonyme"),
        role=payload.get("role", ""),
        action="RECOMMANDATION_KNN",
        details=(
            f"Action suggeree KNN : {k['action_suggeree'][:80]} | similarite={k['similarite_moyenne']}"
        ),
    )
    logger.info(
        "Recommandation KNN : similarite={} action={}",
        k["similarite_moyenne"], k["action_suggeree"][:50]
    )

    return {
        "id":                 str(uuid.uuid4()),
        "reclamation_id":     f"KNN-{str(uuid.uuid4())[:8]}",
        "action_suggeree":    k["action_suggeree"],
        "taux_succes":        k["taux_succes"],
        "nb_cas_similaires":  k["nb_cas_similaires"],
        "similarite_moyenne": k["similarite_moyenne"],
        "incidents_similaires": k["incidents_similaires"],
        "statut_impl":        "en_attente",
        "created_at":         datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }


# ── GET /api/recommandations/{id} ────────────────────────────
@router.get("/{reclamation_id}", summary="Recommandation pour une reclamation — LightGBM + KNN")
async def get_recommandation(reclamation_id: str, payload: dict = Depends(verifier_token)):
    r = recommander_lgbm("Ticket " + reclamation_id)
    return {
        "id":              str(uuid.uuid4()),
        "reclamation_id":  reclamation_id,
        "action_suggeree": r["action_suggeree"],
        "taux_succes":     r["taux_succes"],
        "nb_cas_similaires": r["nb_cas_similaires"],
        "priorite":        r["priorite"],
        "statut_impl":     "en_attente",
        "created_at":      datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }


# ── POST /api/recommandations/{id}/valider ───────────────────
@router.post("/{reco_id}/valider", summary="Valider ou rejeter une recommandation")
async def valider_recommandation(
    reco_id: str,
    req: ValidationRequest,
    payload: dict = Depends(verifier_token),
):
    if req.decision not in ("valider", "rejeter"):
        raise HTTPException(status_code=400, detail="decision doit etre 'valider' ou 'rejeter'")

    statut       = "validee"  if req.decision == "valider" else "rejetee"
    action_label = "RPA declenche automatiquement" if req.decision == "valider" else "Traitement manuel requis"

    log_action(
        utilisateur=payload.get("sub", "anonyme"),
        role=payload.get("role", ""),
        action="VALIDER_RECOMMANDATION",
        details=f"Reco {reco_id} -> {statut} | {req.commentaire or ''}",
    )
    logger.info("Recommandation {} : {}", reco_id, statut)

    return {
        "message":     f"Recommandation {reco_id} {statut}",
        "reco_id":     reco_id,
        "statut":      statut,
        "action":      action_label,
        "commentaire": req.commentaire,
        "date":        datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
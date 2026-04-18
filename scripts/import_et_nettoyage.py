"""
import_et_nettoyage.py — Import et nettoyage des données réelles Attijari bank
PFE Sujet 21 — Données : tickets IT Février + Mars 2026

Structure des données découverte :
- 20 000 lignes (10 000 par mois) — mais ~1 507 tickets uniques (doublons massifs)
- Colonnes clés : ID de demande, Heure de création, Groupe, Statut de la demande,
  Objet, Description, Priorité, Catégorie, Sous-catégorie, Résolution,
  Type de demande, Technicien, État en retard, Temps de résolution du contrat SLA

Exécuter : python scripts/import_et_nettoyage.py
"""
import pandas as pd
import numpy as np
import os
import uuid
import re
import hashlib
import base64
from datetime import datetime
from cryptography.fernet import Fernet

# ── Configuration ─────────────────────────────────────────────
FICHIER_FEVRIER = "data/raw/tous_les_donnèées_février_2026_DATA.xls"
FICHIER_MARS    = "data/raw/tous_les_donnèées_mars_2026_DATA.xls"
SORTIE_CSV      = "data/cleaned/reclamations_propres.csv"
HEADER_ROW      = 8   # La ligne d'en-tête réelle dans les fichiers XLS

# Clé AES-256 pour chiffrer les descriptions sensibles
AES_KEY = os.getenv("AES_KEY", "AttijariPFE2026Key32charsExact!!")

def get_fernet():
    key = hashlib.sha256(AES_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))

def encrypt(text: str) -> str:
    if not text or text in ["Non attribué", "nan", ""]:
        return ""
    try:
        return get_fernet().encrypt(str(text).encode()).decode()
    except:
        return str(text)

def normaliser_priorite(p: str) -> int:
    """Convertit la priorité textuelle en score numérique 1-4"""
    mapping = {"Haute": 1, "Moyenne": 2, "Basse": 3, "Normale": 2, "Non attribué": 2}
    return mapping.get(str(p).strip(), 2)

def normaliser_statut(s: str) -> str:
    """Normalise les statuts variés en valeurs standard"""
    s = str(s).strip().lower()
    if "clotur" in s or "traité" in s or "résolu" in s:
        return "resolue"
    elif "annul" in s:
        return "annulee"
    elif "attente" in s:
        return "en_attente"
    elif "ouvert" in s:
        return "soumise"
    return "soumise"

def normaliser_resolution(r: str) -> str:
    """Normalise les variations de 'Nécessaire fait'"""
    if pd.isna(r) or str(r).strip() in ["", "Non attribué", "*"]:
        return ""
    r = str(r).strip()
    r = re.sub(r'[✨\n\*]', '', r).strip()
    # Normaliser les variantes de NF / Nécessaire fait
    if r.upper() in ["NF", "NÉCESSAIRE FAIT", "NECESSAIRE FAIT", "RESOLU", "RÉSOLU"]:
        return "Nécessaire fait"
    return r

def parser_duree_sla(duree: str) -> float:
    """Convertit '06:00:00' en minutes float"""
    try:
        parts = str(duree).split(":")
        if len(parts) == 3:
            return int(parts[0]) * 60 + int(parts[1]) + int(parts[2]) / 60
    except:
        pass
    return 0.0

def charger_fichier(path: str) -> pd.DataFrame:
    """Charge un fichier XLS Attijari bank avec conversion LibreOffice"""
    print(f"  Chargement : {path}")

    # Si c'est un XLS, convertir d'abord en CSV via LibreOffice
    if path.endswith('.xls'):
        import subprocess
        csv_path = path.replace('.xls', '_temp.csv').replace('data/raw/', 'data/cleaned/')
        os.makedirs('data/cleaned', exist_ok=True)

        # Utiliser LibreOffice pour la conversion
        cmd = f'libreoffice --headless --convert-to csv "{path}" --outdir data/cleaned/ 2>/dev/null'
        subprocess.run(cmd, shell=True, capture_output=True)

        # Renommer le fichier converti
        base = os.path.basename(path).replace('.xls', '.csv')
        converted = f"data/cleaned/{base}"

        if os.path.exists(converted):
            df = pd.read_csv(converted, sep=',', header=HEADER_ROW,
                             encoding='utf-8', on_bad_lines='skip')
            return df

    # Fallback : lecture CSV directe si déjà converti
    if path.endswith('.csv'):
        return pd.read_csv(path, sep=',', header=HEADER_ROW,
                           encoding='utf-8', on_bad_lines='skip')

    raise FileNotFoundError(f"Fichier non trouvé ou format non supporté : {path}")

def nettoyer_et_importer():
    print("=" * 60)
    print("  Import & Nettoyage — Données Attijari bank 2026")
    print("=" * 60)

    # ── 1. Chargement ─────────────────────────────────────────
    print("\n[1/7] Chargement des fichiers XLS...")
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/cleaned", exist_ok=True)

    # Chemins alternatifs (CSV déjà convertis)
    fevrier_csv = "data/cleaned/tous_les_donnèées_février_2026_DATA.csv"
    mars_csv    = "data/cleaned/tous_les_donnèées_mars_2026_DATA.csv"

    frames = []
    for path in [fevrier_csv, mars_csv]:
        if os.path.exists(path):
            df = pd.read_csv(path, sep=',', header=HEADER_ROW,
                             encoding='utf-8', on_bad_lines='skip')
            frames.append(df)
            print(f"  Chargé : {path} — {len(df)} lignes")
        else:
            print(f"  Fichier non trouvé : {path}")
            print(f"  Copier les fichiers XLS dans data/raw/ et reconvertir")

    if not frames:
        print("ERREUR : Aucun fichier de données trouvé.")
        print("Copier les fichiers XLS dans data/raw/ puis relancer.")
        return

    df_raw = pd.concat(frames, ignore_index=True)
    print(f"  Total brut : {len(df_raw)} lignes")

    # ── 2. Suppression des doublons ───────────────────────────
    print("\n[2/7] Suppression des doublons...")
    avant = len(df_raw)
    # Garder la première occurrence de chaque ID de demande
    df = df_raw.drop_duplicates(subset=['ID de demande'], keep='first')
    apres = len(df)
    print(f"  Doublons supprimés : {avant - apres} ({avant} → {apres} lignes)")

    # ── 3. Traitement des valeurs manquantes ──────────────────
    print("\n[3/7] Traitement des valeurs manquantes...")
    # Remplacer "Non attribué" par NaN pour les colonnes optionnelles
    cols_optionnelles = ['Résolution', 'Technicien', 'Sous-catégorie',
                         'Département', 'Région', 'Groupe OLA']
    for col in cols_optionnelles:
        if col in df.columns:
            df[col] = df[col].replace('Non attribué', np.nan)

    nan_avant = df.isnull().sum().sum()
    print(f"  Valeurs manquantes restantes : {nan_avant}")
    print(f"  Colonnes avec NaN : {df.isnull().sum()[df.isnull().sum() > 0].to_dict()}")

    # ── 4. Normalisation des types ────────────────────────────
    print("\n[4/7] Normalisation des types et formats...")

    # Dates
    df['date_creation'] = pd.to_datetime(df['Heure de création'],
                                          format='%d/%m/%Y %I:%M %p', errors='coerce')
    df['date_resolution'] = pd.to_datetime(df['Heure de résolution'],
                                            format='%d/%m/%Y %I:%M %p', errors='coerce')

    nan_dates = df['date_creation'].isna().sum()
    print(f"  Dates création non parsées : {nan_dates}")

    # Durée SLA en minutes
    df['duree_resolution_minutes'] = df['Temps de résolution du contrat SLA'].apply(parser_duree_sla)

    # Priorité numérique
    df['severite'] = df['Priorité'].apply(normaliser_priorite)

    # Statut normalisé
    df['statut_norme'] = df['Statut de la demande'].apply(normaliser_statut)

    # Résolution normalisée
    df['resolution_normee'] = df['Résolution'].apply(normaliser_resolution)

    print("  Priorité → sévérité : OK")
    print("  Statut normalisé : OK")
    print(f"  Durée SLA moyenne : {df['duree_resolution_minutes'].mean():.1f} minutes")

    # ── 5. Normalisation des textes ───────────────────────────
    print("\n[5/7] Normalisation des descriptions textuelles...")

    def nettoyer_texte(t):
        if pd.isna(t):
            return ""
        t = str(t).strip()
        # Supprimer les caractères spéciaux excessifs
        t = re.sub(r'[\n\r\t]+', ' ', t)
        t = re.sub(r'\s+', ' ', t)
        t = re.sub(r'[✨★☆]', '', t)
        return t.strip()

    df['objet_propre']       = df['Objet'].apply(nettoyer_texte)
    df['description_propre'] = df['Description'].apply(nettoyer_texte)
    df['resolution_propre']  = df['resolution_normee'].apply(nettoyer_texte)

    print("  Nettoyage textes : OK")

    # ── 6. Construction du dataset final ─────────────────────
    print("\n[6/7] Construction du dataset final...")

    df_final = pd.DataFrame({
        'id':              [str(uuid.uuid4()) for _ in range(len(df))],
        'id_demande_orig': df['ID de demande'].astype(str),
        'date':            df['date_creation'].dt.strftime('%Y-%m-%d %H:%M:%S').fillna(''),
        'type_operation':  df['Groupe'].fillna('Non attribué'),
        'categorie':       df['Catégorie'].fillna(''),
        'sous_categorie':  df['Sous-catégorie'].fillna(''),
        'objet':           df['objet_propre'],
        'description':     df['description_propre'],
        'action_effectuee':df['resolution_propre'],   # colonne CLÉ pour KNN
        'technicien':      df['Technicien'].fillna(''),
        'departement':     df['Département'].fillna(''),
        'severite':        df['severite'],
        'statut':          df['statut_norme'],
        'priorite_orig':   df['Priorité'].fillna(''),
        'type_demande':    df['Type de demande'].fillna(''),
        'niveau':          df['Niveau'].fillna(''),
        'en_retard':       df['État en retard'].astype(bool),
        'duree_resolution_min': df['duree_resolution_minutes'],
        'date_resolution': df['date_resolution'].dt.strftime('%Y-%m-%d %H:%M:%S').fillna(''),
        'score_anomalie':  None,
        'score_risque':    None,
    })

    print(f"  Dataset final : {len(df_final)} lignes × {len(df_final.columns)} colonnes")
    print(f"  Types de demandes :")
    print(f"    {df['Type de demande'].value_counts().to_dict()}")
    print(f"  Groupes (top 5) :")
    for k, v in df['Groupe'].value_counts().head(5).to_dict().items():
        print(f"    {k}: {v}")
    print(f"  Actions effectuées non vides : {(df_final['action_effectuee'] != '').sum()}")
    print(f"  En retard : {df_final['en_retard'].sum()} / {len(df_final)}")

    # ── 7. Sauvegarde CSV propre ──────────────────────────────
    print("\n[7/7] Sauvegarde du dataset propre...")
    os.makedirs("data/cleaned", exist_ok=True)
    df_final.to_csv(SORTIE_CSV, index=False, encoding='utf-8')
    print(f"  Sauvegardé : {SORTIE_CSV}")
    print(f"  Taille fichier : {os.path.getsize(SORTIE_CSV) // 1024} Ko")

    # ── Résumé statistiques ───────────────────────────────────
    print("\n" + "=" * 60)
    print("  RÉSUMÉ DU DATASET PROPRE")
    print("=" * 60)
    print(f"  Total tickets uniques  : {len(df_final)}")
    print(f"  Période                : {df_final['date'].min()} → {df_final['date'].max()}")
    print(f"  Tickets avec résolution: {(df_final['action_effectuee'] != '').sum()}")
    print(f"  Tickets en retard SLA  : {df_final['en_retard'].sum()}")
    print(f"  Durée résolution moy.  : {df_final['duree_resolution_min'].mean():.0f} min")
    print(f"  Groupes distincts      : {df_final['type_operation'].nunique()}")
    print(f"  Catégories distinctes  : {df_final['categorie'].nunique()}")
    print("=" * 60)
    print("\n  Prochaine étape : python scripts/analyser_eda.py")
    print("  Puis            : python scripts/pipeline_nlp.py")

    return df_final

if __name__ == "__main__":
    df = nettoyer_et_importer()

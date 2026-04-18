"""
import_csv.py — Import des données CSV réelles dans PostgreSQL
PFE Attijari bank — Sujet 21

Lit data/cleaned/reclamations_propres.csv
Insère les 1507 tickets dans la table reclamations
Vide et réinsère si déjà rempli partiellement

Exécuter (venv actif, APRÈS init_db.py) :
    python scripts/import_csv.py
"""
import os
import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()  # Charge les variables du fichier .env

# ── Configuration ──────────────────────────────────────────
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "attijari_pfe")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASSWORD", "postgres")

CSV_PATH = "data/cleaned/reclamations_propres.csv"

G="\033[92m"; R="\033[91m"; Y="\033[93m"; B="\033[94m"; BOLD="\033[1m"; X="\033[0m"
def ok(m):   print(f"  {G}✓{X} {m}")
def err(m):  print(f"  {R}✗{X} {m}")
def info(m): print(f"  {B}→{X} {m}")
def titre(t):print(f"\n{BOLD}{B}{'═'*55}{X}\n{BOLD}  {t}{X}\n{B}{'═'*55}{X}")

def nettoyer_valeur(val, max_len=None):
    """Convertit NaN/None en None Python, tronque si besoin"""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    s = str(val).strip()
    if s.lower() in ("nan", "none", ""):
        return None
    if max_len:
        return s[:max_len]
    return s

def charger_csv():
    """Charge et valide le CSV des réclamations"""
    if not os.path.exists(CSV_PATH):
        err(f"Fichier introuvable : {CSV_PATH}")
        err("Lancer d'abord : python scripts/import_et_nettoyage.py")
        exit(1)

    df = pd.read_csv(CSV_PATH, on_bad_lines="skip")
    info(f"CSV chargé : {len(df)} lignes")

    # Vérifier les colonnes requises
    colonnes_requises = ["id", "date", "type_operation", "objet", "severite", "statut"]
    manquantes = [c for c in colonnes_requises if c not in df.columns]
    if manquantes:
        err(f"Colonnes manquantes : {manquantes}")
        exit(1)

    # Vérifier les scores
    if "score_anomalie" not in df.columns or df["score_anomalie"].isna().sum() == len(df):
        err("score_anomalie absent ou vide — lancer d'abord : python scripts/fix_tout.py")
        exit(1)

    nan_scores = df["score_anomalie"].isna().sum()
    if nan_scores > 0:
        info(f"score_anomalie NaN : {nan_scores} → remplacement par 0.3")
        df["score_anomalie"] = df["score_anomalie"].fillna(0.3)
        df["score_risque"]   = df["score_risque"].fillna(0.28)

    ok(f"Données validées : {len(df)} tickets, 0 NaN critique")
    ok(f"Risque élevé ≥ 0.75 : {(df['score_anomalie'] >= 0.75).sum()} tickets")
    return df

def preparer_lignes(df):
    """Prépare les tuples pour l'insertion PostgreSQL"""
    rows = []
    erreurs = 0

    for _, row in df.iterrows():
        try:
            # Date
            date = pd.to_datetime(row.get("date"), errors="coerce")
            if pd.isna(date):
                erreurs += 1
                continue

            # Description = objet du ticket
            description = nettoyer_valeur(row.get("objet"), 500)
            if not description:
                description = nettoyer_valeur(row.get("description"), 500) or "N/A"

            rows.append((
                str(row["id"]),                                      # id
                date,                                                 # date
                nettoyer_valeur(row.get("type_operation"), 100) or "Non attribué",  # type_operation
                description,                                          # description
                nettoyer_valeur(row.get("action_effectuee"), 500),   # action_effectuee
                int(row.get("severite", 2) or 2),                    # severite
                nettoyer_valeur(row.get("statut"), 50) or "soumise", # statut
                float(row["score_anomalie"]) if not pd.isna(row.get("score_anomalie")) else None,
                float(row["score_risque"])   if not pd.isna(row.get("score_risque"))   else None,
            ))
        except Exception:
            erreurs += 1
            continue

    if erreurs > 0:
        info(f"Lignes ignorées (erreurs format) : {erreurs}")

    ok(f"Lignes préparées pour insertion : {len(rows)}")
    return rows

def importer_dans_bdd(rows):
    """Insère les lignes dans PostgreSQL par batch"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASS
        )
        cur = conn.cursor()

        # Vérifier état actuel
        cur.execute("SELECT COUNT(*) FROM reclamations;")
        nb_avant = cur.fetchone()[0]
        info(f"Tickets actuellement en BDD : {nb_avant}")

        if nb_avant > 0 and nb_avant < len(rows):
            info("Import partiel détecté → nettoyage et réinsertion complète...")
            cur.execute("DELETE FROM recommandations;")
            cur.execute("DELETE FROM actions_rpa;")
            cur.execute("DELETE FROM reclamations;")
            conn.commit()
            ok("Tables vidées")

        cur.execute("SELECT COUNT(*) FROM reclamations;")
        nb_maintenant = cur.fetchone()[0]

        if nb_maintenant > 0:
            ok(f"Base déjà remplie : {nb_maintenant} tickets — aucune action nécessaire")
            cur.close(); conn.close()
            return nb_maintenant

        # Insertion par batch de 200
        query = """
            INSERT INTO reclamations
                (id, date, type_operation, description, action_effectuee,
                 severite, statut, score_anomalie, score_risque)
            VALUES %s
            ON CONFLICT (id) DO NOTHING
        """
        info(f"Insertion en cours ({len(rows)} tickets)...")

        BATCH = 200
        inseres = 0
        for i in range(0, len(rows), BATCH):
            batch = rows[i:i+BATCH]
            execute_values(cur, query, batch)
            conn.commit()
            inseres += len(batch)
            print(f"    {inseres}/{len(rows)} tickets insérés...", end="\r")

        print()

        # Vérification finale
        cur.execute("SELECT COUNT(*) FROM reclamations;")
        nb_final = cur.fetchone()[0]
        ok(f"Import terminé : {nb_final} tickets dans PostgreSQL !")

        # Statistiques
        cur.execute("""
            SELECT type_operation, COUNT(*) as nb,
                   ROUND(AVG(score_risque)::numeric, 3) as score_moy
            FROM reclamations
            GROUP BY type_operation
            ORDER BY nb DESC LIMIT 5;
        """)
        info("Top 5 groupes en BDD :")
        for r in cur.fetchall():
            print(f"      {r[0]:35s} {r[1]:5d} tickets  score moy: {r[2]}")

        cur.execute("SELECT COUNT(*) FROM reclamations WHERE score_risque >= 0.75;")
        alertes = cur.fetchone()[0]
        ok(f"Alertes ≥ 0.75 en BDD : {alertes} tickets")

        cur.execute("SELECT MIN(date), MAX(date) FROM reclamations;")
        dmin, dmax = cur.fetchone()
        info(f"Période : {str(dmin)[:10]} → {str(dmax)[:10]}")

        cur.close()
        conn.close()
        return nb_final

    except psycopg2.OperationalError as e:
        err(f"PostgreSQL non accessible : {e}")
        err("Vérifier que PostgreSQL est démarré")
        err("Lancer d'abord : python scripts/init_db.py")
        return 0
    except psycopg2.errors.UndefinedTable:
        err("Table reclamations n'existe pas")
        err("Lancer d'abord : python scripts/init_db.py")
        return 0
    except Exception as e:
        err(f"Erreur import : {e}")
        import traceback; traceback.print_exc()
        return 0

# ── MAIN ──────────────────────────────────────────────────
if __name__ == "__main__":
    titre("Import CSV → PostgreSQL — Attijari bank")

    # 1. Charger le CSV
    titre("Étape 1 — Chargement du CSV")
    df = charger_csv()

    # 2. Préparer les lignes
    titre("Étape 2 — Préparation des données")
    rows = preparer_lignes(df)

    # 3. Importer dans la BDD
    titre("Étape 3 — Import dans PostgreSQL")
    nb = importer_dans_bdd(rows)

    # Résumé
    print(f"\n{BOLD}{'═'*55}{X}")
    if nb == 1507:
        print(f"{G}{BOLD}  ✓ IMPORT COMPLET : 1507 tickets en BDD !{X}")
    elif nb > 100:
        print(f"{G}{BOLD}  ✓ Import OK : {nb} tickets en BDD{X}")
    elif nb > 0:
        print(f"{Y}{BOLD}  ~ Import partiel : {nb}/{len(df)} tickets{X}")
    else:
        print(f"{R}{BOLD}  ✗ Import échoué — voir les erreurs ci-dessus{X}")
    print(f"\n  Prochaine étape :")
    print(f"  uvicorn app.main:app --reload")
    print(f"  → http://localhost:8000/api/alertes?seuil=0.75")
    print(f"{'═'*55}")

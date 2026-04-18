"""
init_db.py — Initialisation complète de la base de données PostgreSQL
PFE Attijari bank — Sujet 21

Crée toutes les tables + insère les données de démarrage (rôles + admin)

Exécuter (venv actif) :
    python scripts/init_db.py
"""
import os
import uuid
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# ── Configuration ──────────────────────────────────────────
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "attijari_pfe")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASSWORD", "postgres")

G="\033[92m"; R="\033[91m"; Y="\033[93m"; B="\033[94m"; BOLD="\033[1m"; X="\033[0m"
def ok(m):   print(f"  {G}✓{X} {m}")
def err(m):  print(f"  {R}✗{X} {m}")
def info(m): print(f"  {B}→{X} {m}")
def titre(t):print(f"\n{BOLD}{B}{'═'*55}{X}\n{BOLD}  {t}{X}\n{B}{'═'*55}{X}")

def creer_base_si_nexiste_pas():
    """Crée la base attijari_pfe si elle n'existe pas encore"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT,
            dbname="postgres",
            user=DB_USER, password=DB_PASS
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (DB_NAME,))
        if not cur.fetchone():
            cur.execute(f"CREATE DATABASE {DB_NAME};")
            ok(f"Base de données '{DB_NAME}' créée")
        else:
            ok(f"Base de données '{DB_NAME}' déjà existante")

        cur.close()
        conn.close()
    except Exception as e:
        err(f"Création base : {e}")
        raise

def creer_tables(cur):
    """Crée toutes les tables si elles n'existent pas"""

    # ── Table reclamations ──────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reclamations (
            id               VARCHAR(36)  PRIMARY KEY,
            date             TIMESTAMP    NOT NULL,
            type_operation   VARCHAR(100) NOT NULL,
            description      TEXT         NOT NULL,
            action_effectuee TEXT         NULL,
            severite         INTEGER      NOT NULL DEFAULT 2,
            statut           VARCHAR(50)  NOT NULL DEFAULT 'soumise',
            score_anomalie   FLOAT        NULL,
            score_risque     FLOAT        NULL,
            created_at       TIMESTAMP    NOT NULL DEFAULT NOW(),
            updated_at       TIMESTAMP    NULL
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rec_date   ON reclamations(date);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rec_type   ON reclamations(type_operation);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rec_statut ON reclamations(statut);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rec_score  ON reclamations(score_risque);")
    ok("Table reclamations créée")

    # ── Table utilisateurs ──────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id           VARCHAR(36)  PRIMARY KEY,
            nom          VARCHAR(100) NOT NULL,
            email        VARCHAR(150) NOT NULL UNIQUE,
            mot_de_passe VARCHAR(255) NOT NULL,
            role         VARCHAR(50)  NOT NULL DEFAULT 'utilisateur',
            est_actif    BOOLEAN      NOT NULL DEFAULT TRUE,
            created_at   TIMESTAMP    NOT NULL DEFAULT NOW()
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON utilisateurs(email);")
    ok("Table utilisateurs créée")

    # ── Table roles ─────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id          VARCHAR(36) PRIMARY KEY,
            libelle     VARCHAR(50) NOT NULL UNIQUE,
            permissions TEXT[]      NOT NULL DEFAULT '{}'
        );
    """)
    ok("Table roles créée")

    # ── Table audit_logs ────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id             VARCHAR(36)  PRIMARY KEY,
            utilisateur    VARCHAR(150) NULL,
            utilisateur_id VARCHAR(36)  NULL,
            role           VARCHAR(50)  NULL,
            action         VARCHAR(200) NOT NULL,
            details        TEXT         NULL,
            ip_address     VARCHAR(50)  NULL,
            timestamp      TIMESTAMP    NOT NULL DEFAULT NOW()
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_ts     ON audit_logs(timestamp DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_user   ON audit_logs(utilisateur_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);")
    ok("Table audit_logs créée")

    # ── Table predictions ───────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id               VARCHAR(36) PRIMARY KEY,
            date_prediction  TIMESTAMP   NOT NULL DEFAULT NOW(),
            type_operation   VARCHAR(100) NOT NULL,
            score_risque     FLOAT        NOT NULL,
            est_alerte       BOOLEAN      NOT NULL DEFAULT FALSE,
            version_modele   VARCHAR(50)  NULL,
            fenetre_jours    INTEGER      NOT NULL DEFAULT 7
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pred_date  ON predictions(date_prediction DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pred_alerte ON predictions(est_alerte);")
    ok("Table predictions créée")

    # ── Table recommandations ───────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS recommandations (
            id                VARCHAR(36) PRIMARY KEY,
            reclamation_id    VARCHAR(36) NOT NULL REFERENCES reclamations(id) ON DELETE CASCADE,
            action_suggeree   TEXT        NOT NULL,
            taux_succes       FLOAT       NOT NULL DEFAULT 0.0,
            nb_cas_similaires INTEGER     NOT NULL DEFAULT 0,
            priorite          INTEGER     NOT NULL DEFAULT 2,
            statut_impl       VARCHAR(50) NOT NULL DEFAULT 'en_attente',
            created_at        TIMESTAMP   NOT NULL DEFAULT NOW()
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_reco_rec ON recommandations(reclamation_id);")
    ok("Table recommandations créée")

    # ── Table actions_rpa ───────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS actions_rpa (
            id                VARCHAR(36)  PRIMARY KEY,
            recommandation_id VARCHAR(36)  NOT NULL REFERENCES recommandations(id) ON DELETE CASCADE,
            type_action       VARCHAR(200) NOT NULL,
            statut            VARCHAR(50)  NOT NULL DEFAULT 'en_attente',
            resultat          TEXT         NULL,
            execute_par       VARCHAR(50)  NOT NULL DEFAULT 'robot_uipath',
            execute_le        TIMESTAMP    NULL,
            created_at        TIMESTAMP    NOT NULL DEFAULT NOW()
        );
    """)
    ok("Table actions_rpa créée")

def inserer_donnees_demarrage(cur):
    """Insère les rôles et l'administrateur par défaut"""

    # Rôles
    roles = [
        ("role-001", "admin",          ["read","write","delete","manage_users","view_audit"]),
        ("role-002", "responsable_it", ["read","write","validate_rpa","view_dashboard"]),
        ("role-003", "utilisateur",    ["read","submit_reclamation"]),
    ]
    for rid, libelle, perms in roles:
        cur.execute("""
            INSERT INTO roles (id, libelle, permissions)
            VALUES (%s, %s, %s)
            ON CONFLICT (libelle) DO NOTHING;
        """, (rid, libelle, perms))
    ok("Rôles insérés : admin, responsable_it, utilisateur")

    # Mot de passe admin hashé avec bcrypt
    try:
        from passlib.context import CryptContext
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto").hash("Admin@2026!")
    except:
        pwd = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # fallback

    cur.execute("""
        INSERT INTO utilisateurs (id, nom, email, mot_de_passe, role)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (email) DO NOTHING;
    """, ("user-001", "Administrateur", "admin@attijaribank.tn", pwd, "admin"))

    cur.execute("""
        INSERT INTO utilisateurs (id, nom, email, mot_de_passe, role)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (email) DO NOTHING;
    """, ("user-002", "Responsable IT", "responsable.it@attijaribank.tn", pwd, "responsable_it"))

    try:
        from passlib.context import CryptContext
        robot_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto").hash("Robot@2026!")
    except:
        robot_pwd = pwd

    cur.execute("""
        INSERT INTO utilisateurs (id, nom, email, mot_de_passe, role)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (email) DO NOTHING;
    """, ("user-rpa", "Robot UiPath", "robot@attijaribank.tn", robot_pwd, "responsable_it"))

    ok("Utilisateurs insérés : admin · responsable.it · robot")

def verifier_tables(cur):
    """Vérifie que toutes les tables sont bien créées"""
    cur.execute("""
        SELECT table_name, 
               (SELECT COUNT(*) FROM information_schema.columns 
                WHERE table_name = t.table_name AND table_schema = 'public')
        FROM information_schema.tables t
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    rows = cur.fetchall()
    info(f"{len(rows)} tables dans la base :")
    for nom, nb_cols in rows:
        print(f"      {nom:25s} {nb_cols} colonnes")
    return len(rows)

# ── MAIN ──────────────────────────────────────────────────
if __name__ == "__main__":
    titre("Initialisation BDD PostgreSQL — Attijari bank")

    # 1. Créer la base
    info(f"Connexion à {DB_HOST}:{DB_PORT}")
    try:
        creer_base_si_nexiste_pas()
    except Exception as e:
        err(f"Impossible de créer la base : {e}")
        print(f"\n  Créer manuellement :")
        print(f"  psql -U postgres -c \"CREATE DATABASE {DB_NAME};\"")
        exit(1)

    # 2. Créer les tables
    titre("Création des tables")
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASS
        )
        cur = conn.cursor()
        creer_tables(cur)
        conn.commit()
    except Exception as e:
        err(f"Création tables : {e}")
        exit(1)

    # 3. Insérer les données de démarrage
    titre("Insertion des données de démarrage")
    try:
        inserer_donnees_demarrage(cur)
        conn.commit()
    except Exception as e:
        err(f"Insertion données : {e}")
        conn.rollback()

    # 4. Vérification
    titre("Vérification finale")
    nb_tables = verifier_tables(cur)

    cur.execute("SELECT COUNT(*) FROM utilisateurs;")
    nb_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM roles;")
    nb_roles = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM reclamations;")
    nb_recs = cur.fetchone()[0]

    ok(f"{nb_tables} tables créées")
    ok(f"{nb_users} utilisateurs · {nb_roles} rôles")
    info(f"Tickets en BDD : {nb_recs} — (0 = normal, lancer import_csv.py ensuite)")

    cur.close()
    conn.close()

    print(f"\n{BOLD}{'═'*55}{X}")
    print(f"{BOLD}  BASE DE DONNÉES PRÊTE !{X}")
    print(f"{BOLD}{'═'*55}{X}")
    print(f"  Prochaine étape :")
    print(f"  python scripts/import_csv.py")
    print(f"  → Insère les 1507 tickets dans PostgreSQL")
    print(f"{'═'*55}")

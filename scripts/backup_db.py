"""
backup_db.py — Sauvegarde automatique PostgreSQL
PFE Attijari bank — Sujet 21
Exécuter : python scripts/backup_db.py
"""
import subprocess, os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_HOST     = os.getenv("DB_HOST",     "localhost")
DB_PORT     = os.getenv("DB_PORT",     "5432")
DB_USER     = os.getenv("DB_USER",     "postgres")
DB_NAME     = os.getenv("DB_NAME",     "attijari_pfe")
BACKUP_DIR  = os.getenv("BACKUP_PATH", "backups")

def backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts          = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{BACKUP_DIR}/backup_{DB_NAME}_{ts}.sql"

    print(f"Démarrage backup : {backup_file}")
    cmd    = f"pg_dump -h {DB_HOST} -p {DB_PORT} -U {DB_USER} {DB_NAME}"
    result = subprocess.run(
        cmd, shell=True, capture_output=True,
        env={**os.environ, "PGPASSWORD": os.getenv("DB_PASSWORD", "postgres")}
    )

    if result.returncode == 0:
        with open(backup_file, "w", encoding="utf-8") as f:
            f.write(result.stdout.decode("utf-8"))
        size = os.path.getsize(backup_file)
        print(f"Backup créé avec succès : {backup_file} ({size} octets)")
        return backup_file
    else:
        print(f"Erreur backup : {result.stderr.decode()}")
        return None

if __name__ == "__main__":
    backup()

"""
scheduler.py — Planificateur de tâches automatiques
PFE Attijari bank — Sujet 21

Tâches planifiées :
  - Réentraînement LSTM + KNN : chaque lundi à 02h00
  - Nettoyage des logs anciens : chaque dimanche à 03h00
"""
import subprocess
import sys
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.logging_config import logger

# Instance globale du scheduler
_scheduler: BackgroundScheduler | None = None


# ── Tâche 1 : Réentraînement des modèles ─────────────────────
def retrain_models() -> None:
    """
    Réentraîne le modèle LSTM et recalcule les recommandations KNN.
    Planifié chaque lundi à 02h00 — utilise les nouveaux tickets clôturés.
    """
    logger.info("═══ SCHEDULER : démarrage réentraînement LSTM + KNN ═══")
    start = datetime.now()

    for script, label in [
        ("scripts/entrainer_lstm.py",      "LSTM"),
        ("scripts/recommandations_knn.py", "KNN"),
    ]:
        try:
            result = subprocess.run(
                [sys.executable, script],
                capture_output=True,
                text=True,
                timeout=600,            # 10 minutes max
            )
            if result.returncode == 0:
                logger.info("Réentraînement {} terminé avec succès", label)
            else:
                logger.error(
                    "Réentraînement {} échoué (code {}) : {}",
                    label, result.returncode, result.stderr[:500]
                )
        except subprocess.TimeoutExpired:
            logger.error("Réentraînement {} : timeout après 10 minutes", label)
        except Exception as exc:
            logger.error("Réentraînement {} : erreur inattendue : {}", label, exc)

    elapsed = (datetime.now() - start).seconds
    logger.info("═══ SCHEDULER : réentraînement terminé en {}s ═══", elapsed)


# ── Tâche 2 : Nettoyage des logs anciens ─────────────────────
def cleanup_old_logs() -> None:
    """Supprime les fichiers de log de plus de 30 jours."""
    import os
    import glob
    from datetime import timedelta

    logs_dir = "logs"
    if not os.path.isdir(logs_dir):
        return

    cutoff = datetime.now() - timedelta(days=30)
    removed = 0
    for fpath in glob.glob(f"{logs_dir}/*.log.zip"):
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            if mtime < cutoff:
                os.remove(fpath)
                removed += 1
        except Exception:
            pass

    if removed:
        logger.info("Nettoyage logs : {} fichier(s) supprimé(s)", removed)


# ── Démarrage / arrêt ─────────────────────────────────────────
def start_scheduler() -> BackgroundScheduler:
    """Démarre le scheduler en arrière-plan."""
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="Africa/Tunis")

    # Réentraînement chaque lundi à 02h00
    _scheduler.add_job(
        retrain_models,
        CronTrigger(day_of_week="mon", hour=2, minute=0),
        id="retrain_models",
        name="Réentraînement LSTM + KNN",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Nettoyage logs chaque dimanche à 03h00
    _scheduler.add_job(
        cleanup_old_logs,
        CronTrigger(day_of_week="sun", hour=3, minute=0),
        id="cleanup_logs",
        name="Nettoyage logs anciens",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "Scheduler démarré — réentraînement : lundi 02h00 | nettoyage logs : dimanche 03h00"
    )
    return _scheduler


def stop_scheduler() -> None:
    """Arrête proprement le scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler arrêté")

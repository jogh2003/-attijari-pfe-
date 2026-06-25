"""
train_all_models.py - Wrapper pour lancer la génération pipeline + entrainements
Usage: python scripts/train_all_models.py
"""
import subprocess
import sys
import os

SCRIPTS = [
    "python scripts/pipeline_nlp.py",
    "python scripts/entrainer_xgboost.py",
    "python scripts/entrainer_lightgbm_reco.py",
    "python scripts/entrainer_knn.py",
]

if __name__ == '__main__':
    os.makedirs('models', exist_ok=True)
    for cmd in SCRIPTS:
        print(f"[RUN] {cmd}")
        rc = subprocess.call(cmd, shell=True)
        if rc != 0:
            print(f"[ERR] Command failed: {cmd} (exit {rc})", file=sys.stderr)
            sys.exit(rc)
    print("[DONE] Tous les modèles entraînés et sauvegardés dans models/")
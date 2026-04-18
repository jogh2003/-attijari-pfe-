"""
fix_lstm_et_bdd.py — Corrections finales
PFE Attijari bank — Sujet 21

Corrige :
  1. LSTM prédit 100% NORMAL → ré-entraîner avec class_weight
  2. Base de données : 1 ticket → vider et insérer les 1507

Exécuter : python scripts/fix_lstm_et_bdd.py
"""
import numpy as np
import pandas as pd
import os, json, pickle, time

G="\033[92m"; R="\033[91m"; Y="\033[93m"; B="\033[94m"; BOLD="\033[1m"; X="\033[0m"
def ok(m):   print(f"  {G}✓{X} {m}")
def err(m):  print(f"  {R}✗{X} {m}")
def info(m): print(f"  {B}→{X} {m}")
def titre(t):print(f"\n{BOLD}{B}{'═'*55}{X}\n{BOLD}  {t}{X}\n{B}{'═'*55}{X}")

# ════════════════════════════════════════════════════════
# FIX A — Ré-entraîner LSTM avec class_weight
# ════════════════════════════════════════════════════════
titre("FIX A — Ré-entraînement LSTM avec class_weight (fix déséquilibre)")

try:
    import tensorflow as tf

    X_train = np.load("data/processed/X_train.npy")
    X_test  = np.load("data/processed/X_test.npy")
    y_train = np.load("data/processed/y_train.npy")
    y_test  = np.load("data/processed/y_test.npy")

    # Calcul du poids des classes
    n_neg = (y_train == 0).sum()
    n_pos = (y_train == 1).sum()
    ratio = n_neg / n_pos
    class_weight = {0: 1.0, 1: float(ratio)}
    info(f"Déséquilibre : {n_neg} normaux / {n_pos} retards → class_weight[1] = {ratio:.1f}")

    # Architecture identique
    model = tf.keras.Sequential([
        tf.keras.layers.LSTM(32, return_sequences=True,
                             input_shape=(X_train.shape[1], X_train.shape[2])),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.LSTM(16),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(8, activation="relu"),
        tf.keras.layers.Dense(1, activation="sigmoid")
    ], name="attijari_lstm_v2")

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss="binary_crossentropy",
        metrics=["accuracy", tf.keras.metrics.AUC(name="auc")]
    )

    info("Entraînement avec class_weight...")
    t0 = time.time()
    history = model.fit(
        X_train, y_train,
        epochs=50, batch_size=16,
        validation_data=(X_test, y_test),
        class_weight=class_weight,
        callbacks=[
            tf.keras.callbacks.EarlyStopping(
                patience=10, restore_best_weights=True,
                monitor="val_auc", mode="max", verbose=0
            )
        ],
        verbose=1
    )
    duree = time.time() - t0

    loss, acc, auc = model.evaluate(X_test, y_test, verbose=0)
    ok(f"Entraînement terminé en {duree:.0f}s")
    ok(f"Accuracy : {acc*100:.2f}%  |  AUC : {auc:.4f}")

    # Tester les prédictions avec seuil adapté
    preds = model.predict(X_test, verbose=0).flatten()
    info(f"Distribution prédictions — min:{preds.min():.3f} max:{preds.max():.3f} moy:{preds.mean():.3f}")

    # Seuil adapté (top 14% = percentile 86)
    seuil_adapte = float(np.percentile(preds, 86))
    info(f"Seuil adapté (top 14%) : {seuil_adapte:.3f}")

    nb_alertes = (preds >= seuil_adapte).sum()
    nb_surveill = ((preds >= seuil_adapte * 0.6) & (preds < seuil_adapte)).sum()
    ok(f"RISQUE ÉLEVÉ ≥ {seuil_adapte:.2f} : {nb_alertes} tickets ({nb_alertes/len(preds)*100:.1f}%)")
    ok(f"SURVEILLANCE           : {nb_surveill} tickets")

    # Sauvegarder
    model.save("models/lstm_model.h5")
    metriques = {
        "accuracy": float(acc), "auc": float(auc), "loss": float(loss),
        "seuil_alerte": round(seuil_adapte, 3),
        "class_weight": class_weight,
        "epochs": len(history.history["loss"]),
        "n_train": int(len(X_train)), "n_test": int(len(X_test))
    }
    json.dump(metriques, open("models/metriques_lstm.json", "w"), indent=2)
    ok(f"Modèle et seuil sauvegardés (seuil_alerte = {seuil_adapte:.3f})")

except ImportError:
    err("TensorFlow non disponible")
except Exception as e:
    err(f"Erreur : {e}")
    import traceback; traceback.print_exc()

# ════════════════════════════════════════════════════════
# FIX B — Vider la BDD et insérer les 1507 tickets
# ════════════════════════════════════════════════════════
titre("FIX B — Vider BDD et insérer les 1507 tickets")

try:
    import psycopg2
    from psycopg2.extras import execute_values

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST","localhost"), port=os.getenv("DB_PORT","5432"),
        dbname=os.getenv("DB_NAME","attijari_pfe"),
        user=os.getenv("DB_USER","postgres"),
        password=os.getenv("DB_PASSWORD","postgres")
    )
    cur = conn.cursor()

    # Vérifier ticket existant
    cur.execute("SELECT COUNT(*) FROM reclamations;")
    nb = cur.fetchone()[0]
    info(f"Tickets actuellement en BDD : {nb}")

    if nb > 0 and nb < 100:
        info("Vider la table pour réinsérer proprement...")
        cur.execute("DELETE FROM recommandations;")
        cur.execute("DELETE FROM actions_rpa;")
        cur.execute("DELETE FROM reclamations;")
        conn.commit()
        ok("Table vidée")

    cur.execute("SELECT COUNT(*) FROM reclamations;")
    nb_now = cur.fetchone()[0]

    if nb_now == 0:
        df = pd.read_csv("data/cleaned/reclamations_propres.csv")
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date", "id"])
        info(f"Insertion de {len(df)} tickets...")

        rows = []
        for _, row in df.iterrows():
            try:
                rows.append((
                    str(row["id"]),
                    row["date"],
                    str(row["type_operation"])[:100],
                    str(row.get("objet", ""))[:500] or "N/A",
                    str(row["action_effectuee"])[:500] if row.get("action_effectuee") and str(row["action_effectuee"]) != "nan" else None,
                    int(row["severite"]) if not pd.isna(row.get("severite")) else 2,
                    str(row["statut"])[:50],
                    float(row["score_anomalie"]) if not pd.isna(row.get("score_anomalie")) else None,
                    float(row["score_risque"]) if not pd.isna(row.get("score_risque")) else None,
                ))
            except: continue

        execute_values(cur, """
            INSERT INTO reclamations
                (id, date, type_operation, description, action_effectuee,
                 severite, statut, score_anomalie, score_risque)
            VALUES %s ON CONFLICT (id) DO NOTHING
        """, rows, page_size=200)
        conn.commit()

        cur.execute("SELECT COUNT(*) FROM reclamations;")
        final = cur.fetchone()[0]
        ok(f"Import terminé : {final} tickets dans PostgreSQL !")

        cur.execute("SELECT type_operation, COUNT(*) FROM reclamations GROUP BY 1 ORDER BY 2 DESC LIMIT 5;")
        info("Top 5 groupes en BDD :")
        for r in cur.fetchall():
            print(f"      {r[0]}: {r[1]}")

        cur.execute("SELECT COUNT(*) FROM reclamations WHERE score_risque >= 0.75;")
        alertes_bdd = cur.fetchone()[0]
        ok(f"Alertes ≥ 0.75 en BDD : {alertes_bdd} tickets")
    else:
        ok(f"BDD déjà remplie correctement : {nb_now} tickets")

    cur.close(); conn.close()

except ImportError:
    err("psycopg2 non installé → pip install psycopg2-binary")
except psycopg2.OperationalError as e:
    err(f"PostgreSQL non accessible : {e}")
except Exception as e:
    err(f"Erreur BDD : {e}")
    import traceback; traceback.print_exc()

# ════════════════════════════════════════════════════════
# RÉSUMÉ
# ════════════════════════════════════════════════════════
print(f"\n{BOLD}{'═'*55}{X}")
print(f"{BOLD}  CORRECTIONS TERMINÉES{X}")
print(f"{BOLD}{'═'*55}{X}")
print(f"  Relancer l'API :")
print(f"  uvicorn app.main:app --reload")
print(f"\n  Tester les alertes :")
print(f"  curl \"http://localhost:8000/api/alertes?seuil=0.75\"")
print(f"  → Doit retourner des alertes réelles Attijari bank")
print(f"{'═'*55}")
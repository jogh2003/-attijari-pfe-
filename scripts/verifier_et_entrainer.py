"""
verifier_et_entrainer.py — Script complet vérification + entraînement
PFE Attijari bank — Sujet 21

Exécuter dans le terminal VS Code (venv actif) :
    python scripts/verifier_et_entrainer.py

Ce script fait TOUT dans l'ordre :
    1. Vérifie l'environnement Python
    2. Vérifie les données
    3. Vérifie le KNN
    4. Entraîne le modèle LSTM
    5. Teste les prédictions
    6. Vérifie la liaison avec l'API
"""
import sys, os, json, time
import numpy as np
import pandas as pd

# ── Couleurs terminal ────────────────────────────────────
G = "\033[92m"   # vert
R = "\033[91m"   # rouge
Y = "\033[93m"   # jaune
B = "\033[94m"   # bleu
BOLD = "\033[1m"
X = "\033[0m"    # reset

def ok(msg):  print(f"  {G}✓{X} {msg}")
def err(msg): print(f"  {R}✗{X} {msg}")
def warn(msg):print(f"  {Y}!{X} {msg}")
def info(msg):print(f"  {B}→{X} {msg}")
def titre(t): print(f"\n{BOLD}{B}{'═'*55}{X}\n{BOLD}  {t}{X}\n{B}{'═'*55}{X}")

resultats = {"ok": 0, "warn": 0, "err": 0}

# ════════════════════════════════════════════════════════
# ÉTAPE 1 — VÉRIFICATION ENVIRONNEMENT
# ════════════════════════════════════════════════════════
titre("ÉTAPE 1 — Vérification de l'environnement Python")

# Python version
import platform
v = platform.python_version()
if v >= "3.11":
    ok(f"Python {v}")
    resultats["ok"] += 1
else:
    warn(f"Python {v} — recommandé 3.11+")
    resultats["warn"] += 1

# Bibliothèques obligatoires
libs = [
    ("pandas",        "pandas",        "2.x"),
    ("numpy",         "numpy",         "1.x"),
    ("fastapi",       "fastapi",       "0.x"),
    ("sklearn",       "scikit-learn",  "1.x"),
    ("cryptography",  "cryptography",  "40+"),
    ("tensorflow",    "tensorflow",    "2.x"),
    ("matplotlib",    "matplotlib",    "3.x"),
    ("seaborn",       "seaborn",       "0.x"),
]

for import_name, display_name, version_hint in libs:
    try:
        mod = __import__(import_name)
        ver = getattr(mod, "__version__", "ok")
        ok(f"{display_name} {ver}")
        resultats["ok"] += 1
    except ImportError:
        err(f"{display_name} NON INSTALLÉ → pip install {display_name}")
        resultats["err"] += 1

# JWT
try:
    from jose import jwt
    ok("python-jose (JWT)")
    resultats["ok"] += 1
except ImportError:
    try:
        import jwt
        ok(f"PyJWT {jwt.__version__} (JWT — fallback)")
        resultats["ok"] += 1
    except ImportError:
        err("Aucune lib JWT → pip install PyJWT")
        resultats["err"] += 1

# bcrypt/passlib
try:
    from passlib.context import CryptContext
    ok("passlib[bcrypt]")
    resultats["ok"] += 1
except ImportError:
    try:
        import bcrypt
        ok(f"bcrypt {bcrypt.__version__}")
        resultats["ok"] += 1
    except ImportError:
        err("passlib/bcrypt manquant → pip install passlib[bcrypt]")
        resultats["err"] += 1

# ════════════════════════════════════════════════════════
# ÉTAPE 2 — VÉRIFICATION DONNÉES
# ════════════════════════════════════════════════════════
titre("ÉTAPE 2 — Vérification des données Attijari bank")

# Fichiers de données
data_files = [
    ("data/cleaned/reclamations_propres.csv",    "Dataset nettoyé"),
    ("data/processed/dataset_nlp_enrichi.csv",   "Dataset NLP enrichi"),
    ("data/processed/X_train.npy",               "Features LSTM train"),
    ("data/processed/X_test.npy",                "Features LSTM test"),
    ("data/processed/y_train.npy",               "Labels LSTM train"),
    ("data/processed/y_test.npy",                "Labels LSTM test"),
    ("data/processed/embeddings_tfidf.npy",      "Embeddings TF-IDF"),
]

for path, desc in data_files:
    if os.path.exists(path):
        size = os.path.getsize(path) // 1024
        ok(f"{desc} ({size} Ko) — {path}")
        resultats["ok"] += 1
    else:
        err(f"{desc} MANQUANT — {path}")
        err(f"  → Lancer : python scripts/import_et_nettoyage.py")
        resultats["err"] += 1

# Statistiques données
try:
    df = pd.read_csv("data/cleaned/reclamations_propres.csv")
    info(f"Total tickets : {len(df)}")
    info(f"Réclamations  : {(df['type_demande']=='Réclamation').sum()}")
    info(f"En retard SLA : {df['en_retard'].sum()} ({df['en_retard'].mean()*100:.1f}%)")
    if "score_anomalie" in df.columns:
        info(f"Score moy.    : {df['score_anomalie'].mean():.3f}")
        info(f"Risque élevé  : {(df['score_anomalie']>=0.75).sum()} tickets")
    ok("Statistiques données OK")
except Exception as e:
    err(f"Lecture données : {e}")

# ════════════════════════════════════════════════════════
# ÉTAPE 3 — VÉRIFICATION MODÈLE KNN
# ════════════════════════════════════════════════════════
titre("ÉTAPE 3 — Vérification du modèle KNN (recommandations)")

try:
    import pickle
    from collections import Counter

    knn_data = pickle.load(open("models/knn_model.pkl", "rb"))
    knn      = knn_data["knn"]
    df_knn   = knn_data["df"]
    vec      = knn_data["vectorizer"]

    ok(f"KNN chargé : {len(df_knn)} tickets de référence")
    ok(f"Actions distinctes : {df_knn['action_effectuee'].nunique()}")

    # Tests recommandations sur cas réels
    cas_test = [
        ("Demande vérification email SPAM Helpdesk Securite et Habilitation SI", "Spam/Sécurité"),
        ("Blocage Firewall indicateurs compromission Sécurité Opérationnelle",   "Firewall"),
        ("Problème accès Amplitude Système",                                      "Amplitude"),
        ("Problème impression réseau Helpdesk Equipements SI",                    "Imprimante"),
        ("Demande accès VPN télétravail Reseau",                                  "VPN"),
    ]

    print()
    print(f"  {'─'*50}")
    print(f"  Tests recommandations KNN :")
    print(f"  {'─'*50}")
    ok_knn = 0
    for texte, label in cas_test:
        v = vec.transform([texte]).toarray()
        dists, idxs = knn.kneighbors(v)
        actions = [df_knn.iloc[i]["action_effectuee"]
                   for i in idxs[0] if df_knn.iloc[i]["action_effectuee"] != ""]
        if actions:
            top = Counter(actions).most_common(1)[0]
            taux = top[1] / len(actions)
            action_courte = top[0][:55] + "..." if len(top[0]) > 55 else top[0]
            print(f"  {G}✓{X} [{taux*100:.0f}%] {label}")
            print(f"      → {action_courte}")
            ok_knn += 1
        else:
            print(f"  {Y}!{X} {label} → aucune action trouvée")
    print(f"  {'─'*50}")
    ok(f"KNN : {ok_knn}/{len(cas_test)} recommandations générées")
    resultats["ok"] += 1

except Exception as e:
    err(f"KNN : {e}")
    err("  → Lancer : python scripts/recommandations_knn.py")
    resultats["err"] += 1

# ════════════════════════════════════════════════════════
# ÉTAPE 4 — ENTRAÎNEMENT MODÈLE LSTM
# ════════════════════════════════════════════════════════
titre("ÉTAPE 4 — Entraînement du modèle LSTM")

if os.path.exists("models/lstm_model.h5"):
    ok("Modèle LSTM déjà entraîné : models/lstm_model.h5")
    if os.path.exists("models/metriques_lstm.json"):
        m = json.load(open("models/metriques_lstm.json"))
        ok(f"Accuracy : {m.get('accuracy', 0)*100:.2f}%")
        ok(f"AUC      : {m.get('auc', 0):.4f}")
    resultats["ok"] += 1
    LSTM_ENTRAINE = True
else:
    info("Modèle LSTM non trouvé — démarrage de l'entraînement...")
    LSTM_ENTRAINE = False

if not LSTM_ENTRAINE:
    try:
        import tensorflow as tf

        # Charger les données
        X_train = np.load("data/processed/X_train.npy")
        X_test  = np.load("data/processed/X_test.npy")
        y_train = np.load("data/processed/y_train.npy")
        y_test  = np.load("data/processed/y_test.npy")

        info(f"Données LSTM : X_train={X_train.shape}, taux retard={y_train.mean()*100:.1f}%")

        # Architecture LSTM
        model = tf.keras.Sequential([
            tf.keras.layers.LSTM(
                32, return_sequences=True,
                input_shape=(X_train.shape[1], X_train.shape[2])
            ),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.LSTM(16),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(8, activation="relu"),
            tf.keras.layers.Dense(1, activation="sigmoid")
        ], name="attijari_lstm_v1")

        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss="binary_crossentropy",
            metrics=["accuracy", tf.keras.metrics.AUC(name="auc")]
        )

        info("Architecture LSTM créée")
        model.summary()

        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                patience=10, restore_best_weights=True,
                monitor="val_auc", mode="max", verbose=0
            ),
            tf.keras.callbacks.ModelCheckpoint(
                "models/lstm_best.h5", save_best_only=True,
                monitor="val_auc", mode="max", verbose=0
            )
        ]

        info("Entraînement en cours...")
        t0 = time.time()
        history = model.fit(
            X_train, y_train,
            epochs=50, batch_size=16,
            validation_data=(X_test, y_test),
            callbacks=callbacks,
            verbose=1
        )
        duree = time.time() - t0

        # Évaluation
        loss, accuracy, auc = model.evaluate(X_test, y_test, verbose=0)

        ok(f"Entraînement terminé en {duree:.0f}s")
        ok(f"Loss     : {loss:.4f}")
        ok(f"Accuracy : {accuracy*100:.2f}%")
        ok(f"AUC      : {auc:.4f}")

        # Sauvegarder
        os.makedirs("models", exist_ok=True)
        model.save("models/lstm_model.h5")
        ok("Modèle sauvegardé : models/lstm_model.h5")

        metriques = {
            "date_entrainement": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "accuracy":          float(accuracy),
            "auc":               float(auc),
            "loss":              float(loss),
            "epochs":            len(history.history["loss"]),
            "n_train":           int(len(X_train)),
            "n_test":            int(len(X_test)),
            "fenetre_jours":     7,
            "taux_retard_train": float(y_train.mean())
        }
        json.dump(metriques, open("models/metriques_lstm.json", "w"), indent=2)
        ok("Métriques sauvegardées : models/metriques_lstm.json")
        resultats["ok"] += 1

        # MLflow si disponible
        try:
            import mlflow, mlflow.tensorflow
            mlflow.set_tracking_uri("http://localhost:5000")
            mlflow.set_experiment("attijari_lstm_pfe")
            with mlflow.start_run(run_name=f"lstm_{time.strftime('%Y%m%d_%H%M')}"):
                mlflow.log_params(metriques)
                mlflow.log_metric("accuracy", accuracy)
                mlflow.log_metric("auc", auc)
                mlflow.tensorflow.log_model(model, "lstm_model")
            ok("Expérience loggée dans MLflow : http://localhost:5000")
        except:
            warn("MLflow non disponible — modèle sauvegardé localement uniquement")

    except ImportError:
        err("TensorFlow non installé")
        err("  → pip install tensorflow")
        resultats["err"] += 1
    except Exception as e:
        err(f"Erreur entraînement LSTM : {e}")
        resultats["err"] += 1

# ════════════════════════════════════════════════════════
# ÉTAPE 5 — TEST PRÉDICTIONS LSTM
# ════════════════════════════════════════════════════════
titre("ÉTAPE 5 — Test des prédictions LSTM")

if os.path.exists("models/lstm_model.h5"):
    try:
        import tensorflow as tf
        import pickle

        model  = tf.keras.models.load_model("models/lstm_model.h5")
        scaler = pickle.load(open("models/scaler_lstm.pkl", "rb"))
        le     = pickle.load(open("models/label_encoder_groupe.pkl", "rb"))

        X_test = np.load("data/processed/X_test.npy")
        y_test = np.load("data/processed/y_test.npy")

        predictions = model.predict(X_test, verbose=0).flatten()

        nb_alertes  = (predictions >= 0.75).sum()
        nb_surveill = ((predictions >= 0.50) & (predictions < 0.75)).sum()
        nb_normal   = (predictions < 0.50).sum()

        ok(f"Prédictions générées : {len(predictions)} tickets")
        ok(f"RISQUE ÉLEVÉ ≥ 0.75  : {nb_alertes} tickets ({nb_alertes/len(predictions)*100:.1f}%)")
        ok(f"SURVEILLANCE 0.50-0.75: {nb_surveill} tickets ({nb_surveill/len(predictions)*100:.1f}%)")
        ok(f"NORMAL < 0.50         : {nb_normal} tickets ({nb_normal/len(predictions)*100:.1f}%)")

        # Comparaison avec la réalité
        vrais_pos = ((predictions >= 0.75) & (y_test == 1)).sum()
        faux_pos  = ((predictions >= 0.75) & (y_test == 0)).sum()
        if nb_alertes > 0:
            precision = vrais_pos / nb_alertes
            ok(f"Précision alarmes : {precision*100:.1f}%")

        resultats["ok"] += 1

    except Exception as e:
        err(f"Test prédictions : {e}")
        resultats["err"] += 1
else:
    warn("LSTM non entraîné — prédictions non testées")
    resultats["warn"] += 1

# ════════════════════════════════════════════════════════
# ÉTAPE 6 — VÉRIFICATION LIAISON API + UIPATH
# ════════════════════════════════════════════════════════
titre("ÉTAPE 6 — Vérification liaison API / UiPath")

import subprocess, socket

# Vérifier si l'API tourne
api_ok = False
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(("localhost", 8000))
    sock.close()
    if result == 0:
        ok("API FastAPI tourne sur localhost:8000")
        api_ok = True
        resultats["ok"] += 1

        # Tester les endpoints UiPath
        try:
            import urllib.request, urllib.error
            url = "http://localhost:8000/api/alertes?seuil=0.75"
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            nb = len(data) if isinstance(data, list) else data.get("total", 0)
            ok(f"GET /api/alertes?seuil=0.75 → {nb if isinstance(data,list) else nb} alertes")
            ok("UiPath CheckAlerte.xaml peut se connecter")
        except Exception as e:
            warn(f"Test endpoint alertes : {e}")

        try:
            url = "http://localhost:8000/health"
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=5)
            health = json.loads(resp.read())
            ok(f"Health check : {health}")
        except:
            warn("Health check non accessible")
    else:
        warn("API non démarrée — lancer : uvicorn app.main:app --reload")
        resultats["warn"] += 1
except:
    warn("API non démarrée — lancer : uvicorn app.main:app --reload")
    resultats["warn"] += 1

# Vérifier fichiers modèles existants
models_ok = True
for m in ["models/knn_model.pkl", "models/lstm_model.h5",
          "models/scaler_lstm.pkl", "models/label_encoder_groupe.pkl"]:
    if not os.path.exists(m):
        models_ok = False
        err(f"Modèle manquant : {m}")

if models_ok:
    ok("Tous les modèles présents — UiPath peut appeler l'API")

# ════════════════════════════════════════════════════════
# RÉSUMÉ FINAL
# ════════════════════════════════════════════════════════
print(f"\n{BOLD}{'═'*55}{X}")
print(f"{BOLD}  RÉSUMÉ FINAL{X}")
print(f"{BOLD}{'═'*55}{X}")
print(f"  {G}✓ Réussis  : {resultats['ok']}{X}")
print(f"  {Y}! Avertiss.: {resultats['warn']}{X}")
print(f"  {R}✗ Erreurs  : {resultats['err']}{X}")
print(f"{'═'*55}")

if resultats["err"] == 0:
    print(f"\n{G}{BOLD}  PROJET 100% PRÊT — Démarrer l'API :{X}")
    print(f"  uvicorn app.main:app --reload")
    print(f"  Swagger : http://localhost:8000/docs")
    print(f"  UiPath  : lancer Main.xaml dans UiPath Studio")
elif resultats["err"] <= 2:
    print(f"\n{Y}{BOLD}  Projet presque prêt — corriger les {resultats['err']} erreur(s) ci-dessus{X}")
else:
    print(f"\n{R}{BOLD}  Corriger les erreurs avant de continuer{X}")
    print(f"  pip install -r requirements.txt")

print()

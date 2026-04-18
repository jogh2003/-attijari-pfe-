"""
entrainer_lstm.py — Entraînement modèle LSTM sur données réelles Attijari bank
PFE Sujet 21

Données : 1 507 tickets uniques Février–Mars 2026
Features : groupe, priorité, en_retard, durée_résolution, score_anomalie
Cible    : prédire si un ticket sera en retard SLA (en_retard = True)
Exécuter : python scripts/entrainer_lstm.py
"""
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime

os.makedirs("models", exist_ok=True)
os.makedirs("mlruns", exist_ok=True)

def charger_features():
    path = "data/processed/features_lstm.csv"
    if not os.path.exists(path):
        print("ERREUR : lancer d'abord pipeline_nlp.py")
        exit(1)
    df = pd.read_csv(path, on_bad_lines='skip')
    print(f"Features chargées : {len(df)} lignes")
    return df

def preparer_sequences(df, fenetre=7):
    """
    Prépare des séquences temporelles pour le LSTM.

    Avec 1507 tickets sur 2 mois (~60 jours), on crée des séquences
    de 7 jours glissants (fenêtre plus petite car moins de données).

    Features par ticket :
    - severite (1-4) normalisée
    - en_retard (0/1)
    - duree_resolution_min normalisée
    - score_anomalie (0-1)
    - groupe encodé

    Target : en_retard (prédire si le prochain ticket sera en retard)
    """
    print(f"\nPréparation séquences (fenêtre={fenetre} jours)...")

    # Encoder les groupes
    from sklearn.preprocessing import LabelEncoder, MinMaxScaler

    df['date_dt'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date_dt']).sort_values('date_dt').reset_index(drop=True)

    # Encoder le groupe (type_operation)
    le = LabelEncoder()
    df['groupe_enc'] = le.fit_transform(df['type_operation'].fillna('Inconnu'))

    # Normaliser les features numériques
    scaler = MinMaxScaler()
    features_num = ['severite', 'duree_resolution_min', 'score_anomalie', 'groupe_enc']
    df[features_num] = df[features_num].fillna(0)
    df[features_num] = scaler.fit_transform(df[features_num])

    # Sauvegarder l'encodeur et le scaler pour l'inférence
    import pickle
    with open("models/label_encoder_groupe.pkl", "wb") as f:
        pickle.dump(le, f)
    with open("models/scaler_lstm.pkl", "wb") as f:
        pickle.dump(scaler, f)

    # Features finales
    feature_cols = ['severite', 'en_retard', 'duree_resolution_min',
                    'score_anomalie', 'groupe_enc']
    df['en_retard'] = df['en_retard'].astype(float)

    X_data = df[feature_cols].values.astype(np.float32)
    y_data = df['en_retard'].values.astype(np.float32)

    # Créer les séquences
    X, y = [], []
    for i in range(fenetre, len(X_data)):
        X.append(X_data[i-fenetre:i])
        y.append(y_data[i])

    X = np.array(X)
    y = np.array(y)

    print(f"  Séquences créées : X={X.shape}, y={y.shape}")
    print(f"  Taux en retard (target) : {y.mean()*100:.1f}%")

    return X, y, scaler, le

def construire_lstm(input_shape):
    """Architecture LSTM adaptée aux données Attijari bank"""
    import tensorflow as tf

    model = tf.keras.Sequential([
        tf.keras.layers.LSTM(
            32, return_sequences=True,
            input_shape=input_shape,
            name="lstm_1"
        ),
        tf.keras.layers.Dropout(0.2, name="dropout_1"),
        tf.keras.layers.LSTM(16, name="lstm_2"),
        tf.keras.layers.Dropout(0.2, name="dropout_2"),
        tf.keras.layers.Dense(8, activation='relu', name="dense_1"),
        tf.keras.layers.Dense(1, activation='sigmoid', name="output")
    ], name="attijari_lstm_v1")

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss='binary_crossentropy',
        metrics=['accuracy', tf.keras.metrics.AUC(name='auc')]
    )
    return model

def entrainer():
    print("=" * 60)
    print("  Entraînement LSTM — Attijari bank 2026")
    print("=" * 60)

    df = charger_features()

    # ── Préparer les séquences ────────────────────────────────
    FENETRE = 7  # 7 tickets glissants (adapté aux 1507 tickets disponibles)
    X, y, scaler, le = preparer_sequences(df, fenetre=FENETRE)

    if len(X) < 50:
        print("ATTENTION : pas assez de données pour l'entraînement LSTM.")
        print(f"  Séquences disponibles : {len(X)}")
        print("  Attendez d'avoir plus de données ou réduisez la fenêtre.")
        return None

    # ── Split train/test 80/20 ────────────────────────────────
    split = int(len(X) * 0.80)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    print(f"\nDonnées d'entraînement : {X_train.shape}")
    print(f"Données de test        : {X_test.shape}")

    # ── MLflow tracking ───────────────────────────────────────
    mlflow_ok = False
    try:
        import mlflow
        import mlflow.tensorflow
        mlflow.set_tracking_uri("http://localhost:5000")
        mlflow.set_experiment("attijari_lstm_pfe")
        mlflow_ok = True
        print("\nMLflow connecté : http://localhost:5000")
    except:
        print("\nMLflow non disponible — entraînement sans tracking")

    # ── Construire et entraîner le modèle ─────────────────────
    try:
        import tensorflow as tf

        run_context = mlflow.start_run(run_name=f"lstm_{datetime.now().strftime('%Y%m%d_%H%M')}") if mlflow_ok else None

        if run_context:
            run_context.__enter__()

        print("\n[1/3] Construction du modèle LSTM...")
        model = construire_lstm(input_shape=(X_train.shape[1], X_train.shape[2]))
        model.summary()

        if mlflow_ok:
            mlflow.log_params({
                "fenetre_jours": FENETRE,
                "n_features": X_train.shape[2],
                "architecture": "LSTM(32) -> Dropout -> LSTM(16) -> Dropout -> Dense(8) -> Sigmoid",
                "optimizer": "Adam",
                "learning_rate": 0.001,
                "batch_size": 32,
                "epochs_max": 50,
                "n_train_samples": len(X_train),
                "n_test_samples": len(X_test),
                "taux_retard_train": float(y_train.mean())
            })

        print("\n[2/3] Entraînement...")
        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                patience=10, restore_best_weights=True,
                monitor='val_auc', mode='max', verbose=1
            ),
            tf.keras.callbacks.ModelCheckpoint(
                "models/lstm_best.h5", save_best_only=True,
                monitor='val_auc', mode='max', verbose=0
            )
        ]

        history = model.fit(
            X_train, y_train,
            epochs=50, batch_size=32,
            validation_data=(X_test, y_test),
            callbacks=callbacks,
            verbose=1
        )

        print("\n[3/3] Évaluation du modèle...")
        loss, accuracy, auc = model.evaluate(X_test, y_test, verbose=0)

        print(f"\n  Loss       : {loss:.4f}")
        print(f"  Accuracy   : {accuracy*100:.2f}%")
        print(f"  AUC        : {auc:.4f}")

        if mlflow_ok:
            mlflow.log_metrics({
                "test_loss":     loss,
                "test_accuracy": accuracy,
                "test_auc":      auc,
                "epochs_trained": len(history.history['loss'])
            })
            mlflow.tensorflow.log_model(model, "lstm_model")

        # Sauvegarder le modèle final
        model.save("models/lstm_model.h5")
        print(f"\n  Modèle sauvegardé : models/lstm_model.h5")

        # Sauvegarder les métriques
        metriques = {
            "date_entrainement": datetime.now().isoformat(),
            "n_samples_train":   int(len(X_train)),
            "n_samples_test":    int(len(X_test)),
            "fenetre_jours":     FENETRE,
            "loss":              float(loss),
            "accuracy":          float(accuracy),
            "auc":               float(auc),
            "epochs":            len(history.history['loss']),
            "seuil_risque":      0.75
        }
        with open("models/metriques_lstm.json", "w") as f:
            json.dump(metriques, f, indent=2, ensure_ascii=False)

        if mlflow_ok and run_context:
            run_context.__exit__(None, None, None)

        print("\n" + "=" * 60)
        print("  RÉSULTATS LSTM")
        print("=" * 60)
        print(f"  Accuracy    : {accuracy*100:.2f}%")
        print(f"  AUC         : {auc:.4f}")
        print(f"  Modèle      : models/lstm_model.h5")
        print(f"  Métriques   : models/metriques_lstm.json")
        print("=" * 60)
        print("\nProchaine étape : python scripts/recommandations_knn.py")

        return model, metriques

    except ImportError:
        print("TensorFlow non installé. Exécuter : pip install tensorflow")
        return None, None

if __name__ == "__main__":
    entrainer()

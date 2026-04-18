-- ============================================================
-- init_database.sql — PFE Attijari bank — Sujet 21
-- Exécuter dans VS Code : clic droit → Run Query
-- OU dans le terminal : psql -U postgres -f init_database.sql
-- ============================================================

-- ── Étape 1 : Créer la base de données ──────────────────────
-- (Exécuter cette ligne SEULE d'abord si la base n'existe pas)
CREATE DATABASE attijari_pfe;

-- ============================================================
-- Après avoir créé la base, changer la connexion VS Code
-- vers "attijari_pfe" puis exécuter le reste
-- ============================================================

-- ── Étape 2 : Créer les tables ──────────────────────────────

-- Table principale : réclamations bancaires
CREATE TABLE IF NOT EXISTS reclamations (
    id              VARCHAR(36)  PRIMARY KEY,
    date            TIMESTAMP    NOT NULL,
    type_operation  VARCHAR(100) NOT NULL,
    description     TEXT         NOT NULL,        -- chiffré AES-256
    action_effectuee TEXT        NULL,             -- colonne CLÉ pour recommandations
    severite        INTEGER      NOT NULL DEFAULT 1,
    statut          VARCHAR(50)  NOT NULL DEFAULT 'soumise',
    score_anomalie  FLOAT        NULL,
    score_risque    FLOAT        NULL,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP    NULL
);

-- Index pour accélérer les recherches fréquentes
CREATE INDEX IF NOT EXISTS idx_reclamations_date          ON reclamations(date);
CREATE INDEX IF NOT EXISTS idx_reclamations_type          ON reclamations(type_operation);
CREATE INDEX IF NOT EXISTS idx_reclamations_statut        ON reclamations(statut);
CREATE INDEX IF NOT EXISTS idx_reclamations_score_risque  ON reclamations(score_risque);

-- Table : utilisateurs du système
CREATE TABLE IF NOT EXISTS utilisateurs (
    id           VARCHAR(36)  PRIMARY KEY,
    nom          VARCHAR(100) NOT NULL,
    email        VARCHAR(150) NOT NULL UNIQUE,
    mot_de_passe VARCHAR(255) NOT NULL,
    role         VARCHAR(50)  NOT NULL DEFAULT 'utilisateur',
    est_actif    BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_utilisateurs_email ON utilisateurs(email);

-- Table : rôles et permissions (sécurité RBAC)
CREATE TABLE IF NOT EXISTS roles (
    id          VARCHAR(36)  PRIMARY KEY,
    libelle     VARCHAR(50)  NOT NULL UNIQUE,
    permissions TEXT[]       NOT NULL DEFAULT '{}'
);

-- Table : audit trail (traçabilité obligatoire bancaire)
CREATE TABLE IF NOT EXISTS audit_logs (
    id              VARCHAR(36)  PRIMARY KEY,
    utilisateur     VARCHAR(150) NULL,       -- email ou identifiant de l'utilisateur
    utilisateur_id  VARCHAR(36)  NULL,       -- UUID si disponible
    role            VARCHAR(50)  NULL,       -- rôle de l'utilisateur
    action          VARCHAR(200) NOT NULL,
    details         TEXT         NULL,
    ip_address      VARCHAR(50)  NULL,
    timestamp       TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp       ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_utilisateur     ON audit_logs(utilisateur_id);
CREATE INDEX IF NOT EXISTS idx_audit_action          ON audit_logs(action);

-- Table : prédictions du modèle LSTM
CREATE TABLE IF NOT EXISTS predictions (
    id                  VARCHAR(36)  PRIMARY KEY,
    date_prediction     TIMESTAMP    NOT NULL DEFAULT NOW(),
    type_operation      VARCHAR(100) NOT NULL,
    score_risque        FLOAT        NOT NULL,
    est_alerte          BOOLEAN      NOT NULL DEFAULT FALSE,
    version_modele      VARCHAR(50)  NULL,
    fenetre_jours       INTEGER      NOT NULL DEFAULT 30
);

CREATE INDEX IF NOT EXISTS idx_predictions_date    ON predictions(date_prediction DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_alerte  ON predictions(est_alerte);

-- Table : recommandations générées
CREATE TABLE IF NOT EXISTS recommandations (
    id                  VARCHAR(36)  PRIMARY KEY,
    reclamation_id      VARCHAR(36)  NOT NULL REFERENCES reclamations(id),
    action_suggeree     TEXT         NOT NULL,
    taux_succes         FLOAT        NOT NULL DEFAULT 0.0,
    nb_cas_similaires   INTEGER      NOT NULL DEFAULT 0,
    priorite            INTEGER      NOT NULL DEFAULT 2,
    statut_impl         VARCHAR(50)  NOT NULL DEFAULT 'en_attente',
    created_at          TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recommandations_reclamation ON recommandations(reclamation_id);

-- Table : actions RPA exécutées
CREATE TABLE IF NOT EXISTS actions_rpa (
    id               VARCHAR(36)  PRIMARY KEY,
    recommandation_id VARCHAR(36) NOT NULL REFERENCES recommandations(id),
    type_action      VARCHAR(200) NOT NULL,
    statut           VARCHAR(50)  NOT NULL DEFAULT 'en_attente',
    resultat         TEXT         NULL,
    execute_par      VARCHAR(50)  NOT NULL DEFAULT 'robot_uipath',
    execute_le       TIMESTAMP    NULL,
    created_at       TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ── Étape 3 : Insérer les données de démarrage ──────────────

-- Rôles par défaut
INSERT INTO roles (id, libelle, permissions) VALUES
    ('role-001', 'admin',         ARRAY['read', 'write', 'delete', 'manage_users', 'view_audit']),
    ('role-002', 'responsable_it', ARRAY['read', 'write', 'validate_rpa', 'view_dashboard']),
    ('role-003', 'utilisateur',   ARRAY['read', 'submit_reclamation'])
ON CONFLICT (libelle) DO NOTHING;

-- Administrateur par défaut
-- Mot de passe : Admin@2026! (hashé avec bcrypt — à remplacer par le vrai hash)
INSERT INTO utilisateurs (id, nom, email, mot_de_passe, role) VALUES
    ('user-001', 'Administrateur', 'admin@attijaribank.tn',
     '$2b$12$placeholder_hash_a_remplacer_avec_scripts_init_db',
     'admin')
ON CONFLICT (email) DO NOTHING;

-- ── Étape 4 : Vérification ───────────────────────────────────

-- Vérifier que toutes les tables sont créées
SELECT table_name, 
       (SELECT COUNT(*) FROM information_schema.columns 
        WHERE table_name = t.table_name) as nb_colonnes
FROM information_schema.tables t
WHERE table_schema = 'public'
ORDER BY table_name;

-- ============================================================
-- REQUÊTES UTILES POUR LE DÉVELOPPEMENT
-- (Copier-coller dans un nouveau fichier .sql selon besoin)
-- ============================================================

-- Voir toutes les réclamations
-- SELECT * FROM reclamations ORDER BY created_at DESC LIMIT 50;

-- Réclamations à risque élevé
-- SELECT id, type_operation, severite, score_risque, statut
-- FROM reclamations WHERE score_risque > 0.75 ORDER BY score_risque DESC;

-- Statistiques par type d'opération
-- SELECT type_operation, COUNT(*) as total, AVG(severite) as severite_moy,
--        AVG(score_risque) as score_moy
-- FROM reclamations GROUP BY type_operation ORDER BY total DESC;

-- Actions les plus fréquentes (base des recommandations)
-- SELECT action_effectuee, COUNT(*) as frequence
-- FROM reclamations WHERE action_effectuee IS NOT NULL
-- GROUP BY action_effectuee ORDER BY frequence DESC LIMIT 20;

-- Audit trail récent
-- SELECT u.nom, a.action, a.details, a.ip_address, a.timestamp
-- FROM audit_logs a LEFT JOIN utilisateurs u ON a.utilisateur_id = u.id
-- ORDER BY a.timestamp DESC LIMIT 20;

-- Vérifier l'import CSV
-- SELECT COUNT(*) as total_importe,
--        MIN(date) as premiere_reclamation,
--        MAX(date) as derniere_reclamation
-- FROM reclamations;

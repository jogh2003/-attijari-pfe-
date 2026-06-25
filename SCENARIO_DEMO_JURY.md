# Scénario de Démonstration — Attijari Bank Système IA & RPA
## Présentation devant le jury — 12–15 minutes

---

## 🟢 ÉTAPE 0 — PRÉPARATION (2 min avant démo)

### Sur ta machine :
```powershell
# Terminal 1 : Lancer le backend
cd "c:\Users\meriam\Desktop\project - Copie"
venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Le serveur démarre sur **http://localhost:8000**

### Dans le navigateur :
1. Ouvrir **http://localhost:8000** (ou http://127.0.0.1:8000)
2. La page de **login** s'affiche

---

## 🔐 ÉTAPE 1 — AUTHENTIFICATION (1 min)

**Objectif** : Montrer que l'API est sécurisée avec JWT et que les rôles fonctionnent.

### Actions dans l'interface :
1. Sur la page **login**, voir les 4 rôles disponibles
2. Cliquer sur le bouton **Admin** (pré-rempli)
3. Vérifier que l'URL API est détectée (point vert à côté)
4. Cliquer sur **"Se connecter"** → Le JWT est validé, on accède au Dashboard

**À dire au jury** :
> *"Nous utilisons JWT HS256 pour l'authentification sécurisée. 
> 4 rôles : Admin (accès complet), Responsable IT (RPA + audit), Utilisateur (soumettre tickets), Robot UiPath (consultation alertes)."*

---

## 📊 ÉTAPE 2 — DASHBOARD — Afficher l'état du système (2 min)

**Objectif** : Montrer que tous les modèles sont chargés, les données disponibles, et l'architecture en place.

### Actions dans l'interface :

#### 2.1 Vue d'ensemble (KPI cards en haut)
- **Total Tickets** → 1 507 (données réelles Fév–Mars 2026)
- **Tickets en retard SLA** → 193 (12,8%)
- **XGBoost Accuracy** → 99,7% — AUC 1,00
- **Durée moyenne résolution** → 266 min

#### 2.2 État des modèles (carte centrale)
Descendre et montrer la section **"État des modèles IA"** :
- ✅ **Pipeline NLP** — vert
- ✅ **XGBoost** — vert (99,7%)
- ✅ **LightGBM + KNN Reco** — vert (64,4%)
- ✅ **PostgreSQL** — vert
- ✅ **Données CSV** — vert (1507 tickets)

#### 2.3 Graphiques
Montrer les 3 charts :
- **Tickets par groupe** (pie chart) → Sécurité Opérationnelle en tête
- **Distribution scores risque** → pic à 0,8-0,9
- **Tendance hebdomadaire** → volatilité semaine 1-8

**À dire au jury** :
> *"Le système utilise une **architecture hybride 3 niveaux** :
> - **N1** : Score Anomalie (règles < 10ms) — si ≥0,75 → alerte immédiate
> - **N2** : XGBoost confirme (zone grise 0,60–0,75) — accuracy 99,7%
> - **N3** : Recommandation LightGBM + KNN (35 actions) — Top-3 64,4% précision
> 
> Tous les modèles sont en vert, données fusionnées (CSV + PostgreSQL), prêts pour RPA."*

---

## 🎯 ÉTAPE 3 — SOUMETTRE UN NOUVEAU TICKET (5 min)

**Objectif** : Montrer le flux **complet** d'un ticket du début à la fin :
**soumission → analyse NLP → prédiction → recommandation → alerte UiPath → clôture**.

### 3A. Soumettre un ticket via la page "Réclamations"

#### Actions :
1. Cliquer sur **"Réclamations"** dans la sidebar
2. Voir les 1507 tickets existants dans le tableau
3. Remarquer les filtres (groupe, sévérité, retard SLA)

#### Soumettre un **nouveau ticket critique** :
1. Aller dans la sidebar → **"Analyse NLP"** (Admin seulement)

---

## 🧠 ÉTAPE 3B — ANALYSE NLP (3 min)

**Objectif** : Montrer comment un texte libre est analysé en temps réel et génère un score d'anomalie.

### Actions dans l'interface — Page "Analyse NLP" :

#### Option 1 : Exemple pré-défini (PLUS RAPIDE)
1. Voir la zone **"Exemples rapides"** en bas à gauche
2. Cliquer sur : **"→ Compromission firewall (Sécurité)"**
   - Le texte se pré-remplit : *"Compromission du firewall détectée, plusieurs indicateurs d'intrusion actifs sur le réseau interne"*
   - Groupe auto-sélectionné : **Sécurité Opérationnelle**
   - Sévérité : **Critique (1)**
3. Cliquer sur **"Analyser avec le pipeline NLP"**

#### Résultat attendu (POST /reclamations/analyser) :
```
✓ Score anomalie : 0.99 (CRITIQUE)
✓ Alerte déclenchée : OUI
✓ Methode : Score Anomalie (N1 — < 10ms)
✓ Erreurs détectées : ["blocage", "compromission"]
✓ Systèmes détectés : ["Firewall"]
```

**À dire au jury** :
> *"Le pipeline NLP détecte en moins de 10ms que ce ticket est **critique** (0,99).
> Il identifie les mots-clés 'compromission' (+0,25), 'firewall' (+0,20), et 'Sécurité Opérationnelle' (+0,20).
> Résultat : **Score 0,99 ≥ 0,75** → Alerte immédiate déclenchée pour UiPath."*

---

## 📈 ÉTAPE 3C — PRÉDICTION XGBOOST (2 min)

**Objectif** : Montrer que le modèle XGBoost **confirme** ou **rejette** l'alerte si le score est en zone grise.

### Actions dans l'interface — Page "Prédictions XGBoost" :

1. **Groupe** : sélectionner **"Sécurité Opérationnelle"** (ou laisser l'exemple)
2. **Sévérité** : **"Critique (1)"**
3. **Retard historique** : laisser **"Non"** (par défaut)
4. Cliquer sur **"Prédire le risque avec XGBoost"**

#### Résultat attendu (POST /api/predictions/predire) :
```
✓ Score risque XGBoost : 0.99
✓ Niveau : CRITIQUE
✓ Est alerte : OUI
✓ Modèle : xgb_v1 — Accuracy 99,7% — AUC 1,00
```

**Voir aussi** :
- **Scores réels par groupe** (bas de la page) : Sécurité Opé = 0,87 (confirmé réel)
- **Évolution temporelle** : graphique des 8 semaines (tendances)

**À dire au jury** :
> *"XGBoost **confirme** l'alerte (0,99). Le modèle est basé sur 1 207 tickets réels, avec des features :
> - Sévérité (8%)
> - Type de groupe (9%)
> - Score anomalie (29%)
> - Score risque (47%)
> 
> **Accuracy 99,7%** sur données test — c'est notre fiabilité pour confirmer les alertes en zone grise."*

---

## 💡 ÉTAPE 3D — RECOMMANDATION LIGHTGBM + KNN (2 min)

**Objectif** : Montrer que LightGBM suggère une **action corrective** appropriée et que KNN ajoute une similarité incidentielle.

### Actions dans l'interface — Page "Recommandations LightGBM" :

1. Cliquer sur **"Recommandations LightGBM"** dans la sidebar
2. Dans la zone **"Description du problème IT"**, voir le texte du ticket compromission déjà en contexte
   - Ou cliquer sur un des 3 **exemples rapides**
3. Groupe : **"Sécurité Opérationnelle"**
4. Cliquer sur **"Recommandation LightGBM"**

#### Résultat attendu (POST /api/recommandations/analyser) :
```
✓ Action suggérée : "Bloquer accès & Escalader RSSI"
✓ Confiance : 62% (Top-1 accuracy)
✓ Similarité KNN : ~0.80
✓ Incidents similaires : liste d'exemples proches
✓ Alternatives (Top-3) :
  1. Lancer incident response
  2. Isoler systèmes infectés
  3. Réinitialiser tokens compromis
```

**À dire au jury** :
> *"LightGBM propose l'action corrective basée sur 1 374 tickets réels.
> Le modèle utilise **TF-IDF** pour comprendre le texte + **encodeurs** pour groupe/catégorie + **sévérité**.
> Ensuite, **KNN vérifie la similarité** avec incidents passés pour affiner la recommandation.
> **Accuracy Top-3 : 64,4%** — très bon pour recommandations non-déterministes."*

---

## 🚨 ÉTAPE 4 — ALERTES UIPATH EN TEMPS RÉEL (3 min)

**Objectif** : Montrer le flux RPA — UiPath détecte, notifie, et clôt l'alerte.

### Actions dans l'interface — Page "Alertes UiPath" :

#### 4.1 Voir les alertes actives
1. Cliquer sur **"Alertes UiPath"** dans la sidebar
2. KPI cards en haut montrent :
   - **Alertes actives** (ex: 20)
   - **Tickets en surveillance**
   - **Score moyen alertes**
   - **Robots actifs** (3 robots)
3. Descendre → voir la **liste des alertes** (cartes rouges/orange)
   - Chacune montre : ID | Score | Type opération | Action recommandée

#### 4.2 Cliquer sur une alerte pour voir les détails
1. Voir le **score de risque** (ex: 0,99)
2. Voir l'**action recommandée** (ex: "Bloquer accès & Escalader RSSI")
3. Voir le **niveau de détection** (Niveau 1 ou 2)
4. Voir la **date de détection** (ex: 2026-05-16 21:13)

#### 4.3 Notifier le responsable IT
1. Sur une alerte, chercher le bouton **"Notifier IT"** ou **"📧"**
2. Cliquer → L'API appelle **POST /api/alertes/{id}/notifier**
   - Envoie un email au responsable (ou simule si SMTP absent)
   - Résultat : `sent: true` ou `sent: false` (simulation)

**À dire au jury** :
> *"UiPath interroge **GET /api/alertes?seuil=0.75** toutes les 5 minutes.
> Pour ce ticket critique (0,99) :
> - **CheckAlerte.xaml** détecte l'alerte
> - **NotifierIT.xaml** envoie un email au responsable IT
> - Le responsable peut approuver l'action dans UiPath Studio"*

---

## ✅ ÉTAPE 5 — CLÔTURER L'ALERTE (1 min)

**Objectif** : Montrer que la clôture est **persistée en base PostgreSQL** et reste visible dans l'historique.

### Actions dans l'interface — Page "Alertes UiPath" :

#### 5.1 Clôturer une alerte
1. Sur une alerte, chercher le bouton **"Résoudre"** ou **"✓"**
2. Cliquer → Dialog pour confirmer l'action effectuée
3. Entrer une description : *"Firewall rebooté, accès restauré"*
4. Sélectionner **"Statut : resolue"**
5. Cliquer **"Confirmer"** → POST /api/alertes/{id}/cloturer

#### Résultat attendu :
```
✓ Message : "Alerte REC-3FEED3 clôturée"
✓ Statut final : resolue
✓ Date résolution : 2026-05-16T21:13:39
✓ Apprentissage : "Ticket ajouté à la base XGBoost — réentraînement lundi 02h00"
```

#### 5.2 Vérifier la persistence en base
1. Cliquer sur **"Historique des alertes"** (ou voir une section dédiée)
2. Voir la clôture est **persistée en PostgreSQL**
   - ID alerte | Status | Action effectuée | Date résolution
3. Les historiques restent visibles après actualisation

**À dire au jury** :
> *"La clôture est **immédiatement persistée** en PostgreSQL (table `alertes`).
> Cela signifie que même après redémarrage du backend, l'historique est sauvegardé.
> Le ticket rejoint la **base d'apprentissage pour réentraînement** XGBoost lundi 02h00."*

---

## 📋 ÉTAPE 6 — AUDIT TRAIL (1 min — OPTIONNEL)

**Objectif** : Montrer que **toutes les actions sont tracées** pour l'audit bancaire.

### Actions dans l'interface :

1. Cliquer sur **"Audit Trail"** dans la sidebar
2. Voir l'historique complet :
   - **Heure exacte** (horodatage)
   - **Utilisateur** (email)
   - **Rôle** (admin / responsable_it)
   - **Action** (LOGIN / GET_ALERTES / NOTIFIER_RESPONSABLE / RESOLUTION_CONFIRMEE)
   - **Détails** (seuil, nombre alertes, alerte ID, etc.)
   - **IP address** (testclient ou adresse réelle)

**À dire au jury** :
> *"Chaque action est loguée : login, consultation d'alertes, notification, clôture.
> Cela satisfait les **obligations de conformité bancaire**.
> Les logs peuvent être exportés pour audit/compliance."*

---

## 🔄 ÉTAPE 7 — BOUCLE COMPLÈTE : Soumettre un ticket via le formulaire (OPTIONNEL — 2 min)

**Objectif** : Montrer l'intégration utilisateur normal (pas robot).

### Actions dans l'interface :

#### 7.1 Déconnexion & Reconnexion en rôle "Utilisateur"
1. Logout (bouton en bas à gauche)
2. Login avec **"Meriam"** (utilisateur normal)

#### 7.2 Soumettre un ticket
1. Sidebar → **"Soumettre une réclamation"**
2. Remplir le formulaire :
   - **Description** : "Problème de connexion VPN depuis ce matin"
   - **Type opération** : "Helpdesk"
   - **Sévérité** : "Haute"
3. Cliquer **"Soumettre"**

#### Résultat :
- Le ticket est **analysé en NLP** → score généré
- Peut déclencher une **alerte UiPath** si score ≥ 0,75
- L'utilisateur voit la **recommandation d'action**

---

## 🎬 RÉSUMÉ DE LA DÉMO — À répéter au jury

```
┌─────────────────────────────────────────────────────────────┐
│   FLUX COMPLET : Nouveau ticket → Détection → Action      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1️⃣  TICKET CRITIQUE ARRIVE (Firewall compromise)          │
│       └→ Pipeline NLP detects : Score 0,99                │
│                                                             │
│  2️⃣  ALERTE DECLENCHEE (Score ≥ 0,75)                      │
│       └→ UiPath CheckAlerte.xaml triggers                  │
│                                                             │
│  3️⃣  XGBOOST CONFIRME (si zone grise 0,60–0,75)            │
│       └→ Precision 99,7% — AUC 1,00                       │
│                                                             │
│  4️⃣  RECOMMANDATION LIGHTGBM + KNN (Action corrective)     │
│       └→ "Blocker accès & escalader RSSI"                  │
│                                                             │
│  5️⃣  RESPONSABLE IT NOTIFIE (Email SMTP)                   │
│       └→ NotifierIT.xaml executes                          │
│                                                             │
│  6️⃣  RESOLUTION CONFIRMEE (RPA execution)                  │
│       └→ ConfirmerResolution.xaml → POST /cloturer         │
│                                                             │
│  7️⃣  HISTORIQUE PERSISTE (PostgreSQL)                      │
│       └→ Données disponibles après redémarrage             │
│                                                             │
│  8️⃣  APPRENTISSAGE FEEDBACK (Base XGBoost enrichie)        │
│       └→ Réentraînement lundi 02h00 automatique            │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚡ CONSEILS POUR LA DÉMO EN DIRECT

### ✅ À faire :
1. **Tester le backend avant la démo** → `python scripts/smoke_demo.py` (doit afficher PASS)
2. **Préparer des exemples** en copie/paste (textes de tickets critiques)
3. **Avoir PostgreSQL accessible** (ou les tests passent quand même)
4. **Charger lentement** chaque page (laisser les graphiques se dessiner)
5. **Lire les tooltips** en passant la souris sur les éléments

### ⚠️ À éviter :
1. ❌ Aller trop vite (les jury n'aura pas le temps de suivre)
2. ❌ Cliquer sur trop d'onglets en même temps
3. ❌ Parler de détails techniques sans contexte métier
4. ❌ Oublier d'actualiser les pages (données en cache)

### 💡 Si quelque chose échoue :
- **Backend non répondant** → Vérifier que uvicorn est lancé
- **Login échoue** → Vérifier DATABASE_URL dans .env
- **Pas d'alertes** → C'est normal, les alertes dépendent des données CSV
- **Charts non affichés** → Actualiser la page (Ctrl+F5)
- **SMTP absent** → Expliquer que l'envoi est simulé en démo

---

## 📝 QUESTIONS PROBABLES DU JURY

**Q: Pourquoi 3 niveaux et pas juste XGBoost ?**
> R: XGBoost prend 50–100ms, règles prennent < 10ms. Pour une banque, la **vitesse est critique**.
> Les règles ont aussi **l'avantage** d'être explicables (audit / compliance).

**Q: Que faire si un modèle drifts ?**
> R: **Réentraînement automatique** chaque lundi 02h00 (APScheduler).
> N1 (règles) ne drifts jamais car c'est du code, pas du ML.

**Q: Combien de tickets peut traiter le système ?**
> R: Les données utilisées sont **1 507 tickets réels** (Fév–Mars 2026).
> En production, ce serait facilement **scalable** (MongoDB pour les logs, Redis pour le cache).

**Q: PostgreSQL vs MongoDB vs autre ?**
> R: PostgreSQL car données structurées (audit, alerts, users).
> En prod, ajouterait Redis (cache) et Elasticsearch (recherche full-text).

---

## 🎯 TIMING TOTAL

| Étape | Durée | Cumulé |
|-------|-------|---------|
| 0. Préparation | 2 min | 2 min |
| 1. Authentification | 1 min | 3 min |
| 2. Dashboard | 2 min | 5 min |
| 3. NLP + XGBoost + LightGBM | 5 min | 10 min |
| 4. Alertes UiPath | 2 min | 12 min |
| 5. Clôture & Historique | 1 min | 13 min |
| 6. Questions du jury | 2–5 min | 15–18 min |
| **TOTAL** | **12–15 min** | **15–18 min** |

✅ **Démo rapide, fluide, impressionnante.**

---

**Bon courage pour la soutenance ! 🚀**

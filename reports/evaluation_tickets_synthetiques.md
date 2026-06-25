# Rapport d'évaluation des tickets synthétiques

Date : 2026-06-05 19:53:52

## 1. Résumé
- Tickets originaux : 1507
- Tickets synthétiques générés : 1507
- Tickets augmentés : 3014

## 2. Jeu de données synthétiques
- Les tickets synthétiques sont construits par échantillonnage avec remplacement et enrichis de modificateurs de texte.
- La génération conserve les principales colonnes existantes et ajuste les scores et durées de manière réaliste.

## 3. Résultats de l'évaluation

### 3.1 Détection NLP
| Model | Accuracy | Precision | Recall | F1 | Roc_auc |
|---|---|---|---|---|---|
| Rule-based score_anomalie >= 0.70 | 0.8974 | 0.6000 | 0.6154 | 0.6076 | 0.7500 |
| LogisticRegression (TF-IDF) | 0.7616 | 0.3012 | 0.6410 | 0.4098 | 0.8286 |

### 3.2 Prédiction de retard
| Model | Accuracy | Precision | Recall | F1 | Roc_auc |
|---|---|---|---|---|---|
| RandomForest (structured) | 0.9967 | 0.9750 | 1.0000 | 0.9873 | 1.0000 |
| XGBoost (structured) | 0.9967 | 0.9750 | 1.0000 | 0.9873 | 0.9999 |

### 3.3 Recommandation
| Model | Top1 | Top3 |
|---|---|---|
| LightGBM | 0.6534 | 0.6859 |
| LogisticRegression (multiclass) | 0.3899 | 0.5090 |
| KNN text-similarity | 0.8484 | 0.9206 |

## 4. Résultats sur le jeu augmenté

### 4.1 Détection NLP
| Model | Accuracy | Precision | Recall | F1 | Roc_auc |
|---|---|---|---|---|---|
| Rule-based score_anomalie >= 0.75 | 0.8939 | 0.6207 | 0.4615 | 0.5294 | 0.7258 |
| LogisticRegression (TF-IDF) | 0.8391 | 0.4410 | 0.9103 | 0.5941 | 0.9326 |

### 4.2 Prédiction de retard
| Model | Accuracy | Precision | Recall | F1 | Roc_auc |
|---|---|---|---|---|---|
| RandomForest (structured) | 0.9983 | 1.0000 | 0.9872 | 0.9935 | 1.0000 |
| XGBoost (structured) | 0.9983 | 0.9873 | 1.0000 | 0.9936 | 1.0000 |

### 4.3 Recommandation
| Model | Top1 | Top3 |
|---|---|---|
| LightGBM | 0.7232 | 0.7318 |
| LogisticRegression (multiclass) | 0.1799 | 0.5692 |
| KNN text-similarity | 0.7785 | 0.9048 |

## 5. Comparaison Original vs Augmenté

### 5.1 Détection NLP
| Model | Accuracy | Precision | Recall | F1 | Roc_auc |
|---|---|---|---|---|---|
| Rule-based score_anomalie >= 0.70 | 0.8974 | 0.6000 | 0.6154 | 0.6076 | 0.7500 |
| LogisticRegression (TF-IDF) | 0.7616 | 0.3012 | 0.6410 | 0.4098 | 0.8286 |
| Rule-based score_anomalie >= 0.75 | 0.8939 | 0.6207 | 0.4615 | 0.5294 | 0.7258 |
| LogisticRegression (TF-IDF) | 0.8391 | 0.4410 | 0.9103 | 0.5941 | 0.9326 |

### 5.2 Prédiction de retard
| Model | Accuracy | Precision | Recall | F1 | Roc_auc |
|---|---|---|---|---|---|
| RandomForest (structured) | 0.9967 | 0.9750 | 1.0000 | 0.9873 | 1.0000 |
| XGBoost (structured) | 0.9967 | 0.9750 | 1.0000 | 0.9873 | 0.9999 |
| RandomForest (structured) | 0.9983 | 1.0000 | 0.9872 | 0.9935 | 1.0000 |
| XGBoost (structured) | 0.9983 | 0.9873 | 1.0000 | 0.9936 | 1.0000 |

### 5.3 Recommandation
| Model | Top1 | Top3 |
|---|---|---|
| LightGBM | 0.6534 | 0.6859 |
| LogisticRegression (multiclass) | 0.3899 | 0.5090 |
| KNN text-similarity | 0.8484 | 0.9206 |
| LightGBM | 0.7232 | 0.7318 |
| LogisticRegression (multiclass) | 0.1799 | 0.5692 |
| KNN text-similarity | 0.7785 | 0.9048 |

## 6. Exemples de tickets synthétiques

### Ticket synthétique 1
- type_operation : Sécurité Opérationnelle
- categorie : Securite et Habilitation SI
- en_retard : False
- objet : Demande de vérification et Libération émail SPAM — urgent
- description : '@@OPERATION=AddRequest@@ @@REQUESTTEMPLATE= Demande de vérification et Libération émail SPAM@@ @@SUBJECT= Demande de vérification et Libération émail SPAM@@ Bonjour, Merci de valider ce mail, il s'agit d'une demande d'ARP. Cordialement / B
- score_anomalie : 0.5865017591021472
- score_risque : 0.5542230120744828

### Ticket synthétique 2
- type_operation : Helpdesk
- categorie : Securite et Habilitation SI
- en_retard : False
- objet : Problème d'authentification // ACCES NV DA AGENCE TAJEROUINE 036 - MATRICULE 1826 — urgent
- description : Bonjour , Merci de nous fournir les accès des applications nécessaires pour le nouveau DA de l'agence Tajerouine 036 Mr Benaleya Bechir , Matricule 1826 Cdt Incident similaire déjà signalé hier.
- score_anomalie : 0.6235307740622907
- score_risque : 0.5464555134598766

### Ticket synthétique 3
- type_operation : Sécurité Opérationnelle
- categorie : Securite et Habilitation SI
- en_retard : False
- objet : Demande de vérification et Libération émail SPAM — urgent
- description : '@@OPERATION=AddRequest@@ @@REQUESTTEMPLATE= Demande de vérification et Libération émail SPAM@@ @@SUBJECT= Demande de vérification et Libération émail SPAM@@ Bonjour Merci de débloquer . Bien cordialement BOUCHNEB KHALIL Analyste PME Poste:
- score_anomalie : 0.5756217143916955
- score_risque : 0.5547616709232721

### Ticket synthétique 4
- type_operation : Sécurité Opérationnelle
- categorie : Securite et Habilitation SI
- en_retard : False
- objet : Demande de vérification et Libération émail SPAM — urgent
- description : @@OPERATION=AddRequest@@ @@REQUESTTEMPLATE= Demande de vérification et Libération émail SPAM@@ @@SUBJECT= Demande de vérification et Libération émail SPAM@@ Bonjour Priere me liberer ce mail cdt De: Notifications-antispam@attijaribank.com.t
- score_anomalie : 0.6129611767753442
- score_risque : 0.5814755234946434

### Ticket synthétique 5
- type_operation : Helpdesk
- categorie : Amplitude
- en_retard : True
- objet : Problème d'accès Amplitude/NOUVEAU GCP AG102 — urgent
- description : Dans le cadre de la nouvelle affectation GCP 102 ,veuillez activer à Mme Nesrine ZINELABIDINE MLE 4576 l’accès amplitude agence 102 Bien à vous, Requête traitée en priorité par l'équipe IT.
- score_anomalie : 0.9584802399682114
- score_risque : 0.92991062719234

## 7. Inférences de production sur tickets synthétiques

- Ticket 1 : groupe=Sécurité Opérationnelle categorie=Securite et Habilitation SI severite=2
  - score_risque=0.99 version=xgb_v1
  - action_LGBM=Autre - escalade support
  - action_KNN=Désactiver le compte suspect, analyser les logs d'authentification et notifier le RSSI

- Ticket 2 : groupe=Helpdesk categorie=Securite et Habilitation SI severite=1
  - score_risque=0.576 version=xgb_v1
  - action_LGBM=Votre réclamation a été transmise au prestataire pour traitement En cas de non-résolution ou de retard, merci de répondre directement au mail envoyé au prestataire pour assurer le suivi.
  - action_KNN=Nous vous invitons à saisir une nouvelle réclamation en précisant de manière détaillée la liste des applications concernées, votre identifiant ainsi que l’affectation rencontrée, afin d’en faciliter l

- Ticket 3 : groupe=Sécurité Opérationnelle categorie=Securite et Habilitation SI severite=2
  - score_risque=0.99 version=xgb_v1
  - action_LGBM=Autre - escalade support
  - action_KNN=Désactiver le compte suspect, analyser les logs d'authentification et notifier le RSSI

- Ticket 4 : groupe=Sécurité Opérationnelle categorie=Securite et Habilitation SI severite=2
  - score_risque=0.99 version=xgb_v1
  - action_LGBM=Autre - escalade support
  - action_KNN=Bonjour,Après vérification, nous ne pouvons pas libérer cet email car il contient un fichier .zip, ce type de pièce jointe étant bloqué par notre politique de sécurité.

- Ticket 5 : groupe=Helpdesk categorie=Amplitude severite=1
  - score_risque=0.495 version=xgb_v1
  - action_LGBM=Autre - escalade support
  - action_KNN=Redémarrer le service Amplitude et vérifier les logs d'application

## 8. Conclusions
- L’augmentation a permis de comparer les performances des modèles sur des tickets originaux et synthétiques.
- Le fichier CSV généré est disponible dans `data/cleaned/reclamations_propres_augmente.csv`.

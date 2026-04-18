"""
analyser_eda.py — Analyse Exploratoire des Données (EDA)
PFE Attijari bank — Sujet 21

Génère tous les graphiques pour le rapport PFE.
Exécuter : python scripts/analyser_eda.py
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # pas de fenêtre GUI
import seaborn as sns
import os

# Style
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.family']    = 'DejaVu Sans'
COULEURS = ['#534AB7', '#185FA5', '#993C1D', '#854F0B', '#0F6E56', '#3B6D11', '#A32D2D']

os.makedirs("reports/figures", exist_ok=True)

def charger_donnees():
    path = "data/cleaned/reclamations_propres.csv"
    if not os.path.exists(path):
        print(f"ERREUR : {path} non trouvé — lancer d'abord import_et_nettoyage.py")
        exit(1)
    df = pd.read_csv(path, parse_dates=['date'], on_bad_lines='skip')
    print(f"Données chargées : {len(df)} tickets")
    return df

def graphique_1_distribution_groupes(df):
    """Distribution des tickets par groupe technique"""
    fig, ax = plt.subplots(figsize=(14, 7))
    counts = df['type_operation'].value_counts().head(10)
    bars = ax.barh(counts.index, counts.values, color=COULEURS[0], alpha=0.85)
    ax.bar_label(bars, padding=4, fontsize=10)
    ax.set_title("Distribution des tickets par Groupe technique\nAttijari bank — Février–Mars 2026",
                 fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Nombre de tickets", fontsize=12)
    ax.invert_yaxis()
    plt.tight_layout()
    path = "reports/figures/01_distribution_groupes.png"
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Sauvegardé : {path}")

def graphique_2_evolution_temporelle(df):
    """Évolution du nombre de tickets par jour"""
    fig, ax = plt.subplots(figsize=(14, 6))
    df_time = df.copy()
    df_time['date_jour'] = pd.to_datetime(df_time['date'], errors='coerce').dt.date
    daily = df_time.groupby('date_jour').size().reset_index(name='count')
    ax.plot(pd.to_datetime(daily['date_jour']), daily['count'],
            color=COULEURS[0], linewidth=2, marker='o', markersize=4)
    ax.fill_between(pd.to_datetime(daily['date_jour']), daily['count'],
                    alpha=0.15, color=COULEURS[0])
    ax.set_title("Évolution quotidienne du nombre de tickets\nFévrier–Mars 2026",
                 fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Nombre de tickets", fontsize=12)
    plt.xticks(rotation=45)
    plt.tight_layout()
    path = "reports/figures/02_evolution_temporelle.png"
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Sauvegardé : {path}")

def graphique_3_priorite_statut(df):
    """Répartition des priorités et statuts"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Priorités
    prio = df['priorite_orig'].value_counts()
    prio_colors = [COULEURS[2], COULEURS[0], COULEURS[4], COULEURS[3]][:len(prio)]
    wedges, texts, autotexts = axes[0].pie(prio.values, labels=prio.index,
                                            autopct='%1.1f%%', colors=prio_colors,
                                            startangle=90)
    for at in autotexts:
        at.set_fontsize(10)
    axes[0].set_title("Répartition par Priorité", fontsize=13, fontweight='bold')

    # Statuts
    stat = df['statut'].value_counts()
    stat_colors = [COULEURS[4], COULEURS[2], COULEURS[0], COULEURS[1]][:len(stat)]
    bars = axes[1].bar(stat.index, stat.values, color=stat_colors, alpha=0.85)
    axes[1].bar_label(bars, padding=3, fontsize=10)
    axes[1].set_title("Répartition par Statut", fontsize=13, fontweight='bold')
    axes[1].set_ylabel("Nombre de tickets")
    plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=20)

    plt.suptitle("Priorités et Statuts — Données réelles Attijari bank",
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    path = "reports/figures/03_priorite_statut.png"
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Sauvegardé : {path}")

def graphique_4_categorie(df):
    """Distribution des catégories"""
    fig, ax = plt.subplots(figsize=(14, 6))
    cats = df['categorie'].value_counts().head(8)
    bars = ax.bar(cats.index, cats.values, color=COULEURS[:len(cats)], alpha=0.85)
    ax.bar_label(bars, padding=3, fontsize=10)
    ax.set_title("Distribution par Catégorie de problème\nAttijari bank — Données réelles",
                 fontsize=14, fontweight='bold', pad=15)
    ax.set_ylabel("Nombre de tickets", fontsize=12)
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    path = "reports/figures/04_categories.png"
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Sauvegardé : {path}")

def graphique_5_duree_resolution(df):
    """Distribution des durées de résolution"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Histogramme durées
    durees = df['duree_resolution_min'][df['duree_resolution_min'] > 0]
    axes[0].hist(durees, bins=30, color=COULEURS[0], alpha=0.75, edgecolor='white')
    axes[0].set_title("Distribution des durées de résolution", fontsize=13, fontweight='bold')
    axes[0].set_xlabel("Durée (minutes)", fontsize=11)
    axes[0].set_ylabel("Fréquence", fontsize=11)
    axes[0].axvline(durees.mean(), color='red', linestyle='--', linewidth=2,
                    label=f'Moyenne: {durees.mean():.0f} min')
    axes[0].legend()

    # Boxplot par groupe
    top_groupes = df['type_operation'].value_counts().head(6).index
    df_box = df[df['type_operation'].isin(top_groupes) & (df['duree_resolution_min'] > 0)]
    df_box.boxplot(column='duree_resolution_min', by='type_operation', ax=axes[1],
                   patch_artist=True)
    axes[1].set_title("Durée de résolution par Groupe", fontsize=13, fontweight='bold')
    axes[1].set_xlabel("Groupe", fontsize=11)
    axes[1].set_ylabel("Durée (minutes)", fontsize=11)
    plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=30, ha='right')
    axes[1].get_figure().suptitle('')

    plt.tight_layout()
    path = "reports/figures/05_duree_resolution.png"
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Sauvegardé : {path}")

def graphique_6_retard_sla(df):
    """Analyse des tickets en retard SLA"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Retard global
    retard = df['en_retard'].value_counts()
    labels = ['Dans les délais', 'En retard']
    colors = [COULEURS[4], COULEURS[2]]
    axes[0].pie(retard.values, labels=labels, autopct='%1.1f%%',
                colors=colors, startangle=90)
    axes[0].set_title("Respect du SLA (global)", fontsize=13, fontweight='bold')

    # Retard par groupe
    top_g = df['type_operation'].value_counts().head(6).index
    retard_g = df[df['type_operation'].isin(top_g)].groupby('type_operation')['en_retard'].mean() * 100
    bars = axes[1].bar(retard_g.index, retard_g.values, color=COULEURS[2], alpha=0.8)
    axes[1].bar_label(bars, fmt='%.1f%%', padding=3, fontsize=10)
    axes[1].set_title("Taux de retard SLA par Groupe (%)", fontsize=13, fontweight='bold')
    axes[1].set_ylabel("% en retard", fontsize=11)
    axes[1].axhline(y=retard_g.mean(), color='red', linestyle='--', linewidth=1.5,
                    label=f'Moy: {retard_g.mean():.1f}%')
    axes[1].legend()
    plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=30, ha='right')

    plt.suptitle("Analyse du respect des SLAs — Données réelles Attijari bank",
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    path = "reports/figures/06_retard_sla.png"
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Sauvegardé : {path}")

def graphique_7_type_demande(df):
    """Réclamations vs Demandes de service"""
    fig, ax = plt.subplots(figsize=(10, 6))
    types = df['type_demande'].value_counts()
    bars = ax.bar(types.index, types.values,
                  color=[COULEURS[2], COULEURS[0], COULEURS[3]][:len(types)],
                  alpha=0.85, width=0.5)
    ax.bar_label(bars, padding=4, fontsize=12, fontweight='bold')
    ax.set_title("Répartition : Réclamations vs Demandes de service\nAttijari bank — Données réelles",
                 fontsize=14, fontweight='bold', pad=15)
    ax.set_ylabel("Nombre de tickets", fontsize=12)
    plt.tight_layout()
    path = "reports/figures/07_type_demande.png"
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Sauvegardé : {path}")

def graphique_8_heatmap_groupe_priorite(df):
    """Heatmap : Groupe × Priorité"""
    fig, ax = plt.subplots(figsize=(12, 8))
    top_g = df['type_operation'].value_counts().head(8).index
    pivot = df[df['type_operation'].isin(top_g)].pivot_table(
        index='type_operation', columns='priorite_orig',
        values='id', aggfunc='count', fill_value=0
    )
    sns.heatmap(pivot, annot=True, fmt='d', cmap='Blues',
                linewidths=0.5, ax=ax, cbar_kws={'label': 'Nombre de tickets'})
    ax.set_title("Heatmap : Nombre de tickets par Groupe × Priorité\nAttijari bank — Données réelles",
                 fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Priorité", fontsize=12)
    ax.set_ylabel("Groupe", fontsize=12)
    plt.tight_layout()
    path = "reports/figures/08_heatmap_groupe_priorite.png"
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Sauvegardé : {path}")

def graphique_9_top_objets(df):
    """Top 15 des incidents les plus fréquents"""
    fig, ax = plt.subplots(figsize=(14, 8))
    objets = df['objet'].value_counts().head(15)
    bars = ax.barh(range(len(objets)), objets.values, color=COULEURS[0], alpha=0.85)
    ax.set_yticks(range(len(objets)))
    ax.set_yticklabels([o[:55] + '...' if len(o) > 55 else o for o in objets.index],
                       fontsize=10)
    ax.bar_label(bars, padding=3, fontsize=10)
    ax.set_title("Top 15 des types d'incidents les plus fréquents\nAttijari bank — Données réelles",
                 fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Nombre d'occurrences", fontsize=12)
    ax.invert_yaxis()
    plt.tight_layout()
    path = "reports/figures/09_top_incidents.png"
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Sauvegardé : {path}")

def graphique_10_top_actions(df):
    """Top actions effectuées — base pour les recommandations KNN"""
    fig, ax = plt.subplots(figsize=(12, 6))
    actions = df[df['action_effectuee'] != '']['action_effectuee'].value_counts().head(10)
    bars = ax.barh(actions.index, actions.values, color=COULEURS[4], alpha=0.85)
    ax.bar_label(bars, padding=3, fontsize=10)
    ax.set_title("Top 10 des actions correctives (base KNN recommandations)\nAttijari bank — Données réelles",
                 fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Fréquence", fontsize=12)
    ax.invert_yaxis()
    plt.tight_layout()
    path = "reports/figures/10_top_actions.png"
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Sauvegardé : {path}")

def afficher_stats_finales(df):
    print("\n" + "=" * 60)
    print("  STATISTIQUES EDA FINALES")
    print("=" * 60)
    print(f"  Total tickets uniques    : {len(df)}")
    print(f"  Réclamations             : {(df['type_demande'] == 'Réclamation').sum()}")
    print(f"  Demandes de service      : {(df['type_demande'] == 'Demande de Service').sum()}")
    print(f"  Tickets en retard SLA    : {df['en_retard'].sum()} ({df['en_retard'].mean()*100:.1f}%)")
    print(f"  Durée résolution moyenne : {df['duree_resolution_min'].mean():.0f} minutes")
    print(f"  Tickets résolus          : {(df['statut'] == 'resolue').sum()}")
    print(f"  Tickets avec action      : {(df['action_effectuee'] != '').sum()}")
    print(f"  Groupe dominant          : {df['type_operation'].value_counts().idxmax()}")
    print(f"  Catégorie dominante      : {df['categorie'].value_counts().idxmax()}")
    print("=" * 60)

# ── MAIN ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  EDA — Analyse Exploratoire — Attijari bank 2026")
    print("=" * 60)

    df = charger_donnees()

    print("\nGénération des graphiques...")
    graphique_1_distribution_groupes(df)
    graphique_2_evolution_temporelle(df)
    graphique_3_priorite_statut(df)
    graphique_4_categorie(df)
    graphique_5_duree_resolution(df)
    graphique_6_retard_sla(df)
    graphique_7_type_demande(df)
    graphique_8_heatmap_groupe_priorite(df)
    graphique_9_top_objets(df)
    graphique_10_top_actions(df)

    afficher_stats_finales(df)

    print(f"\n10 graphiques sauvegardés dans reports/figures/")
    print("Prochaine étape : python scripts/pipeline_nlp.py")

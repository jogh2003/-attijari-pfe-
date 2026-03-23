"""Script d'import CSV vers PostgreSQL - adapter selon le vrai CSV recu"""
import sys, uuid
sys.path.insert(0, ".")
import pandas as pd

def importer(csv_path: str):
    print(f"Lecture : {csv_path}")
    df = pd.read_csv(csv_path, encoding="utf-8")
    print(f"Shape : {df.shape}")
    print(f"Colonnes : {list(df.columns)}")
    print("\nApercu :")
    print(df.head())
    print("\nValeurs manquantes :")
    print(df.isnull().sum())
    print(f"\nDoublons : {df.duplicated().sum()}")
    # TODO: adapter les noms de colonnes et importer en BDD
    print("\nAdapter les noms de colonnes dans ce script selon le CSV recu.")

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/reclamations.csv"
    importer(path)

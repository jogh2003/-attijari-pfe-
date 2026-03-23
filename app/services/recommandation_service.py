"""Service recommandations KNN"""
import numpy as np
from sklearn.neighbors import NearestNeighbors
from typing import List, Optional

class RecommandationService:
    def __init__(self):
        self.knn = None
        self.embeddings = []
        self.actions = []

    def charger_historique(self, embeddings: np.ndarray, actions: List[str]):
        self.embeddings = embeddings
        self.actions = actions
        self.knn = NearestNeighbors(n_neighbors=5, metric="cosine")
        self.knn.fit(embeddings)
        print(f"KNN entraine sur {len(actions)} cas")

    def recommander(self, embedding: np.ndarray) -> Optional[dict]:
        if not self.knn or len(self.actions) == 0:
            return None
        distances, indices = self.knn.kneighbors([embedding])
        actions_sim = [self.actions[i] for i in indices[0]]
        action = max(set(actions_sim), key=actions_sim.count)
        taux = actions_sim.count(action) / len(actions_sim)
        return {
            "action_suggeree": action,
            "taux_succes": round(taux, 2),
            "nb_cas_similaires": len(actions_sim),
            "priorite": 1 if taux >= 0.8 else 2
        }

recommandation_service = RecommandationService()

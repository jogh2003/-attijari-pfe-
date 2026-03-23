"""Service NLP : spaCy + BERT embeddings"""
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class NLPService:
    def __init__(self):
        self.nlp = None
        self.bert_model = None

    def load_models(self):
        import spacy
        from sentence_transformers import SentenceTransformer
        print("Chargement spaCy...")
        self.nlp = spacy.load("fr_core_news_md")
        print("Chargement BERT...")
        self.bert_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        print("Modeles NLP charges.")

    def extraire_entites(self, texte: str) -> dict:
        if not self.nlp:
            raise RuntimeError("Modele spaCy non charge")
        doc = self.nlp(texte)
        return {
            "tokens": [t.text for t in doc if not t.is_stop],
            "entites": [(e.text, e.label_) for e in doc.ents],
            "lemmes": [t.lemma_ for t in doc if not t.is_stop]
        }

    def get_embedding(self, texte: str) -> np.ndarray:
        if not self.bert_model:
            raise RuntimeError("Modele BERT non charge")
        return self.bert_model.encode(texte)

    def calculer_similarite(self, v1: np.ndarray, v2: np.ndarray) -> float:
        return float(cosine_similarity([v1], [v2])[0][0])

nlp_service = NLPService()

"""Service NLP : spaCy + BERT embeddings"""
import subprocess
import sys

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class NLPService:
    def __init__(self):
        self.nlp = None
        self.bert_model = None

    def load_models(self):
        import spacy
        try:
            self.nlp = spacy.load("fr_core_news_md")
        except OSError:
            print("Modèle spaCy fr_core_news_md introuvable, installation...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "fr_core_news_md"])
            self.nlp = spacy.load("fr_core_news_md")

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers est requis pour le service NLP. "
                "Exécutez 'pip install -r requirements.txt' puis relancez.'"
            ) from exc

        print("Chargement spaCy...")
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

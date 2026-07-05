import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

from sentence_transformers import SentenceTransformer
import numpy as np
from config import Config


class BERTEmbedder:
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            print(f"Loading BERT model: {Config.BERT_MODEL}...")
            # Forzar 'cpu' por defecto para evitar incompatibilidades de CUDA con PyTorch
            device = os.environ.get("BERT_DEVICE", "cpu")
            print(f"Using device: {device}")
            cls._model = SentenceTransformer(Config.BERT_MODEL, device=device)
            print("BERT model loaded successfully.")
        return cls._model

    @classmethod
    def get_embedding(cls, text):
        """Genera un embedding para un único texto. Retorna una lista de floats."""
        model = cls.get_model()
        if isinstance(text, list):
            return cls.get_embeddings_batch(text)
        
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    @classmethod
    def get_embeddings_batch(cls, texts):
        """Genera embeddings para una lista de textos. Retorna una lista de listas de floats."""
        model = cls.get_model()
        embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

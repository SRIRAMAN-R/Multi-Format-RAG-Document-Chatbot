"""
Embedding Generator Module
--------------------------
Generates dense vector embeddings using HuggingFace SentenceTransformers (local CPU execution),
Google Gemini Embeddings API, or a lightweight fallback vectorizer.
"""

import os
from typing import List, Optional
import numpy as np
from src.utils.logger import logger
from config import DEFAULT_EMBEDDING_MODEL

class EmbeddingManager:
    """Multi-provider Vector Embedding Generator."""

    def __init__(self, provider: str = "sentence_transformers", model_name: str = DEFAULT_EMBEDDING_MODEL):
        self.provider = provider
        self.model_name = model_name
        self._st_model = None
        self._init_provider()

    def _init_provider(self):
        """Initializes the requested embedding provider with automatic fallback."""
        if self.provider == "sentence_transformers":
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading SentenceTransformer model '{self.model_name}'...")
                self._st_model = SentenceTransformer(self.model_name)
                logger.info("SentenceTransformer model loaded successfully.")
            except Exception as e:
                logger.warning(f"SentenceTransformers load failed: {e}. Falling back to TF-IDF Embeddings.")
                self.provider = "tfidf"
                self._init_tfidf()
        elif self.provider == "tfidf":
            self._init_tfidf()

    def _init_tfidf(self):
        """Initializes fallback TF-IDF vectorizer."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        self._vectorizer = TfidfVectorizer(max_features=384, stop_words="english")
        self._is_fitted = False

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generates a list of vector embedding floats for input texts."""
        if not texts:
            return []

        # Provider 1: Local SentenceTransformers model
        if self.provider == "sentence_transformers" and self._st_model is not None:
            embeddings = self._st_model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
            return embeddings.tolist()

        # Provider 2: Google Gemini Embeddings API
        elif self.provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=api_key)
                    results = []
                    for txt in texts:
                        res = genai.embed_content(
                            model="models/text-embedding-004",
                            content=txt
                        )
                        results.append(res['embedding'])
                    return results
                except Exception as e:
                    logger.error(f"Gemini embedding error: {e}. Falling back to SentenceTransformers.")
                    self.provider = "sentence_transformers"
                    self._init_provider()
                    return self.embed_texts(texts)

        # Provider 3: Fallback Hash vectorizer for offline zero-dependency execution
        from sklearn.feature_extraction.text import HashingVectorizer
        vectorizer = HashingVectorizer(n_features=384, norm='l2')
        matrix = vectorizer.transform(texts)
        return matrix.toarray().tolist()

    def embed_query(self, query: str) -> List[float]:
        """Embeds a single search query string."""
        res = self.embed_texts([query])
        return res[0] if res else []

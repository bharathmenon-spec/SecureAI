"""Local embedding generation using sentence-transformers.

The model is loaded lazily on first use so importing this module stays cheap.
"""
from typing import List, Optional

import numpy as np

from app.core.config import get_settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    def __init__(self) -> None:
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            model_name = get_settings().embedding_model
            logger.info("Loading embedding model '%s'", model_name)
            self._model = SentenceTransformer(model_name)
        return self._model

    def embed(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        vectors = self._get_model().encode(
            texts, convert_to_numpy=True, show_progress_bar=False
        )
        return np.asarray(vectors, dtype=np.float32)

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed([text])[0]


_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _service
    if _service is None:
        _service = EmbeddingService()
    return _service

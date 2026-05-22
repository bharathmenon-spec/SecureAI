"""Local numpy-backed vector store.

Holds only sanitized-chunk embeddings plus lightweight metadata used for
defense-in-depth role/sensitivity pre-filtering. Persisted to a local pickle
file - no external vector database is used.
"""
import pickle
import threading
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from app.core.config import get_settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class VectorStore:
    def __init__(self) -> None:
        self._path = get_settings().data_path / "vector_store.pkl"
        self._lock = threading.Lock()
        self._ids: List[str] = []
        self._vectors: List[np.ndarray] = []
        self._meta: Dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            with open(self._path, "rb") as fh:
                data = pickle.load(fh)
            self._ids = data["ids"]
            self._vectors = data["vectors"]
            self._meta = data["meta"]
            logger.info("Loaded %d vectors from local store", len(self._ids))
        except Exception as exc:  # corrupt store - start clean
            logger.warning("Could not load vector store (%s); starting empty", exc)

    def _persist(self) -> None:
        with open(self._path, "wb") as fh:
            pickle.dump(
                {"ids": self._ids, "vectors": self._vectors, "meta": self._meta}, fh
            )

    def add_batch(self, items: List[Tuple[str, np.ndarray, dict]]) -> None:
        with self._lock:
            for chunk_id, vector, metadata in items:
                vec = np.asarray(vector, dtype=np.float32)
                if chunk_id in self._meta:
                    self._vectors[self._ids.index(chunk_id)] = vec
                else:
                    self._ids.append(chunk_id)
                    self._vectors.append(vec)
                self._meta[chunk_id] = metadata
            self._persist()

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        predicate: Optional[Callable[[dict], bool]] = None,
    ) -> List[Tuple[str, float, dict]]:
        """Return up to top_k (chunk_id, cosine_score, metadata) tuples.

        ``predicate`` filters on metadata before a chunk is considered - this
        is the retrieval-time RBAC pre-filter.
        """
        with self._lock:
            if not self._ids:
                return []
            matrix = np.vstack(self._vectors)
            query = np.asarray(query_vector, dtype=np.float32)
            query_norm = query / (np.linalg.norm(query) + 1e-9)
            matrix_norm = matrix / (
                np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9
            )
            scores = matrix_norm @ query_norm

            results: List[Tuple[str, float, dict]] = []
            for idx in np.argsort(scores)[::-1]:
                chunk_id = self._ids[idx]
                meta = self._meta.get(chunk_id, {})
                if predicate is not None and not predicate(meta):
                    continue
                results.append((chunk_id, float(scores[idx]), meta))
                if len(results) >= top_k:
                    break
            return results

    def count(self) -> int:
        return len(self._ids)


_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store

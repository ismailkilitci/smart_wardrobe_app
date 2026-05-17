from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class VectorSearchResult:
    item_id: str
    score: float


class VectorIndex:
    """Small FAISS-compatible vector index wrapper with a pure-Python fallback."""

    def __init__(self, dimension: int) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be positive")
        self.dimension = dimension
        self._ids: list[str] = []
        self._vectors: list[list[float]] = []
        self._faiss_index = None
        try:
            import faiss  # type: ignore
            import numpy as np  # type: ignore

            self._np = np
            self._faiss_index = faiss.IndexFlatIP(dimension)
        except Exception:
            self._np = None

    @property
    def backend(self) -> str:
        return "faiss" if self._faiss_index is not None else "python"

    def add(self, item_id: str, vector: Iterable[float]) -> None:
        normalized = self._normalize(vector)
        self._ids.append(item_id)
        self._vectors.append(normalized)
        if self._faiss_index is not None and self._np is not None:
            arr = self._np.array([normalized], dtype="float32")
            self._faiss_index.add(arr)

    def search(self, vector: Iterable[float], top_k: int = 5) -> list[VectorSearchResult]:
        if top_k <= 0 or not self._ids:
            return []
        query = self._normalize(vector)
        if self._faiss_index is not None and self._np is not None:
            scores, indexes = self._faiss_index.search(
                self._np.array([query], dtype="float32"),
                min(top_k, len(self._ids)),
            )
            return [
                VectorSearchResult(self._ids[int(idx)], float(score))
                for score, idx in zip(scores[0], indexes[0])
                if int(idx) >= 0
            ]

        rows = [
            VectorSearchResult(item_id, sum(a * b for a, b in zip(query, stored)))
            for item_id, stored in zip(self._ids, self._vectors)
        ]
        rows.sort(key=lambda row: row.score, reverse=True)
        return rows[:top_k]

    def _normalize(self, vector: Iterable[float]) -> list[float]:
        values = [float(v) for v in vector]
        if len(values) != self.dimension:
            raise ValueError(f"expected vector dimension {self.dimension}, got {len(values)}")
        norm = math.sqrt(sum(v * v for v in values))
        if norm == 0:
            raise ValueError("zero vector cannot be indexed")
        return [v / norm for v in values]

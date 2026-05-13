"""Optional vector retrieval backend with graceful fallback.

This module keeps the project runnable even when vector DB dependencies
are unavailable in the environment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class VectorHit:
    id: str
    score: float
    payload: Dict[str, Any]


class VectorStoreBackend:
    """Thin wrapper around optional vector-db implementations.

    Supported backends:
    - "none": disabled
    - "chroma": optional; requires chromadb package
    """

    def __init__(
        self,
        backend: str = "none",
        collection_name: str = "memories",
        persist_path: str | None = None,
    ) -> None:
        self.backend = (backend or "none").lower()
        self.collection_name = collection_name
        self.persist_path = persist_path or os.getenv("CHROMA_DB_PATH", "chroma_db")
        self.available = False
        self._collection = None

        if self.backend == "chroma":
            try:
                import chromadb  # type: ignore

                client = chromadb.PersistentClient(path=self.persist_path)
                self._collection = client.get_or_create_collection(name=collection_name)
                self.available = True
            except Exception:
                self.available = False

    def add(self, doc_id: str, content: str, metadata: Dict[str, Any] | None = None) -> None:
        if not self.available or self.backend != "chroma" or self._collection is None:
            return
        clean_metadata = self._clean_metadata(metadata or {})
        if hasattr(self._collection, "upsert"):
            self._collection.upsert(
                ids=[doc_id],
                documents=[content],
                metadatas=[clean_metadata],
            )
            return
        try:
            self._collection.delete(ids=[doc_id])
        except Exception:
            pass
        self._collection.add(ids=[doc_id], documents=[content], metadatas=[clean_metadata])

    @staticmethod
    def _clean_metadata(metadata: Dict[str, Any]) -> Dict[str, str | int | float | bool]:
        clean: Dict[str, str | int | float | bool] = {}
        for key, value in metadata.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                clean[key] = value
            else:
                clean[key] = str(value)
        return clean

    def search(
        self, query: str, top_k: int = 10, filters: dict[str, Any] | None = None
    ) -> List[VectorHit]:
        if not self.available or self.backend != "chroma" or self._collection is None:
            return []
        result = self._collection.query(
            query_texts=[query],
            n_results=top_k,
            where=filters if filters else None,
        )
        ids = (result.get("ids") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        hits: List[VectorHit] = []
        for i, mid in enumerate(ids):
            dist = float(distances[i]) if i < len(distances) else 1.0
            # Convert distance-like signal to score-like signal.
            score = 1.0 / (1.0 + max(0.0, dist))
            payload = metadatas[i] if i < len(metadatas) and isinstance(metadatas[i], dict) else {}
            hits.append(VectorHit(id=str(mid), score=score, payload=payload))
        return hits

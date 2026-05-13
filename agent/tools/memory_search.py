"""Memory retrieval tool with time-decay re-ranking."""

from __future__ import annotations

from typing import Any, Dict, List

from memory import LongTermMemory, OpenSourceMemoryHub, VectorStoreBackend, rerank_top_k


class MemorySearch:
    """Search long-term memories and return ranked hits."""

    def __init__(
        self,
        ltm: LongTermMemory | None = None,
        *,
        db_path: str = "memory.db",
        candidate_k: int = 30,
        top_k: int = 5,
        decay_lambda: float = 0.05,
        retrieval_backend: str = "chroma",
        open_source_memory_hub: OpenSourceMemoryHub | None = None,
        vector_persist_path: str | None = None,
    ) -> None:
        self.ltm = ltm or LongTermMemory(db_path=db_path)
        self.candidate_k = candidate_k
        self.top_k = top_k
        self.decay_lambda = decay_lambda
        self.vector_store = VectorStoreBackend(
            backend=retrieval_backend,
            collection_name="memories",
            persist_path=vector_persist_path,
        )
        self.open_source_memory_hub = open_source_memory_hub or OpenSourceMemoryHub()

    def run(
        self,
        query: str = "",
        context: Any = None,
        status_filter: str | None = "active",
        mtype_filter: str | None = None,
        **_: Any,
    ) -> Dict[str, Any]:
        if not query.strip():
            return {"tool": "memory_search", "query": query, "hits": [], "text": ""}

        if isinstance(context, dict):
            if "status_filter" in context and status_filter == "active":
                status_filter = context.get("status_filter")
            if "mtype_filter" in context and mtype_filter is None:
                mtype_filter = context.get("mtype_filter")

        user_id_filter: str | None = None
        if isinstance(context, dict):
            uid = context.get("user_id")
            if isinstance(uid, str):
                normalized_uid = uid.strip()
                if normalized_uid:
                    user_id_filter = normalized_uid

        candidates: List[Dict[str, Any]] = []
        memory_rows = self.ltm.list_memories(
            status=status_filter,
            mtype=mtype_filter,
            user_id=user_id_filter,
            limit=self.candidate_k,
        )

        stm_text = ""
        user_id = ""
        enable_mimo_analysis = False
        if isinstance(context, dict):
            stm = context.get("stm")
            if stm is not None:
                stm_text = str(stm)
            uid = context.get("user_id")
            if isinstance(uid, str):
                user_id = uid
            raw_flag = context.get("enable_mimo_analysis")
            if isinstance(raw_flag, bool):
                enable_mimo_analysis = raw_flag
        external_hints = self.open_source_memory_hub.collect_hints(
            user_id=user_id or "anonymous",
            query=query,
            stm_text=stm_text,
            ltm_rows=memory_rows,
            enable_mimo_analysis=enable_mimo_analysis,
        )
        expansion = " ".join([str(x) for x in external_hints.get("query_expansion", [])])
        effective_query = f"{query} {expansion}".strip() if expansion else query

        if self.vector_store.available:
            for row in memory_rows:
                self.vector_store.add(
                    doc_id=str(row.get("id", "")),
                    content=str(row.get("content", "")),
                    metadata={
                        "type": row.get("type"),
                        "importance": row.get("importance"),
                        "status": row.get("status"),
                        "ts": row.get("ts"),
                        "user_id": row.get("user_id"),
                    },
                )

        # Preferred path: vector retrieval if backend is available.
        vector_hits = self.vector_store.search(
            effective_query,
            top_k=self.candidate_k,
            filters={"user_id": user_id_filter} if user_id_filter else None,
        )
        vector_candidates = 0
        if vector_hits:
            for hit in vector_hits:
                mem = self.ltm.get_memory(hit.id)
                if not mem:
                    continue
                if status_filter is not None and mem.get("status") != status_filter:
                    continue
                if mtype_filter is not None and mem.get("type") != mtype_filter:
                    continue
                if user_id_filter is not None and mem.get("user_id") != user_id_filter:
                    continue
                if mem:
                    # Keep vector score as an additional signal for debugging.
                    mem["vector_score"] = hit.score
                    candidates.append(mem)
                    vector_candidates += 1

        # Fallback path: SQL LIKE retrieval.
        if not candidates:
            candidates = self.ltm.text_search(
                effective_query, status=status_filter, user_id=user_id_filter, limit=self.candidate_k
            )
            if mtype_filter is not None:
                candidates = [c for c in candidates if c.get("type") == mtype_filter]
            if user_id_filter is not None:
                candidates = [c for c in candidates if c.get("user_id") == user_id_filter]
        if not candidates:
            # Fallback for order/wording mismatch in simple SQL LIKE retrieval.
            candidates = memory_rows
        hits: List[Dict[str, Any]] = rerank_top_k(
            query=query,
            candidates=candidates,
            top_k=self.top_k,
            decay_lambda=self.decay_lambda,
        )
        used_vector = bool(vector_candidates and hits)
        if not hits and candidates is not memory_rows:
            candidates = memory_rows
            hits = rerank_top_k(
                query=query,
                candidates=candidates,
                top_k=self.top_k,
                decay_lambda=self.decay_lambda,
            )
            used_vector = False

        summary_lines = [f"- {h.get('content', '')}" for h in hits]
        if stm_text:
            summary_lines.append(f"[stm] {stm_text}")

        return {
            "tool": "memory_search",
            "query": query,
            "backend": "vector" if used_vector else "sql_fallback",
            "status_filter": status_filter,
            "mtype_filter": mtype_filter,
            "user_id_filter": user_id_filter,
            "open_source_memory": external_hints,
            "hits": hits,
            "text": "\n".join(summary_lines),
        }

    def store_interaction(self, *, user_id: str, user_input: str, assistant_output: str) -> Dict[str, Any]:
        if self.open_source_memory_hub is None:
            return {}
        return self.open_source_memory_hub.store_interaction(
            user_id=user_id,
            user_input=user_input,
            assistant_output=assistant_output,
        )

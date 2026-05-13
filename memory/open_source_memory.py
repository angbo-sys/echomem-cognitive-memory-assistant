from __future__ import annotations

import asyncio
import json
import math
import os
import queue
import re
import sys
import threading
import importlib.util
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from llm.deepseek_adapter import DeepSeekAdapter
from llm.mimo_adapter import MiMoAdapter
from .retrieval import lexical_similarity


# ---------------------------------------------------------------------------
# Enhanced text matching utilities
# ---------------------------------------------------------------------------

_STOPWORDS = frozenset({
    "用户", "偏好", "目标", "学习", "回答", "喜欢", "需要", "the", "and", "user",
    "一个", "可以", "这个", "那个", "什么", "怎么", "如何", "请", "帮", "我",
})


def _ngram_tokenize(text: str, n_range: Tuple[int, int] = (2, 4)) -> List[str]:
    """Extract Chinese N-gram tokens and whitespace-delimited words."""
    normalized = re.sub(r"[^\w一-鿿]+", " ", text.lower())
    tokens: List[str] = []
    for word in normalized.split():
        if len(word) >= 2:
            tokens.append(word)
        # Chinese character N-grams
        if re.fullmatch(r"[一-鿿]+", word) and len(word) > 1:
            for n in range(n_range[0], min(n_range[1] + 1, len(word) + 1)):
                for i in range(len(word) - n + 1):
                    tokens.append(word[i:i + n])
    return [t for t in tokens if t not in _STOPWORDS]


def _bm25_score(query_tokens: List[str], doc_tokens: List[str], k1: float = 1.5, b: float = 0.75) -> float:
    """Simplified BM25 scoring between query and document token lists."""
    if not query_tokens or not doc_tokens:
        return 0.0
    doc_counter = Counter(doc_tokens)
    doc_len = len(doc_tokens)
    avg_dl = max(doc_len, 1)
    score = 0.0
    for qt in query_tokens:
        tf = doc_counter.get(qt, 0)
        if tf == 0:
            continue
        idf = math.log(1.0 + 1.0 / (tf + 0.5))
        numerator = tf * (k1 + 1)
        denominator = tf + k1 * (1 - b + b * doc_len / avg_dl)
        score += idf * numerator / denominator
    return score


def _ngram_similarity(text_a: str, text_b: str) -> float:
    """Compute Jaccard similarity over N-gram tokens."""
    tokens_a = set(_ngram_tokenize(text_a))
    tokens_b = set(_ngram_tokenize(text_b))
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def _top_bm25_matches(query: str, texts: List[str], top_k: int = 3) -> List[str]:
    """Rank texts by BM25 score against query, return top-k."""
    query_tokens = _ngram_tokenize(query)
    scored: List[Tuple[float, str]] = []
    for text in texts:
        doc_tokens = _ngram_tokenize(text)
        score = _bm25_score(query_tokens, doc_tokens)
        if score > 0:
            scored.append((score, text))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored[:top_k]]


def _top_ngram_matches(query: str, texts: List[str], top_k: int = 3) -> List[str]:
    """Rank texts by N-gram Jaccard similarity, return top-k."""
    scored: List[Tuple[float, str]] = []
    for text in texts:
        score = _ngram_similarity(query, text)
        if score > 0:
            scored.append((score, text))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored[:top_k]]


def _combined_top_matches(query: str, texts: List[str], top_k: int = 3) -> List[str]:
    """Combine BM25 and N-gram similarity for robust matching."""
    query_tokens = _ngram_tokenize(query)
    scored: List[Tuple[float, str]] = []
    for text in texts:
        doc_tokens = _ngram_tokenize(text)
        bm25 = _bm25_score(query_tokens, doc_tokens)
        ngram = _ngram_similarity(query, text)
        combined = 0.6 * bm25 + 0.4 * ngram * 10  # normalize scales
        if combined > 0:
            scored.append((combined, text))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored[:top_k]]


# Keep backward-compatible alias
def _top_lexical_matches(query: str, texts: Iterable[str], top_k: int = 3) -> List[str]:
    return _combined_top_matches(query, list(texts), top_k=top_k)


def _memory_content(row: Dict[str, Any]) -> str:
    return str(row.get("content", "")).strip()


def _row_type(row: Dict[str, Any]) -> str:
    return str(row.get("type", "")).strip().lower()


def _keyword_matches(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in keywords)


def _humanize_signal(text: Any, limit: int = 160) -> str:
    """Make framework signals readable enough to be useful in Prompt/UI."""
    raw = str(text or "").strip()
    if not raw:
        return ""
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and parsed.get("field") and parsed.get("value") is not None:
            raw = f"{parsed.get('field')}: {parsed.get('value')}"
    except (TypeError, ValueError, json.JSONDecodeError):
        pass
    raw = re.sub(r"\s+", " ", raw)
    return raw[:limit].strip()


def _dedupe_signals(items: Iterable[Any], *, limit: int = 5) -> List[str]:
    signals: List[str] = []
    seen: set[str] = set()
    for item in items:
        text = _humanize_signal(item)
        if not text or text in seen:
            continue
        seen.add(text)
        signals.append(text)
        if len(signals) >= limit:
            break
    return signals


def _tokenize_concepts(text: str) -> List[str]:
    normalized = re.sub(r"[^\w一-鿿]+", " ", text.lower())
    tokens = [t.strip() for t in normalized.split() if len(t.strip()) >= 2]
    expanded: List[str] = []
    for token in tokens:
        expanded.append(token)
        if re.fullmatch(r"[一-鿿]+", token) and len(token) > 2:
            for size in range(2, min(6, len(token)) + 1):
                for idx in range(0, len(token) - size + 1):
                    expanded.append(token[idx : idx + size])
    deduped: List[str] = []
    seen: set[str] = set()
    for token in expanded:
        if token in _STOPWORDS or token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped


def _base_concepts(text: str) -> List[str]:
    normalized = re.sub(r"[^\w一-鿿]+", " ", text.lower())
    concepts = [t.strip() for t in normalized.split() if len(t.strip()) >= 2]
    return [c for c in concepts if c not in _STOPWORDS]


def _concept_overlaps(query_terms: set[str], concept: str) -> bool:
    return any(term in concept or concept in term for term in query_terms)


# ---------------------------------------------------------------------------
# Entity extraction for knowledge graph
# ---------------------------------------------------------------------------

_SUBJECT_KEYWORDS = frozenset({
    "数学", "英语", "物理", "化学", "生物", "语文", "历史", "地理", "政治",
    "编程", "算法", "数据结构", "阅读", "写作", "听力", "口语", "概率论",
    "线性代数", "微积分", "统计", "机器学习", "深度学习",
})

_GOAL_KEYWORDS = frozenset({
    "目标", "计划", "准备", "打算", "想要", "希望", "考研", "高考", "雅思",
    "托福", "考级", "竞赛",
})

_STRUGGLE_KEYWORDS = frozenset({
    "薄弱", "不会", "困难", "不懂", "难", "差", "弱", "搞不定", "搞不懂",
})


def _extract_entities(text: str) -> List[Dict[str, str]]:
    """Extract typed entities from text for knowledge graph construction."""
    entities: List[Dict[str, str]] = []
    normalized = text.lower()

    for kw in _SUBJECT_KEYWORDS:
        if kw in normalized:
            entities.append({"name": kw, "type": "subject"})

    for kw in _GOAL_KEYWORDS:
        if kw in normalized:
            # Try to extract the goal target
            match = re.search(rf"{kw}[：:是为]?\s*(.{{2,20}}?)(?:[，。；\s]|$)", text)
            if match:
                entities.append({"name": match.group(1).strip(), "type": "goal"})
            else:
                entities.append({"name": kw, "type": "goal"})

    for kw in _STRUGGLE_KEYWORDS:
        if kw in normalized:
            match = re.search(rf"{kw}[的是在]?\s*(.{{2,20}}?)(?:[，。；\s]|$)", text)
            if match:
                entities.append({"name": match.group(1).strip(), "type": "struggle"})

    return entities


# ---------------------------------------------------------------------------
# User Knowledge Graph (enhanced)
# ---------------------------------------------------------------------------

class UserKnowledgeGraph:
    """Build a lightweight user knowledge system with typed edges."""

    _SEP = re.compile(r"[，,。；;：:\n]+")

    def build(self, texts: List[str], max_edges: int = 120) -> Dict[str, Any]:
        nodes: Dict[str, str] = {}  # name -> type
        edges: List[Dict[str, str]] = []

        # Phase 1: Extract entities from all texts
        for text in texts:
            entities = _extract_entities(text)
            for ent in entities:
                name = ent["name"][:48]
                if name not in nodes:
                    nodes[name] = ent["type"]

        # Phase 2: Build edges from entity co-occurrence and text structure
        for text in texts:
            parts = [p.strip() for p in self._SEP.split(text) if p.strip()]
            if len(parts) < 2:
                continue

            # Structured edge from comma-separated parts
            root = parts[0][:48]
            if root not in nodes:
                nodes[root] = "topic"
            for item in parts[1:]:
                leaf = item[:48]
                if leaf not in nodes:
                    nodes[leaf] = "detail"

                # Infer edge type from content
                relation = self._infer_relation(root, leaf, text)
                edge = {"source": root, "relation": relation, "target": leaf}
                if edge not in edges:
                    edges.append(edge)
                if len(edges) >= max_edges:
                    break
            if len(edges) >= max_edges:
                break

        # Phase 3: Build semantic edges between entities of the same text
        for text in texts:
            entities = _extract_entities(text)
            subjects = [e["name"] for e in entities if e["type"] == "subject"]
            struggles = [e["name"] for e in entities if e["type"] == "struggle"]
            goals = [e["name"] for e in entities if e["type"] == "goal"]

            for s in subjects:
                for st in struggles:
                    edge = {"source": s, "relation": "struggles_with", "target": st}
                    if edge not in edges and len(edges) < max_edges:
                        edges.append(edge)
                for g in goals:
                    edge = {"source": s, "relation": "aims_for", "target": g}
                    if edge not in edges and len(edges) < max_edges:
                        edges.append(edge)

        if not nodes:
            return {"nodes": [], "edges": [], "mermaid": "graph TD\n  Empty[No Knowledge Yet]"}

        return {
            "nodes": sorted(nodes.keys()),
            "node_types": nodes,
            "edges": edges,
            "mermaid": self.to_mermaid(edges),
        }

    @staticmethod
    def _infer_relation(source: str, target: str, context: str) -> str:
        """Infer semantic relation type from context."""
        normalized = context.lower()
        if _keyword_matches(normalized, ("薄弱", "不会", "困难", "差", "弱")):
            return "struggles_with"
        if _keyword_matches(normalized, ("目标", "计划", "准备", "想要")):
            return "aims_for"
        if _keyword_matches(normalized, ("喜欢", "偏好", "擅长", "拿手")):
            return "excels_at"
        return "contains"

    @staticmethod
    def to_mermaid(edges: List[Dict[str, str]]) -> str:
        lines = ["graph TD"]
        if not edges:
            lines.append("  Empty[No Knowledge Yet]")
            return "\n".join(lines)
        for i, edge in enumerate(edges):
            s = edge["source"].replace('"', "'")
            t = edge["target"].replace('"', "'")
            r = edge["relation"].replace('"', "'")
            lines.append(f'  N{i}["{s}"] -->|{r}| M{i}["{t}"]')
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Framework hint
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FrameworkHint:
    framework: str
    available: bool
    details: Dict[str, Any]


# ---------------------------------------------------------------------------
# Mem0Adapter — real integration with enhanced fallback
# ---------------------------------------------------------------------------

class Mem0Adapter:
    """Mem0: real memory backend with cloud API or local fallback."""

    def __init__(
        self,
        *,
        mem0_api_key: str = "",
        llm_api_key: str = "",
        llm_base_url: str = "",
        llm_model: str = "",
        embedder_provider: str = "fastembed",
        embedder_model: str = "BAAI/bge-small-en-v1.5",
        vector_store_provider: str = "faiss",
        vector_store_path: str = "",
    ) -> None:
        self.available = False
        self._client: Any = None
        self._memory: Any = None
        self._is_cloud = False
        self._local_mode = False
        self.cloud_configured = bool(mem0_api_key)
        self.cloud_init_error = ""
        self.api_call_count = 0

        # Priority 1: Cloud API (mem0 hosted)
        if mem0_api_key:
            try:
                from mem0 import MemoryClient  # type: ignore
                self._client = MemoryClient(api_key=mem0_api_key)
                self._is_cloud = True
                self.available = True
                return
            except Exception as exc:
                self.cloud_init_error = f"{type(exc).__name__}: {exc}"

        # Priority 2: Local Memory with fastembed + faiss
        try:
            from mem0 import Memory  # type: ignore
            from mem0.configs.base import MemoryConfig, VectorStoreConfig, LlmConfig, EmbedderConfig  # type: ignore

            embedder_dims = 384 if embedder_provider == "fastembed" else 1536
            faiss_path = vector_store_path or os.path.join(os.getcwd(), ".mem0_faiss")

            mem0_cfg = MemoryConfig(
                embedder=EmbedderConfig(
                    provider=embedder_provider,
                    config={"model": embedder_model, "embedding_dims": embedder_dims},
                ),
                vector_store=VectorStoreConfig(
                    provider=vector_store_provider,
                    config={"path": faiss_path, "embedding_model_dims": embedder_dims},
                ),
            )
            if llm_api_key and llm_base_url:
                mem0_cfg.llm = LlmConfig(
                    provider="openai",
                    config={
                        "api_key": llm_api_key,
                        "openai_base_url": llm_base_url,
                        "model": llm_model or "deepseek-v4-flash",
                    },
                )
            self._memory = Memory(mem0_cfg)
            self.available = True
        except Exception:
            self._local_mode = True

    def store(self, content: str, user_id: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store a memory via Mem0 backend. Returns True if stored."""
        try:
            if self._is_cloud and self._client is not None:
                self.api_call_count += 1
                self._client.add(content, user_id=user_id, metadata=metadata or {})
                return True
            if self._memory is not None:
                self._memory.add(content, user_id=user_id, metadata=metadata or {})
                return True
        except Exception:
            pass
        return False

    def search(self, query: str, user_id: str, limit: int = 5) -> List[str]:
        """Semantic search via Mem0 backend. Returns list of memory strings."""
        try:
            results = None
            if self._is_cloud and self._client is not None:
                self.api_call_count += 1
                results = self._client.search(query, filters={"user_id": user_id})
            elif self._memory is not None:
                results = self._memory.search(query, filters={"user_id": user_id})
            if results is not None:
                if isinstance(results, dict):
                    results = results.get("results", results.get("memories", []))
                return [str(r.get("memory", r.get("text", ""))) for r in results if r]
        except Exception:
            pass
        return []

    def get_user_facts(self, user_id: str, ltm_rows: List[Dict[str, Any]], query: str) -> FrameworkHint:
        # Try real Mem0 search first
        mem0_results = self.search(query, user_id, limit=3)

        preference_rows: List[str] = []
        fact_rows: List[str] = []
        goal_rows: List[str] = []
        for row in ltm_rows:
            content = _memory_content(row)
            if not content:
                continue
            mtype = _row_type(row)
            if mtype == "preference" or _keyword_matches(content, ("偏好", "喜欢", "风格", "prefer", "style")):
                preference_rows.append(content)
            elif mtype == "goal" or _keyword_matches(content, ("目标", "计划", "准备", "goal")):
                goal_rows.append(content)
            else:
                fact_rows.append(content)

        # Use Mem0 results if available, otherwise enhanced fallback
        if mem0_results:
            facts = _dedupe_signals(mem0_results, limit=3)
            signal_source = "mem0_semantic_search"
        else:
            profile_pool = preference_rows + goal_rows
            ranked = _combined_top_matches(query, profile_pool, top_k=3)
            facts = _dedupe_signals(ranked or profile_pool[:3] or fact_rows[:3], limit=3)
            signal_source = "mem0_enhanced_fallback" if self._local_mode else "mem0_local_profile_index"

        details = {
            "available": self.available,
            "signal_source": signal_source,
            "sdk": "mem0.MemoryClient" if self._is_cloud else ("mem0.Memory" if self._memory is not None else "enhanced_local"),
            "facts": facts,
            "preferences": _dedupe_signals(preference_rows, limit=3),
            "goals": _dedupe_signals(goal_rows, limit=3),
            "mem0_search_used": bool(mem0_results),
            "cloud_configured": self.cloud_configured,
            "cloud_available": self._is_cloud,
            "cloud_api_used": bool(self._is_cloud and mem0_results),
            "cloud_api_call_count": self.api_call_count,
            "cloud_init_error": self.cloud_init_error,
            "value_summary": "提取用户偏好、目标和画像事实，用于个性化回复",
        }
        return FrameworkHint("mem0", self.available or self._local_mode, details)


# ---------------------------------------------------------------------------
# LlamaCloudAdapter — cloud document parsing via LlamaCloud API
# ---------------------------------------------------------------------------

class LlamaCloudAdapter:
    """LlamaCloud: cloud document parsing and structured extraction."""

    def __init__(self, api_key: str = "") -> None:
        self.available = False
        self._client: Any = None
        self.cloud_configured = bool(api_key)
        self.init_error = ""
        self.api_call_count = 0
        if not api_key:
            return
        try:
            from llama_cloud import LlamaCloud  # type: ignore
            self._client = LlamaCloud(api_key=api_key)
            self.available = True
        except Exception as exc:
            local_deps = os.path.join(os.getcwd(), ".deps", f"py{sys.version_info.major}{sys.version_info.minor}")
            if os.path.isdir(local_deps) and local_deps not in sys.path:
                sys.path.append(local_deps)
                try:
                    from llama_cloud import LlamaCloud  # type: ignore
                    self._client = LlamaCloud(api_key=api_key)
                    self.available = True
                    self.init_error = ""
                    return
                except Exception as retry_exc:
                    exc = retry_exc
            self.init_error = f"{type(exc).__name__}: {exc}"

    def parse_document(self, file_path: str) -> Optional[str]:
        """Parse a document to Markdown via LlamaCloud."""
        if not self.available or self._client is None:
            return None
        try:
            self.api_call_count += 1
            with open(file_path, "rb") as file_obj:
                result = self._client.parsing.parse(
                    upload_file=(os.path.basename(file_path), file_obj.read()),
                    tier="cost_effective",
                    version="latest",
                    expand=["markdown"],
                    timeout=120,
                )
            if result.markdown and result.markdown.pages:
                return result.markdown.pages[0].markdown
            return None
        except Exception:
            return None

    def parse_text(self, text: str, filename: str = "document.txt") -> Optional[str]:
        """Parse plain text via LlamaParse. Useful for connectivity tests."""
        if not self.available or self._client is None or not text.strip():
            return None
        try:
            self.api_call_count += 1
            result = self._client.parsing.parse(
                upload_file=(filename, text.encode("utf-8"), "text/plain"),
                tier="cost_effective",
                version="latest",
                expand=["markdown"],
                timeout=120,
            )
            if result.markdown and result.markdown.pages:
                return result.markdown.pages[0].markdown
            return None
        except Exception:
            return None

    def extract_structured(self, file_path: str, schema: dict) -> Optional[dict]:
        """Extract structured data from a document via LlamaCloud."""
        if not self.available or self._client is None:
            return None
        try:
            self.api_call_count += 1
            file = self._client.files.create(file=file_path, purpose="extract")
            job = self._client.extract.create(
                document_input_value=file.id,
                config={"extract_options": {"data_schema": schema, "tier": "agentic"}},
            )
            return job.extract_result
        except Exception:
            return None


# ---------------------------------------------------------------------------
# LlamaIndexMemoryAdapter — real integration with enhanced fallback
# ---------------------------------------------------------------------------

class LlamaIndexMemoryAdapter:
    """LlamaIndex memory: real buffer with enhanced BM25 fallback."""

    def __init__(self, token_limit: int = 30000) -> None:
        self.available = False
        self._memory: Any = None
        self._chat_msg_cls: Any = None
        try:
            from llama_index.core.memory import Memory  # type: ignore
            from llama_index.core.llms import ChatMessage  # type: ignore
            self._memory = Memory(token_limit=token_limit)
            self._chat_msg_cls = ChatMessage
            self.available = True
        except Exception:
            pass

    def add_conversation(self, user_input: str, assistant_output: str) -> bool:
        """Add a conversation turn to the memory buffer."""
        if not self.available or self._memory is None or self._chat_msg_cls is None:
            return False
        try:
            self._memory.put(self._chat_msg_cls(role="user", content=user_input))
            self._memory.put(self._chat_msg_cls(role="assistant", content=assistant_output))
            return True
        except Exception:
            return False

    def add_documents(self, documents: List[str]) -> int:
        """Add documents to LlamaIndex memory buffer. Returns count added."""
        if self._memory is None or self._chat_msg_cls is None:
            return 0
        count = 0
        for doc in documents[:24]:
            try:
                self._memory.put(self._chat_msg_cls(role="user", content=doc))
                count += 1
            except Exception:
                break
        return count

    def retrieve(self, query: str, ltm_rows: List[Dict[str, Any]]) -> FrameworkHint:
        docs = [str(r.get("content", "")) for r in ltm_rows if str(r.get("content", "")).strip()]
        memory_items: List[str] = []

        # Try real LlamaIndex Memory retrieval
        if self._memory is not None:
            try:
                # Add docs to memory if not already present
                self.add_documents(docs[:24])
                messages = self._memory.get(input=query)
                memory_items = [str(item.content) for item in messages if str(item.content).strip()]
            except Exception:
                memory_items = []

        if memory_items:
            doc_hits = _dedupe_signals(_combined_top_matches(query, memory_items, top_k=3), limit=3)
            signal_source = "llamaindex_memory_buffer"
        else:
            # Enhanced fallback: BM25 scoring
            doc_hits = _top_bm25_matches(query, docs, top_k=3)
            if not doc_hits:
                doc_hits = _top_ngram_matches(query, docs, top_k=3)
            doc_hits = _dedupe_signals(doc_hits, limit=3)
            signal_source = "llamaindex_enhanced_fallback" if not self.available else "llamaindex_local_doc_index"

        details: Dict[str, Any] = {
            "available": self.available,
            "signal_source": signal_source,
            "doc_hits": doc_hits,
            "memory_items": _dedupe_signals(memory_items, limit=5),
            "llamaindex_search_used": bool(memory_items),
            "value_summary": "检索会话/文档式知识证据，用于增强回答依据",
        }
        if self._memory is not None:
            details["memory_api"] = "llama_index.core.memory.Memory"
        return FrameworkHint("llamaindex_memory", self.available or bool(doc_hits), details)


# ---------------------------------------------------------------------------
# CogneeCloudAdapter — cloud knowledge graph via Cognee Cloud API
# ---------------------------------------------------------------------------

class CogneeCloudAdapter:
    """Cognee Cloud: cloud-hosted knowledge graph service."""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
        dataset_name: str = "echomem",
        node_set: str | Iterable[str] = "",
        search_type: str = "GRAPH_COMPLETION",
    ) -> None:
        self.available = False
        self._api_key = api_key
        self._base_url = base_url.rstrip("/") if base_url else ""
        self._dataset_name = dataset_name.strip() or "echomem"
        self._node_set = self._normalize_node_set(node_set)
        self._search_type = (search_type or "GRAPH_COMPLETION").strip().upper()
        self._headers = {"X-Api-Key": api_key, "Content-Type": "application/json"} if api_key else {}
        self.api_call_count = 0
        self.last_error = ""
        if api_key and base_url:
            self.available = True

    @staticmethod
    def _normalize_node_set(node_set: str | Iterable[str]) -> List[str]:
        if isinstance(node_set, str):
            raw_items = node_set.split(",")
        else:
            raw_items = list(node_set)
        normalized: List[str] = []
        seen: set[str] = set()
        for item in raw_items:
            value = str(item).strip()
            if not value or value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        return normalized

    def _request(self, method: str, path: str, **kwargs: Any) -> Optional[Any]:
        """Send an API request to Cognee Cloud."""
        import urllib.request
        import urllib.error
        import json as _json
        if not self._api_key or not self._base_url:
            return None
        try:
            url = f"{self._base_url}{path}"
            data = _json.dumps(kwargs.get("json", {})).encode() if "json" in kwargs else None
            req = urllib.request.Request(
                url,
                data=data,
                headers=self._headers,
                method=method,
            )
            self.api_call_count += 1
            with urllib.request.urlopen(req, timeout=15) as resp:
                return _json.loads(resp.read().decode())
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            return None

    def add_knowledge(self, texts: List[str]) -> bool:
        """Add knowledge to the cloud graph."""
        if not self.available:
            return False
        clean_texts = [str(text).strip() for text in texts[:10] if str(text).strip()]
        if not clean_texts:
            return False
        add_payload: Dict[str, Any] = {
            "textData": clean_texts,
            "datasetName": self._dataset_name,
        }
        if self._node_set:
            add_payload["nodeSet"] = self._node_set
        added = self._request(
            "POST",
            "/api/v1/add_text",
            json=add_payload,
        )
        if added is None:
            return False
        cognified = self._request(
            "POST",
            "/api/v1/cognify",
            json={"datasets": [self._dataset_name], "runInBackground": False},
        )
        return cognified is not None

    def search_graph(self, query: str, limit: int = 5) -> List[str]:
        """Search the cloud knowledge graph."""
        if not self.available:
            return []
        search_payload: Dict[str, Any] = {
            "searchType": self._search_type,
            "query": query,
            "datasets": [self._dataset_name],
            "topK": limit,
            "onlyContext": True,
        }
        if self._node_set:
            search_payload["nodeName"] = self._node_set
        result = self._request(
            "POST",
            "/api/v1/search",
            json=search_payload,
        )
        if result is None:
            return []
        if isinstance(result, dict):
            items = result.get("results", result.get("data", []))
        elif isinstance(result, list):
            items = result
        else:
            return []
        signals: List[str] = []
        for item in items:
            text = self._extract_search_text(item)
            if text:
                signals.append(text)
            if len(signals) >= limit:
                break
        return signals

    @classmethod
    def _extract_search_text(cls, item: Any) -> str:
        if isinstance(item, dict):
            value = item.get("search_result", item.get("text", item.get("context", "")))
            if isinstance(value, (dict, list)):
                return _humanize_signal(json.dumps(value, ensure_ascii=False))
            return _humanize_signal(value)
        if isinstance(item, (list, tuple)):
            return _humanize_signal(" ".join(cls._extract_search_text(part) for part in item))
        return _humanize_signal(item)


# ---------------------------------------------------------------------------
# CogneeAdapter — real integration with enhanced fallback
# ---------------------------------------------------------------------------

class CogneeAdapter:
    """Cognee: real knowledge graph with enhanced concept fallback."""

    def __init__(
        self,
        cloud_adapter: Optional[CogneeCloudAdapter] = None,
        *,
        enable_local: bool = True,
    ) -> None:
        self.available = False
        self._cognee: Any = None
        self._cloud = cloud_adapter
        if enable_local:
            os.environ.setdefault("COGNEE_SKIP_CONNECTION_TEST", "true")
            try:
                import cognee  # type: ignore
                self._cognee = cognee
                self.available = True
            except Exception:
                pass
        # Cloud adapter makes it "available" even without local cognee
        if self._cloud is not None and self._cloud.available:
            self.available = True

    async def add_knowledge(self, texts: List[str]) -> bool:
        """Add knowledge to Cognee graph (cloud or local)."""
        # Try cloud first
        if self._cloud is not None and self._cloud.available:
            return self._cloud.add_knowledge(texts)
        # Fallback to local
        if self._cognee is None:
            return False
        try:
            for text in texts[:10]:
                await self._cognee.add(text)
            await self._cognee.cognify()
            return True
        except Exception:
            return False

    async def query_graph(self, query_text: str) -> List[str]:
        """Query Cognee knowledge graph (cloud or local)."""
        if self._cloud is not None and self._cloud.available:
            return self._cloud.search_graph(query_text)
        if self._cognee is None:
            return []
        try:
            results = await self._cognee.search(query_text)
            return [str(r) for r in results if r]
        except Exception:
            return []

    @staticmethod
    def _run_async_blocking(coro: Any) -> Any:
        """Run a coroutine from sync code, including inside an existing event loop."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        result_queue: queue.Queue[Any] = queue.Queue(maxsize=1)

        def _runner() -> None:
            try:
                result_queue.put(asyncio.run(coro))
            except Exception:
                result_queue.put(None)

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()
        thread.join(timeout=15)
        if thread.is_alive():
            return None
        return result_queue.get() if not result_queue.empty() else None

    def related_concepts(self, query: str, ltm_rows: List[Dict[str, Any]]) -> FrameworkHint:
        query_terms = set(_tokenize_concepts(query))
        relation_counts: Dict[str, int] = {}
        concept_edges: List[Dict[str, Any]] = []

        # Try cloud search first
        cloud_results: List[str] = []
        cloud_used = False
        if self._cloud is not None and self._cloud.available:
            cloud_results = self._cloud.search_graph(query, limit=5)
            cloud_used = bool(cloud_results)

        local_graph_results: List[str] = []
        local_graph_used = False
        if not cloud_used and self._cognee is not None:
            docs = [str(row.get("content", "")).strip() for row in ltm_rows if str(row.get("content", "")).strip()]
            if docs:
                self._run_async_blocking(self.add_knowledge(docs[:10]))
            graph_result = self._run_async_blocking(self.query_graph(query))
            if isinstance(graph_result, list):
                local_graph_results = [str(item) for item in graph_result if str(item).strip()][:5]
                local_graph_used = bool(local_graph_results)

        # Enhanced concept extraction with N-gram analysis
        for row in ltm_rows:
            content = str(row.get("content", ""))
            tokens = _tokenize_concepts(content)
            if not tokens or not any(_concept_overlaps(query_terms, token) for token in tokens):
                continue
            for token in tokens:
                if _concept_overlaps(query_terms, token):
                    continue
                relation_counts[token] = relation_counts.get(token, 0) + 1
            anchors = [token for token in tokens if _concept_overlaps(query_terms, token)]
            for anchor in anchors[:2]:
                # Keep a full sentence evidence edge so Chinese n-grams do not hide the actual relation.
                relation = "co_occurs"
                if _keyword_matches(content.lower(), ("目标", "计划")):
                    relation = "related_goal"
                elif _keyword_matches(content.lower(), ("薄弱", "不会", "困难")):
                    relation = "weakness_of"
                concept_edges.append({"source": anchor, "relation": relation, "target": content})
                for token in tokens[:8]:
                    if token != anchor:
                        concept_edges.append({"source": anchor, "relation": relation, "target": token})
                    if len(concept_edges) >= 24:
                        break
                if len(concept_edges) >= 24:
                    break

        related = sorted(relation_counts.items(), key=lambda x: x[1], reverse=True)[:6]
        relationship_evidence: List[str] = []
        for edge in concept_edges:
            source = _humanize_signal(edge.get("source", ""))
            relation = _humanize_signal(edge.get("relation", "")) or "related"
            target = _humanize_signal(edge.get("target", ""))
            if source and target:
                relationship_evidence.append(f"{source} -> {relation} -> {target}")
        meaningful_query_terms = [
            term
            for term in query_terms
            if len(term) >= 3 and not _keyword_matches(term, ("偏好", "详细", "解释", "关系", "我的"))
        ]

        def evidence_score(text: str) -> Tuple[int, float, int]:
            matched_meaningful_terms = sum(1 for term in meaningful_query_terms if term in text)
            return (matched_meaningful_terms, _ngram_similarity(query, text), len(text))

        relationship_evidence.sort(key=evidence_score, reverse=True)

        # Determine signal source
        if cloud_used:
            signal_source = "cognee_cloud_search"
        elif local_graph_used:
            signal_source = "cognee_local_graph_search"
        elif self.available and self._cognee is not None:
            signal_source = "cognee_local_concept_graph"
        else:
            signal_source = "cognee_enhanced_concept_graph"

        # Merge graph results with local concepts
        all_concepts = relationship_evidence + [k for k, _ in related]
        graph_results = cloud_results or local_graph_results
        if graph_results:
            for cr in graph_results:
                cr_stripped = _humanize_signal(cr)
                if cr_stripped and cr_stripped not in all_concepts:
                    all_concepts.insert(0, cr_stripped)
            all_concepts = _dedupe_signals(all_concepts, limit=8)

        details: Dict[str, Any] = {
            "available": self.available,
            "signal_source": signal_source,
            "related_concepts": _dedupe_signals(all_concepts, limit=8),
            "concept_edges": concept_edges,
            "relationship_evidence": _dedupe_signals(relationship_evidence, limit=6),
            "cognee_available": self.available,
            "cloud_configured": bool(self._cloud is not None and self._cloud._api_key and self._cloud._base_url),
            "cloud_available": bool(self._cloud is not None and self._cloud.available),
            "cloud_search_used": cloud_used,
            "cloud_api_call_count": getattr(self._cloud, "api_call_count", 0) if self._cloud else 0,
            "cloud_last_error": getattr(self._cloud, "last_error", "") if self._cloud else "",
            "local_graph_search_used": local_graph_used,
            "graph_results": graph_results,
            "value_summary": "抽取概念关系和图谱联想，用于发现相关知识连接",
        }
        return FrameworkHint("cognee", self.available or bool(all_concepts), details)


# ---------------------------------------------------------------------------
# MimoKnowledgeAnalyzer — LLM-powered knowledge analysis
# ---------------------------------------------------------------------------

class MimoKnowledgeAnalyzer:
    """Optional knowledge analysis using configured provider."""

    def __init__(
        self,
        *,
        provider: str = "mimo",
        model: str = "mimo-v2.5-pro",
        api_key: str = "",
        base_url: str = "https://token-plan-cn.xiaomimimo.com/v1",
        timeout: float = 20.0,
        use_api_key_header: bool = False,
    ) -> None:
        self.enabled = False
        self._llm: Any = None
        self._sample_limit = 60
        self._disabled_reason = "uninitialized"
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = threading.Lock()
        self.provider = provider.strip().lower() or "mimo"
        self._sample_limit = int(os.getenv("MIMO_ANALYSIS_MAX_ITEMS", "60"))
        self._wait_timeout = float(os.getenv("MIMO_ANALYSIS_WAIT_TIMEOUT", str(min(timeout, 3.0))))
        if self.provider == "deepseek":
            if not api_key.strip():
                self._disabled_reason = "missing_api_key"
                return
            self._llm = DeepSeekAdapter(
                api_key=api_key,
                base_url=base_url,
                model=model,
                timeout=timeout,
                max_retries=int(os.getenv("MIMO_MAX_RETRIES", "1")),
                retry_backoff_sec=float(os.getenv("MIMO_RETRY_BACKOFF_SEC", "0.6")),
            )
            self.enabled = True
            self._disabled_reason = ""
            return

        if not api_key.strip():
            self._disabled_reason = "missing_api_key"
            return
        self._llm = MiMoAdapter(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=timeout,
            use_api_key_header=use_api_key_header,
        )
        self.enabled = True
        self._disabled_reason = ""

    def _cache_key(self, query: str, graph: Dict[str, Any]) -> str:
        nodes = [str(x) for x in graph.get("nodes", [])[: self._sample_limit]]
        edges = [str(x) for x in graph.get("edges", [])[: self._sample_limit]]
        return repr((self.provider, query.strip(), nodes, edges))

    def _get_cached(self, key: str) -> Dict[str, Any] | None:
        with self._cache_lock:
            cached = self._cache.get(key)
            return dict(cached) if cached is not None else None

    def _store_cache(self, key: str, result: Dict[str, Any]) -> None:
        if result.get("error"):
            return
        with self._cache_lock:
            self._cache[key] = dict(result)

    def _analyze_uncached(self, query: str, graph: Dict[str, Any]) -> Dict[str, Any]:
        try:
            graph_nodes = graph.get("nodes", [])
            graph_edges = graph.get("edges", [])
            sampled_graph = {
                "nodes": graph_nodes[: self._sample_limit],
                "edges": graph_edges[: self._sample_limit],
                "mermaid": graph.get("mermaid", ""),
            }
            prompt = (
                "请根据用户知识图输出三部分：1) 当前知识体系总结 2) 知识结构建议 3) 下一步学习建议。"
                f"\n问题：{query}\n图节点数：{len(graph_nodes)}\n图边数：{len(graph_edges)}\n"
                f"图采样(JSON)：{sampled_graph}"
            )
            text = self._llm.generate(prompt)
            return {"enabled": True, "summary": text, "provider": self.provider}
        except Exception as exc:
            return {"enabled": True, "summary": "", "provider": self.provider, "error": str(exc)}

    def analyze(self, query: str, graph: Dict[str, Any], *, enabled: bool = True) -> Dict[str, Any]:
        if not enabled:
            return {
                "enabled": False,
                "summary": "",
                "provider": self.provider,
                "reason": "disabled_by_ui_toggle",
            }
        if not self.enabled or self._llm is None:
            return {
                "enabled": False,
                "summary": "",
                "provider": self.provider,
                "reason": self._disabled_reason or "not_ready",
            }
        key = self._cache_key(query, graph)
        cached = self._get_cached(key)
        if cached is not None:
            cached["cache_hit"] = True
            return cached

        results: queue.Queue[Dict[str, Any]] = queue.Queue(maxsize=1)

        def worker() -> None:
            result = self._analyze_uncached(query, graph)
            self._store_cache(key, result)
            try:
                results.put_nowait(result)
            except queue.Full:
                pass

        thread = threading.Thread(target=worker, name="mimo-knowledge-analysis", daemon=True)
        thread.start()
        try:
            return results.get(timeout=max(self._wait_timeout, 0.0))
        except queue.Empty:
            return {
                "enabled": True,
                "summary": "",
                "provider": self.provider,
                "reason": "timeout_degraded",
                "wait_timeout": self._wait_timeout,
            }


# ---------------------------------------------------------------------------
# OpenSourceMemoryHub — orchestrator
# ---------------------------------------------------------------------------

class OpenSourceMemoryHub:
    """Compose open-source memory frameworks for complementary capabilities."""

    _SCENARIO_PATTERNS: Dict[str, tuple[str, ...]] = {
        "preference_alignment": (
            "偏好", "喜欢", "不喜欢", "风格", "口吻", "语气",
            "habit", "prefer", "style",
        ),
        "session_continuation": ("继续", "刚才", "上文", "这个会话", "session", "context"),
        "knowledge_qa": ("解释", "是什么", "原理", "知识", "learn", "concept", "文档"),
        "association_brainstorm": ("联想", "相关", "拓展", "brainstorm", "idea", "启发"),
    }
    _SCENARIO_FRAMEWORK_PRIORITY: Dict[str, List[str]] = {
        "preference_alignment": ["mem0", "llamaindex_memory", "cognee"],
        "session_continuation": ["mem0", "llamaindex_memory", "cognee"],
        "knowledge_qa": ["llamaindex_memory", "cognee", "mem0"],
        "association_brainstorm": ["cognee", "llamaindex_memory", "mem0"],
        "general": ["mem0", "llamaindex_memory", "cognee"],
    }

    def __init__(
        self,
        *,
        enable_mem0: bool = True,
        enable_llamaindex_memory: bool = True,
        enable_cognee: bool = True,
        mem0_api_key: str = "",
        mem0_llm_api_key: str = "",
        mem0_llm_base_url: str = "",
        mem0_llm_model: str = "",
        mem0_embedder_provider: str = "fastembed",
        mem0_embedder_model: str = "BAAI/bge-small-en-v1.5",
        mem0_vector_store_provider: str = "faiss",
        mem0_vector_store_path: str = "",
        llamaindex_token_limit: int = 30000,
        llamaindex_cloud_mode: bool = False,
        llamaindex_api_key: str = "",
        cognee_cloud_mode: bool = False,
        cognee_api_key: str = "",
        cognee_base_url: str = "",
        cognee_dataset_name: str = "echomem",
        cognee_node_set: str = "",
        cognee_search_type: str = "GRAPH_COMPLETION",
        analysis_provider: str = "mimo",
        analysis_model: str = "mimo-v2.5-pro",
        analysis_api_key: str = "",
        analysis_base_url: str = "https://token-plan-cn.xiaomimimo.com/v1",
        analysis_timeout: float = 20.0,
        analysis_use_api_key_header: bool = False,
    ) -> None:
        self.mem0 = Mem0Adapter(
            mem0_api_key=mem0_api_key,
            llm_api_key=mem0_llm_api_key,
            llm_base_url=mem0_llm_base_url,
            llm_model=mem0_llm_model,
            embedder_provider=mem0_embedder_provider,
            embedder_model=mem0_embedder_model,
            vector_store_provider=mem0_vector_store_provider,
            vector_store_path=mem0_vector_store_path,
        ) if enable_mem0 else None

        # LlamaIndex: local Memory buffer (always), plus optional LlamaCloud
        self.llamaindex = LlamaIndexMemoryAdapter(
            token_limit=llamaindex_token_limit,
        ) if enable_llamaindex_memory else None
        self.llama_cloud = LlamaCloudAdapter(api_key=llamaindex_api_key) if llamaindex_cloud_mode else None

        # Cognee: local + optional cloud
        cognee_cloud = CogneeCloudAdapter(
            api_key=cognee_api_key,
            base_url=cognee_base_url,
            dataset_name=cognee_dataset_name,
            node_set=cognee_node_set,
            search_type=cognee_search_type,
        ) if cognee_cloud_mode else None
        self.cognee = CogneeAdapter(
            cloud_adapter=cognee_cloud,
            enable_local=not (cognee_cloud_mode and cognee_cloud is not None and cognee_cloud.available),
        ) if enable_cognee else None
        self.knowledge_graph = UserKnowledgeGraph()
        self.mimo_analyzer = MimoKnowledgeAnalyzer(
            provider=analysis_provider,
            model=analysis_model,
            api_key=analysis_api_key,
            base_url=analysis_base_url,
            timeout=analysis_timeout,
            use_api_key_header=analysis_use_api_key_header,
        )

    @classmethod
    def _detect_scenario(cls, query: str) -> str:
        normalized = query.lower().strip()
        for scenario, patterns in cls._SCENARIO_PATTERNS.items():
            if any(p in normalized for p in patterns):
                return scenario
        return "general"

    @staticmethod
    def _collect_framework_expansion(framework: str, details: Dict[str, Any]) -> List[str]:
        if framework == "mem0":
            return _dedupe_signals(details.get("facts", []), limit=2)
        if framework == "llamaindex_memory":
            return _dedupe_signals(details.get("doc_hits", []), limit=2)
        if framework == "cognee":
            return _dedupe_signals(details.get("related_concepts", []), limit=3)
        return []

    @staticmethod
    def _build_contribution(
        framework: str,
        role: str,
        details: Dict[str, Any],
        expansion: List[str],
    ) -> Dict[str, Any]:
        return {
            "framework": framework,
            "role": role,
            "available": bool(details.get("available")),
            "signal_source": str(details.get("signal_source", "")),
            "signal_count": len(expansion),
            "signals": expansion[:3],
            "value_summary": str(details.get("value_summary", "")),
            "used_in_query_expansion": bool(expansion),
            "signal_quality": "valuable" if expansion else "empty",
            "cloud_configured": bool(details.get("cloud_configured")),
            "cloud_available": bool(details.get("cloud_available")),
            "cloud_api_used": bool(details.get("cloud_api_used") or details.get("cloud_search_used")),
            "cloud_api_call_count": int(details.get("cloud_api_call_count") or 0),
        }

    @staticmethod
    def _filter_rows_for_user(rows: List[Dict[str, Any]], user_id: str) -> List[Dict[str, Any]]:
        if not user_id:
            return []
        uid = user_id.strip()
        if not uid:
            return []
        tagged = [r for r in rows if str(r.get("user_id", "")).strip() == uid]
        return tagged

    def _augment_rows_with_llamacloud(
        self,
        *,
        query: str,
        rows: List[Dict[str, Any]],
        user_id: str,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Prefer LlamaCloud parsing when configured, then fall back to raw rows."""
        details: Dict[str, Any] = {
            "available": bool(self.llama_cloud is not None and self.llama_cloud.available),
            "cloud_api_used": False,
            "cloud_configured": bool(self.llama_cloud is not None and getattr(self.llama_cloud, "cloud_configured", True)),
            "cloud_api_call_count": getattr(self.llama_cloud, "api_call_count", 0) if self.llama_cloud else 0,
            "cloud_init_error": getattr(self.llama_cloud, "init_error", "") if self.llama_cloud else "",
            "signal_source": "llamacloud_unavailable",
        }
        if self.llama_cloud is None:
            return rows, details
        details["signal_source"] = "llamacloud_not_configured"
        if not self.llama_cloud.available:
            details["cloud_init_error"] = self.llama_cloud.init_error
            return rows, details

        docs = [_memory_content(row) for row in rows if _memory_content(row)]
        selected = _combined_top_matches(query, docs, top_k=3) or docs[:3]
        parse_input = "\n\n".join(selected).strip()
        if not parse_input:
            details["signal_source"] = "llamacloud_no_input"
            return rows, details

        parsed = self.llama_cloud.parse_text(parse_input, filename="echomem-memory-context.txt")
        if not parsed:
            details["signal_source"] = "llamacloud_parse_failed"
            details["cloud_api_call_count"] = getattr(self.llama_cloud, "api_call_count", 1)
            return rows, details

        parsed_row = {
            "user_id": user_id,
            "content": parsed,
            "type": "llamacloud_parsed_memory",
            "source": "llamacloud",
        }
        details.update(
            {
                "cloud_api_used": True,
                "cloud_api_call_count": getattr(self.llama_cloud, "api_call_count", 1),
                "signal_source": "llamacloud_parse",
                "parsed_preview": _humanize_signal(parsed, limit=220),
            }
        )
        return [parsed_row] + rows, details

    def collect_hints(
        self,
        *,
        user_id: str,
        query: str,
        stm_text: str,
        ltm_rows: List[Dict[str, Any]],
        enable_mimo_analysis: bool = True,
    ) -> Dict[str, Any]:
        hints: Dict[str, Any] = {}
        framework_expansions: Dict[str, List[str]] = {}
        session_id = f"session-{user_id or 'anonymous'}"
        scoped_rows = self._filter_rows_for_user(ltm_rows, user_id)
        llama_rows, llamacloud_details = self._augment_rows_with_llamacloud(
            query=query,
            rows=scoped_rows,
            user_id=user_id,
        )
        hints["llamacloud_parse"] = llamacloud_details
        scenario = self._detect_scenario(query)

        if self.mem0 is not None:
            mem0_hint = self.mem0.get_user_facts(user_id=user_id, ltm_rows=scoped_rows, query=query)
            hints["mem0"] = mem0_hint.details
            hints.setdefault("framework_status", {})["mem0"] = {
                "available": mem0_hint.available,
                "signal_source": mem0_hint.details.get("signal_source", ""),
                "cloud_configured": mem0_hint.details.get("cloud_configured", False),
                "cloud_available": mem0_hint.details.get("cloud_available", False),
                "cloud_api_used": mem0_hint.details.get("cloud_api_used", False),
                "cloud_api_call_count": mem0_hint.details.get("cloud_api_call_count", 0),
            }
            framework_expansions["mem0"] = self._collect_framework_expansion("mem0", mem0_hint.details)
        if self.llamaindex is not None:
            llama_hint = self.llamaindex.retrieve(query=query, ltm_rows=llama_rows)
            llama_hint.details.update(
                {
                    "cloud_configured": llamacloud_details.get("cloud_configured", False),
                    "cloud_available": llamacloud_details.get("available", False),
                    "cloud_api_used": llamacloud_details.get("cloud_api_used", False),
                    "cloud_api_call_count": llamacloud_details.get("cloud_api_call_count", 0),
                }
            )
            hints["llamaindex_memory"] = llama_hint.details
            hints.setdefault("framework_status", {})["llamaindex_memory"] = {
                "available": llama_hint.available,
                "signal_source": llama_hint.details.get("signal_source", ""),
                "cloud_configured": llamacloud_details.get("cloud_configured", False),
                "cloud_available": llamacloud_details.get("available", False),
                "cloud_api_used": llamacloud_details.get("cloud_api_used", False),
                "cloud_api_call_count": llamacloud_details.get("cloud_api_call_count", 0),
            }
            framework_expansions["llamaindex_memory"] = self._collect_framework_expansion(
                "llamaindex_memory", llama_hint.details
            )
        if self.cognee is not None:
            cognee_hint = self.cognee.related_concepts(query=query, ltm_rows=scoped_rows)
            hints["cognee"] = cognee_hint.details
            hints.setdefault("framework_status", {})["cognee"] = {
                "available": cognee_hint.available,
                "signal_source": cognee_hint.details.get("signal_source", ""),
                "cloud_configured": cognee_hint.details.get("cloud_configured", False),
                "cloud_available": cognee_hint.details.get("cloud_available", False),
                "cloud_api_used": bool(cognee_hint.details.get("cloud_api_call_count", 0)),
                "cloud_api_call_count": cognee_hint.details.get("cloud_api_call_count", 0),
            }
            framework_expansions["cognee"] = self._collect_framework_expansion("cognee", cognee_hint.details)

        knowledge_texts = [str(r.get("content", "")) for r in scoped_rows if str(r.get("content", "")).strip()]
        graph = self.knowledge_graph.build(knowledge_texts)
        hints["user_knowledge_system"] = {
            "user_id": user_id,
            "memory_scope_size": len(scoped_rows),
            "node_count": len(graph["nodes"]),
            "edge_count": len(graph["edges"]),
            "graph": graph,
        }
        hints["mimo_analysis"] = self.mimo_analyzer.analyze(query=query, graph=graph, enabled=enable_mimo_analysis)

        priorities = self._SCENARIO_FRAMEWORK_PRIORITY.get(scenario, self._SCENARIO_FRAMEWORK_PRIORITY["general"])
        routed: List[str] = []
        for framework in priorities:
            routed.extend(framework_expansions.get(framework, []))
        merged: List[str] = []
        seen: set[str] = set()
        for item in routed:
            token = item.strip()
            if not token or token in seen:
                continue
            seen.add(token)
            merged.append(item)

        hints["scenario_routing"] = {
            "scenario": scenario,
            "framework_priority": priorities,
            "framework_expansion": framework_expansions,
        }
        hints["framework_contributions"] = [
            self._build_contribution(
                "mem0",
                "用户偏好/画像事实",
                hints.get("mem0", {}) if isinstance(hints.get("mem0"), dict) else {},
                framework_expansions.get("mem0", []),
            ),
            self._build_contribution(
                "llamaindex_memory",
                "文档/会话知识命中",
                hints.get("llamaindex_memory", {}) if isinstance(hints.get("llamaindex_memory"), dict) else {},
                framework_expansions.get("llamaindex_memory", []),
            ),
            self._build_contribution(
                "cognee",
                "知识图谱关联概念",
                hints.get("cognee", {}) if isinstance(hints.get("cognee"), dict) else {},
                framework_expansions.get("cognee", []),
            ),
        ]
        hints["query_expansion"] = merged
        return hints

    def store_interaction(self, *, user_id: str, user_input: str, assistant_output: str) -> Dict[str, Any]:
        """Write the latest turn into all available memory frameworks."""
        uid = (user_id or "anonymous").strip() or "anonymous"
        turn_text = f"user: {user_input}\nassistant: {assistant_output}".strip()
        writes: Dict[str, Any] = {}

        if self.mem0 is not None:
            before_calls = getattr(self.mem0, "api_call_count", 0)
            stored = self.mem0.store(
                turn_text,
                uid,
                metadata={"source": "echomem_chat", "framework_role": "profile_facts"},
            )
            writes["mem0"] = {
                "role": "长期偏好/事实记忆",
                "stored": stored,
                "cloud_api_used": getattr(self.mem0, "api_call_count", 0) > before_calls,
                "cloud_available": getattr(self.mem0, "_is_cloud", False),
            }
        if self.llamaindex is not None:
            writes["llamaindex_memory"] = {
                "role": "会话缓冲/文档式上下文",
                "stored": self.llamaindex.add_conversation(user_input, assistant_output),
            }
        if self.cognee is not None:
            cloud = getattr(self.cognee, "_cloud", None)
            before_calls = getattr(cloud, "api_call_count", 0) if cloud else 0
            stored = bool(self.cognee._run_async_blocking(self.cognee.add_knowledge([turn_text])))
            writes["cognee"] = {
                "role": "图谱实体/关系构建",
                "stored": stored,
                "cloud_api_used": (getattr(cloud, "api_call_count", 0) if cloud else 0) > before_calls,
                "cloud_available": bool(cloud is not None and getattr(cloud, "available", False)),
            }
        return writes

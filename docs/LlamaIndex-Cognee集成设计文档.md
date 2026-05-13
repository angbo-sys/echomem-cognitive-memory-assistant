# LlamaIndex & Cognee 集成设计文档

> 创建日期：2026-05-10
> 目标：将 LlamaIndex 和 Cognee 从"装饰性信号"升级为"真实后端集成"
> 当前版本：LlamaIndex 0.14.21 / Cognee 1.0.8

---

## 一、框架概览

### 1.1 LlamaIndex Cloud（文档解析 + 向量索引）

**定位**：企业级文档处理平台，支持 Parse/Extract/Classify/Split/Sheets/Index 六大产品。

**云端 API**：
- Dashboard: https://cloud.llamaindex.ai
- SDK: `pip install llama-cloud>=2.1`
- API Key: `LLAMA_CLOUD_API_KEY=llx-...`

**核心 API**：
```python
from llama_cloud import LlamaCloud

client = LlamaCloud()  # 使用 LLAMA_CLOUD_API_KEY 环境变量

# 1. 文档解析（Parse）
file = client.files.create(file="document.pdf", purpose="parse")
result = client.parsing.parse(file_id=file.id, tier="agentic", version="latest", expand=["markdown"])
print(result.markdown.pages[0].markdown)

# 2. 结构化数据提取（Extract）
from pydantic import BaseModel, Field

class Resume(BaseModel):
    name: str = Field(description="Full name")
    skills: list[str] = Field(description="Technical skills")

file = client.files.create(file="resume.pdf", purpose="extract")
job = client.extract.create(document_input_value=file.id, config={"extract_options": {"data_schema": Resume.model_json_schema()}})
print(job.extract_result)

# 3. 向量索引（Index）- 用于 RAG
# 创建托管向量搜索管道
```

**关键特性**：
- 130+ 格式文档解析（PDF/扫描/图片）
- Agentic OCR 技术
- 结构化数据提取（自定义 Schema）
- 托管向量搜索管道（RAG）

---

### 1.2 LlamaIndex Memory（本地会话记忆）

**定位**：会话级短期记忆缓冲，支持 token 限制的 FIFO 队列 + 可扩展 memory blocks。

**核心 API**：
```python
from llama_index.core.memory import Memory
from llama_index.core.llms import ChatMessage

# 初始化
memory = Memory(token_limit=30000)

# 写入消息
memory.put(ChatMessage(role="user", content="用户消息"))
memory.put(ChatMessage(role="assistant", content="助手回复"))

# 批量写入
memory.put_messages([msg1, msg2, msg3])

# 检索（带 memory blocks）
messages = memory.get(input="查询文本")

# 获取所有历史
all_messages = memory.get_all()

# 重置
memory.reset()
```

**关键特性**：
- Token 限制自动管理（FIFO 队列）
- 支持自定义 memory blocks（如摘要、检索增强）
- 同步/异步 API 均支持
- 内置 SQLAlchemy 存储（可持久化）

---

### 1.3 Cognee Cloud（知识图谱 API）

**定位**：云端知识图谱服务，支持语义理解、概念关联、多跳推理。

**云端 API**：
- Endpoint: `https://api.aws.cognee.ai`
- 文档: https://api.aws.cognee.ai/docs
- 认证: `X-Api-Key` Header
- 试用: 14 天免费试用

**核心 API**：
```python
import httpx

API_BASE = "https://api.aws.cognee.ai"
API_KEY = "your-api-key"

headers = {"X-Api-Key": API_KEY}

# 1. 检查订阅状态
response = httpx.get(f"{API_BASE}/api/v1/subscriptions/status", headers=headers)
print(response.json())  # {"status": "trial"} | {"status": "active"}

# 2. 获取用户 ID
response = httpx.get(f"{API_BASE}/api/v1/api-keys/my-user-id", headers=headers)
user_id = response.json()

# 3. 创建租户
response = httpx.post(f"{API_BASE}/api/v1/tenants?tenant_name=my-project", headers=headers)

# 4. 添加用户到租户
response = httpx.post(f"{API_BASE}/api/v1/tenants/users?tenant_id={tenant_id}&user_id={user_id}", headers=headers)
```

**关键特性**：
- 多租户架构
- API Key 认证
- 订阅管理（试用/付费）
- 用户权限控制

---

### 1.4 Cognee Local（本地知识图谱）

**定位**：本地知识图谱库，支持语义理解、概念关联。

**核心 API（V1 Legacy）**：
```python
import cognee

# 添加知识
await cognee.add("文本内容")

# 处理知识（构建图谱）
await cognee.cognify()

# 检索
results = await cognee.search("查询文本", query_type=SearchType.GRAPH_COMPLETION)
```

**核心 API（V1.0+ New）**：
```python
import cognee

# 存储记忆
result = await cognee.remember("文本内容")

# 检索记忆
results = await cognee.recall("查询文本")

# 遗忘
await cognee.forget("记忆ID")

# 改进
await cognee.improve("查询文本")
```

**关键特性**：
- 本地存储（SQLite + LanceDB）
- 支持异步 API
- 内置知识图谱构建
- 多用户访问控制
- 会话记忆支持

---

## 二、集成架构设计

### 2.1 整体架构

```
用户输入
    ↓
Orchestrator
    ↓
┌─────────────────────────────────────────────────────────┐
│                   OpenSourceMemoryHub                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ Mem0Adapter │  │ LlamaIndex  │  │ Cognee      │    │
│  │ (已完成)    │  │ Adapter     │  │ Adapter     │    │
│  │ Cloud/Local │  │ Cloud/Local │  │ Cloud/Local │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────┘
    ↓
query_expansion → 注入 Prompt
```

### 2.2 部署模式选择

| 框架 | 云端模式 | 本地模式 | 推荐场景 |
|------|---------|---------|---------|
| LlamaIndex | LlamaCloud API | Memory Buffer | 文档解析用云端，会话记忆用本地 |
| Cognee | Cognee Cloud API | SQLite + LanceDB | 生产环境用云端，开发测试用本地 |

### 2.3 数据流

**LlamaIndex Cloud（文档解析）**：
```
文档 → LlamaCloud.parse() → 结构化文本 → 存储到 LTM
```

**LlamaIndex Memory（会话记忆）**：
```
对话消息 → put() → Memory Buffer → get(query) → 相关消息 → query_expansion
```

**Cognee Cloud**：
```
LTM 记忆 → POST /api/v1/... → 知识图谱 → GET /api/v1/... → 相关概念 → query_expansion
```

**Cognee Local**：
```
LTM 记忆 → add() → cognify() → 知识图谱 → search(query) → 相关概念 → query_expansion
```

---

## 三、LlamaIndex 集成方案

### 3.1 云端模式（LlamaCloud）

**适用场景**：文档解析、结构化数据提取、托管向量索引

```python
class LlamaCloudAdapter:
    """LlamaCloud: 云端文档解析和向量索引"""

    def __init__(self, api_key: str = "") -> None:
        self.available = False
        self._client: Any = None
        try:
            from llama_cloud import LlamaCloud
            self._client = LlamaCloud(api_key=api_key) if api_key else LlamaCloud()
            self.available = True
        except Exception:
            pass

    def parse_document(self, file_path: str) -> Optional[str]:
        """解析文档为 Markdown"""
        if not self.available or self._client is None:
            return None
        try:
            file = self._client.files.create(file=file_path, purpose="parse")
            result = self._client.parsing.parse(
                file_id=file.id,
                tier="agentic",
                version="latest",
                expand=["markdown"]
            )
            return result.markdown.pages[0].markdown if result.markdown else None
        except Exception:
            return None

    def extract_structured(self, file_path: str, schema: dict) -> Optional[dict]:
        """从文档提取结构化数据"""
        if not self.available or self._client is None:
            return None
        try:
            file = self._client.files.create(file=file_path, purpose="extract")
            job = self._client.extract.create(
                document_input_value=file.id,
                config={"extract_options": {"data_schema": schema, "tier": "agentic"}}
            )
            return job.extract_result
        except Exception:
            return None
```

### 3.2 本地模式（Memory Buffer）

**适用场景**：会话级短期记忆

```python
class LlamaIndexMemoryAdapter:
    """LlamaIndex Memory: 真实会话记忆缓冲"""

    def __init__(self, token_limit: int = 30000) -> None:
        self.available = False
        self._memory: Any = None
        self._chat_msg_cls: Any = None
        try:
            from llama_index.core.memory import Memory
            from llama_index.core.llms import ChatMessage
            self._memory = Memory(token_limit=token_limit)
            self._chat_msg_cls = ChatMessage
            self.available = True
        except Exception:
            pass

    def add_conversation(self, user_input: str, assistant_output: str) -> bool:
        """添加一轮对话到记忆缓冲"""
        if not self.available or self._memory is None:
            return False
        try:
            self._memory.put(self._chat_msg_cls(role="user", content=user_input))
            self._memory.put(self._chat_msg_cls(role="assistant", content=assistant_output))
            return True
        except Exception:
            return False

    def retrieve(self, query: str, ltm_rows: List[Dict[str, Any]]) -> FrameworkHint:
        """检索相关记忆"""
        docs = [str(r.get("content", "")) for r in ltm_rows if str(r.get("content", "")).strip()]
        memory_items: List[str] = []

        # 尝试真实 LlamaIndex Memory 检索
        if self._memory is not None:
            try:
                # 添加 LTM 文档到 memory
                self._add_documents(docs[:24])
                # 检索相关消息
                messages = self._memory.get(input=query)
                memory_items = [str(msg.content) for msg in messages if str(msg.content).strip()]
            except Exception:
                memory_items = []

        if memory_items:
            doc_hits = _combined_top_matches(query, memory_items, top_k=3)
            signal_source = "llamaindex_memory_buffer"
        else:
            # 回退：BM25 匹配
            doc_hits = _top_bm25_matches(query, docs, top_k=3)
            signal_source = "llamaindex_enhanced_fallback"

        return FrameworkHint(
            "llamaindex_memory",
            self.available or bool(doc_hits),
            {
                "available": self.available,
                "signal_source": signal_source,
                "doc_hits": doc_hits,
                "memory_items": memory_items[:5],
            }
        )

    def _add_documents(self, documents: List[str]) -> int:
        """批量添加文档到 memory"""
        if self._memory is None or self._chat_msg_cls is None:
            return 0
        count = 0
        for doc in documents:
            try:
                self._memory.put(self._chat_msg_cls(role="user", content=doc))
                count += 1
            except Exception:
                break
        return count
```

### 3.3 配置参数

```toml
# config/settings.toml
[memory_frameworks]
enable_llamaindex_memory = true
llamaindex_token_limit = 30000
llamaindex_cloud_mode = false  # true=云端, false=本地

# 环境变量
# LLAMA_CLOUD_API_KEY=llx-...  # 云端 API Key
```

### 3.4 测试用例

```python
def test_llamaindex_memory_add_and_retrieve():
    """验证 LlamaIndex Memory 真实写入和检索"""
    adapter = LlamaIndexMemoryAdapter(token_limit=10000)
    assert adapter.available

    # 写入对话
    adapter.add_conversation("我在学概率论", "概率论是研究随机现象的学科")

    # 检索
    rows = [{"content": "用户在学概率论", "type": "knowledge"}]
    hint = adapter.retrieve("概率论是什么", rows)

    assert hint.details["available"]
    assert len(hint.details["doc_hits"]) > 0
```

---

## 四、Cognee 集成方案

### 4.1 云端模式（Cognee Cloud API）

**适用场景**：生产环境、多用户、需要持久化知识图谱

```python
class CogneeCloudAdapter:
    """Cognee Cloud: 云端知识图谱服务"""

    def __init__(self, api_key: str = "", base_url: str = "https://api.aws.cognee.ai") -> None:
        self.available = False
        self._api_key = api_key
        self._base_url = base_url
        self._headers = {"X-Api-Key": api_key} if api_key else {}
        if api_key:
            self.available = True

    def _request(self, method: str, path: str, **kwargs) -> Optional[dict]:
        """发送 API 请求"""
        import httpx
        try:
            url = f"{self._base_url}{path}"
            response = httpx.request(method, url, headers=self._headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

    def check_subscription(self) -> str:
        """检查订阅状态"""
        result = self._request("GET", "/api/v1/subscriptions/status")
        return result.get("status", "none") if result else "none"

    def create_tenant(self, name: str) -> Optional[str]:
        """创建租户"""
        result = self._request("POST", f"/api/v1/tenants?tenant_name={name}")
        return result.get("tenant_id") if result else None

    def add_knowledge(self, texts: List[str]) -> bool:
        """添加知识到云端图谱"""
        # TODO: 实现实际的 API 调用
        return False

    def search_graph(self, query: str, limit: int = 5) -> List[str]:
        """查询云端知识图谱"""
        # TODO: 实现实际的 API 调用
        return []
```

### 4.2 本地模式（SQLite + LanceDB）

**适用场景**：开发测试、离线环境、单用户

```python
class CogneeAdapter:
    """Cognee Local: 本地知识图谱"""

    def __init__(self) -> None:
        self.available = False
        self._cognee: Any = None
        try:
            import cognee
            self._cognee = cognee
            self.available = True
        except Exception:
            pass

    async def add_knowledge(self, texts: List[str]) -> bool:
        """添加知识到本地图谱"""
        if self._cognee is None:
            return False
        try:
            for text in texts[:10]:
                await self._cognee.add(text)
            await self._cognee.cognify()
            return True
        except Exception:
            return False

    async def search_graph(self, query: str, limit: int = 5) -> List[str]:
        """查询本地知识图谱"""
        if self._cognee is None:
            return []
        try:
            results = await self._cognee.search(query)
            return [str(r) for r in results if r][:limit]
        except Exception:
            return []

    def related_concepts(self, query: str, ltm_rows: List[Dict[str, Any]]) -> FrameworkHint:
        """获取相关概念"""
        query_terms = set(_tokenize_concepts(query))
        relation_counts: Dict[str, int] = {}
        concept_edges: List[Dict[str, Any]] = []

        # 增强概念提取
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
                for token in tokens[:8]:
                    if token != anchor:
                        concept_edges.append({"source": anchor, "relation": "co_occurs", "target": token})
                    if len(concept_edges) >= 8:
                        break

        related = sorted(relation_counts.items(), key=lambda x: x[1], reverse=True)[:6]

        return FrameworkHint(
            "cognee",
            self.available or bool(related),
            {
                "available": self.available,
                "signal_source": "cognee_local_concept_graph",
                "related_concepts": [k for k, _ in related],
                "concept_edges": concept_edges,
            }
        )
```

### 4.3 配置参数

```toml
# config/settings.toml
[memory_frameworks]
enable_cognee = true
cognee_cloud_mode = false  # true=云端, false=本地

# 环境变量
# COGNEE_API_KEY=your-api-key  # 云端 API Key
# COGNEE_DISABLE_TELEMETRY=true
# CACHING=false  # 禁用会话缓存
# ENABLE_BACKEND_ACCESS_CONTROL=false  # 禁用多用户控制
```

### 4.4 测试用例

```python
def test_cognee_local_add_and_search():
    """验证 Cognee 本地知识图谱构建"""
    adapter = CogneeAdapter()
    assert adapter.available

    # 添加知识
    texts = ["概率论研究随机现象", "贝叶斯公式用于条件概率"]
    result = asyncio.get_event_loop().run_until_complete(
        adapter.add_knowledge(texts)
    )
    assert result

    # 搜索
    results = asyncio.get_event_loop().run_until_complete(
        adapter.search_graph("概率论相关概念")
    )
    assert len(results) > 0

def test_cognee_cloud_subscription():
    """验证 Cognee Cloud 订阅状态"""
    import os
    api_key = os.getenv("COGNEE_API_KEY", "")
    if not api_key:
        return  # 跳过无 API Key 的测试

    adapter = CogneeCloudAdapter(api_key=api_key)
    assert adapter.available

    status = adapter.check_subscription()
    assert status in ("trial", "active")
```

---

## 五、配置变更

### 5.1 config/settings.toml

```toml
[memory_frameworks]
enable_mem0 = true
enable_llamaindex_memory = true
enable_cognee = true

# LlamaIndex 配置
llamaindex_token_limit = 30000
llamaindex_cloud_mode = false  # true=云端, false=本地

# Cognee 配置
cognee_cloud_mode = false  # true=云端, false=本地
```

### 5.2 .env 文件

```bash
# LlamaIndex Cloud（可选）
LLAMA_CLOUD_API_KEY=llx-...

# Cognee Cloud（可选）
COGNEE_API_KEY=your-api-key
```

### 5.3 config/loader.py

```python
@dataclass(frozen=True)
class MemoryFrameworkConfig:
    enable_mem0: bool = True
    enable_llamaindex_memory: bool = True
    enable_cognee: bool = True
    llamaindex_token_limit: int = 30000
    llamaindex_cloud_mode: bool = False
    cognee_cloud_mode: bool = False
```

### 5.4 config/factory.py

```python
def build_memory_search_from_config(cfg: AppConfig) -> MemorySearch:
    mem0_api_key = os.getenv("MEM0_API_KEY", "")
    llamaindex_api_key = os.getenv("LLAMA_CLOUD_API_KEY", "")
    cognee_api_key = os.getenv("COGNEE_API_KEY", "")

    memory_hub = OpenSourceMemoryHub(
        enable_mem0=cfg.memory_frameworks.enable_mem0,
        enable_llamaindex_memory=cfg.memory_frameworks.enable_llamaindex_memory,
        enable_cognee=cfg.memory_frameworks.enable_cognee,
        llamaindex_token_limit=cfg.memory_frameworks.llamaindex_token_limit,
        llamaindex_cloud_mode=cfg.memory_frameworks.llamaindex_cloud_mode,
        llamaindex_api_key=llamaindex_api_key,
        cognee_cloud_mode=cfg.memory_frameworks.cognee_cloud_mode,
        cognee_api_key=cognee_api_key,
        # ... 其他参数
    )
    return MemorySearch(...)
```

---

## 六、测试计划

### 6.1 单元测试

| 测试文件 | 测试内容 |
|---------|---------|
| `tests/test_llamaindex_memory.py` | Memory 初始化、add_conversation、retrieve |
| `tests/test_llamaindex_cloud.py` | LlamaCloud 文档解析、结构化提取 |
| `tests/test_cognee.py` | add_knowledge、search_graph、related_concepts |
| `tests/test_cognee_cloud.py` | Cloud API 订阅检查、知识图谱操作 |
| `tests/test_open_source_memory.py` | 更新现有测试，移除 zep 相关 |

### 6.2 集成测试

```python
def test_full_pipeline():
    """验证完整链路：写入 → 检索 → query_expansion"""
    hub = OpenSourceMemoryHub(
        enable_mem0=True,
        enable_llamaindex_memory=True,
        enable_cognee=True,
    )

    # 写入记忆
    hub.mem0.store("用户偏好简洁回答", user_id="test")

    # 收集 hints
    hints = hub.collect_hints(
        user_id="test",
        query="按我的偏好回答",
        stm_text="",
        ltm_rows=[{"content": "用户偏好简洁回答", "type": "preference"}],
    )

    # 验证
    assert len(hints.get("query_expansion", [])) > 0
    assert "llamaindex_memory" in hints.get("framework_status", {})
    assert "cognee" in hints.get("framework_status", {})
```

### 6.3 E2E 验证

```bash
# 运行测试
conda run -n echomem-test python -m unittest discover tests -v

# 运行工作流
conda run -n echomem-test python scripts/workflow.py

# 验证 LlamaCloud API 连接
conda run -n echomem-test python -c "
import os
from llama_cloud import LlamaCloud
client = LlamaCloud(api_key=os.getenv('LLAMA_CLOUD_API_KEY'))
print('LlamaCloud connected:', client is not None)
"

# 验证框架信号
conda run -n echomem-test python -c "
from memory import OpenSourceMemoryHub
hub = OpenSourceMemoryHub()
hints = hub.collect_hints(
    user_id='demo_user',
    query='概率论相关概念',
    stm_text='',
    ltm_rows=[{'content': '概率论知识', 'type': 'knowledge'}],
)
print('query_expansion:', hints.get('query_expansion'))
print('framework_status:', hints.get('framework_status'))
"
```

---

## 七、验收标准

| 指标 | 当前值 | 目标值 |
|------|--------|--------|
| `query_expansion_count` | 0 | ≥ 2 |
| LlamaIndex `available` | 仅检查包导入 | 检查实例化成功 |
| Cognee `available` | 仅检查包导入 | 检查实例化成功 |
| LlamaCloud API 连接 | 未测试 | 连接成功 |
| 真实后端调用次数 | 0 | 每次 collect_hints 至少 1 次 |
| 测试通过 | 69/69 | ≥ 74 |

---

## 八、实施顺序

| 阶段 | 任务 | 预计时间 |
|------|------|---------|
| Phase 1 | LlamaCloud 适配器实现 | 1 小时 |
| Phase 2 | LlamaIndex Memory 适配器重写 | 1 小时 |
| Phase 3 | Cognee Cloud 适配器实现 | 1 小时 |
| Phase 4 | Cognee Local 适配器增强 | 30 分钟 |
| Phase 5 | 配置更新 | 15 分钟 |
| Phase 6 | 单元测试 | 30 分钟 |
| Phase 7 | 集成测试 | 30 分钟 |
| Phase 8 | 文档更新 | 15 分钟 |

---

## 九、风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| LlamaIndex API 变更 | 使用 try/except 包裹，失败则 available=False |
| Cognee 需要外部服务 | 默认使用本地存储，不依赖外部服务 |
| API Key 泄漏 | 统一从 .env 读取，不硬编码 |
| 性能下降 | 异步调用 + 超时控制 + 缓存 |
| 接口变更 | 保持 FrameworkHint 返回结构不变 |

---

## 十、API Keys 状态

| 框架 | API Key | 状态 |
|------|---------|------|
| Mem0 | 通过 `MEM0_API_KEY` 配置 | ✅ 已配置 |
| LlamaCloud | 通过 `LLAMA_CLOUD_API_KEY` 配置 | ✅ 已配置 |
| Cognee Cloud | 通过 `COGNEE_API_KEY` 配置 | ✅ 已配置 |

**Cognee Cloud 配置**：
- Base URL：通过 `COGNEE_BASE_URL` 配置
- Tenant ID：本地运行可放在 `.env`，运行代码不直接依赖
- 环境变量：`COGNEE_API_KEY`, `COGNEE_BASE_URL`, `COGNEE_DATASET_NAME`

---

## 十一、后续增强

1. **LlamaIndex 增强**：
   - 接入 LlamaCloud 托管向量索引
   - 支持自定义 memory blocks（如摘要、检索增强）

2. **Cognee 增强**：
   - 接入外部图数据库（如 Neo4j）
   - 支持多用户访问控制

3. **整体增强**：
   - 实验框架 CI 自动基准测试
   - UI 展示框架信号质量

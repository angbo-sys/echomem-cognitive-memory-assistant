# AI 记忆框架本地部署完整指南

> 本文档聚焦主流 AI 记忆框架的 **本地部署方案**，用于 Agent 开发集成。所有方案均可在本地机器或私有服务器运行。

---

## 目录

1. [Mem0 - AI 专属记忆层](#1-mem0)
2. [LlamaIndex Memory - 文档+对话双记忆](#2-llamaindex-memory)
3. [Cognee - 开源知识图谱记忆](#3-cognee)
4. [框架对比与选型建议](#4-框架对比)

> **注意**: Zep (Graphiti) 已从 EchoMem 项目中移除，不再集成。

---

## 1. Mem0

**GitHub**: https://github.com/mem0ai/mem0  
**文档**: https://docs.mem0.ai  
**许可证**: Apache 2.0

### 核心特性

- 多级记忆：用户级、会话级、Agent 级
- 单次 LLM 调用即可提取记忆，低延迟
- 实体链接和多信号检索（语义+BM25+实体）
- 支持 Python、Node.js SDK

---

### 本地部署方式一：库模式（最快上手）

```bash
# 基础安装
pip install mem0ai

# 含 NLP 增强（BM25 关键词匹配 + 实体提取）
pip install mem0ai[nlp]
python -m spacy download en_core_web_sm

# Node.js 版本
npm install mem0ai
```

**配置本地 LLM（可选，避免调用 OpenAI）：**

```python
from mem0 import Memory

# 使用本地 Ollama
memory = Memory.from_config({
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "llama3.2",
            "ollama_base_url": "http://localhost:11434"
        }
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text",
            "ollama_base_url": "http://localhost:11434"
        }
    }
})
```

---

### 本地部署方式二：Docker 自托管服务器（推荐生产使用）

#### 前置要求

- Docker & Docker Compose
- 4GB+ 内存

#### 步骤 1：克隆仓库

```bash
git clone https://github.com/mem0ai/mem0.git
cd mem0/server
```

#### 步骤 2：配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# 禁用认证（本地开发）
AUTH_DISABLED=true

# 或设置管理员密钥
ADMIN_API_KEY=your-local-admin-key

# LLM 配置（使用本地模型或远程 API）
OPENAI_API_KEY=sk-xxx  # 可选，使用本地模型可不填
```

#### 步骤 3：一键启动

```bash
# 推荐：自动完成所有设置
make bootstrap

# 或手动启动
docker compose up -d
```

#### 步骤 4：验证服务

```bash
# 检查容器状态
docker compose ps

# 访问 API 文档
open http://localhost:8080/docs

# 或访问 Dashboard（如果包含）
open http://localhost:3000
```

#### Docker Compose 配置参考

```yaml
# docker-compose.yml
services:
  mem0:
    image: mem0/mem0-server:latest
    ports:
      - "8080:8080"
    environment:
      - AUTH_DISABLED=true
      - QDRANT_URL=http://qdrant:6333
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - qdrant

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  qdrant_data:
```

---

### 本地使用示例

```python
from mem0 import Memory

# 初始化（本地模式）
memory = Memory()

# 添加记忆
memory.add("用户喜欢深色模式和 Vim 快捷键", user_id="alice")
memory.add("上次讨论了项目部署方案", user_id="alice", agent_id="dev-assistant")

# 搜索记忆
results = memory.search(
    "Alice 的偏好是什么？",
    filters={"user_id": "alice"},
    top_k=5
)

# 带记忆的对话
def chat_with_memory(message: str, user_id: str = "default") -> str:
    # 检索相关记忆
    memories = memory.search(query=message, filters={"user_id": user_id}, top_k=3)
    memories_str = "\n".join(f"- {m['memory']}" for m in memories["results"])
    
    # 构建带记忆的系统提示
    system_prompt = f"""你是一个有记忆的 AI 助手。
    
用户记忆：
{memories_str}

基于以上记忆回答问题。"""
    
    # 调用 LLM...
    # assistant_response = ...
    
    # 保存新记忆
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
        {"role": "assistant", "content": assistant_response}
    ]
    memory.add(messages, user_id=user_id)
    
    return assistant_response

# CLI 使用
# mem0 init
# mem0 add "用户喜欢深色模式" --user-id alice
# mem0 search "Alice 喜欢什么？" --user-id alice
```

---

## 2. LlamaIndex Memory

**文档**: https://developers.llamaindex.ai  
**GitHub**: https://github.com/run-llama/llama_index  
**许可证**: MIT

### 核心特性

- 文档记忆 + 对话记忆双重支持
- 与 LlamaIndex 知识索引深度集成
- 支持多种记忆类型：Buffer、Summary、Vector
- 100% 本地运行，无外部服务依赖

---

### 本地部署方式

#### 前置要求

- Python 3.10+
- LLM（OpenAI API 或本地模型）

#### 步骤 1：安装

```bash
# 创建虚拟环境
python -m venv llama-memory-env
source llama-memory-env/bin/activate

# 核心安装
pip install llama-index-core

# 根据需要安装 LLM 提供商
pip install llama-index-llms-openai      # OpenAI
pip install llama-index-llms-ollama      # 本地 Ollama
pip install llama-index-llms-anthropic   # Claude

# 向量存储（可选，用于 VectorMemory）
pip install llama-index-vector-stores-qdrant   # Qdrant
pip install llama-index-vector-stores-chroma   # ChromaDB（更轻量）
```

#### 步骤 2：配置本地 LLM

```python
# 使用 Ollama 本地模型
from llama_index.llms.ollama import Ollama

llm = Ollama(model="llama3.2", base_url="http://localhost:11434")

# 或使用 OpenAI
from llama_index.llms.openai import OpenAI
llm = OpenAI(model="gpt-4")
```

---

### 记忆类型详解

| 类型 | 用途 | 特点 | 适用场景 |
|------|------|------|----------|
| **ChatMemoryBuffer** | 对话缓冲 | 保留最近 N 条消息 | 简单对话 |
| **ChatSummaryMemoryBuffer** | 长对话摘要 | 自动压缩历史 | 长期对话 |
| **VectorMemory** | 语义搜索 | 向量检索相关上下文 | 知识问答 |
| **CompositeMemory** | 组合模式 | 同时使用多种策略 | 复杂 Agent |

---

### 完整使用示例

#### 示例 1：基础对话记忆

```python
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core import Settings
from llama_index.llms.ollama import Ollama

# 配置本地 LLM
Settings.llm = Ollama(model="llama3.2", base_url="http://localhost:11434")

# 创建对话记忆（保留最近 4096 token）
memory = ChatMemoryBuffer.from_defaults(token_limit=4096)

# 模拟对话
from llama_index.core.chat_engine import SimpleChatEngine

chat_engine = SimpleChatEngine.from_defaults(memory=memory)

# 对话 1
response = chat_engine.chat("我是一名 Python 开发者，正在学习机器学习")
print(response)

# 对话 2（自动关联上下文）
response = chat_engine.chat("基于我的背景，推荐一些学习资源")
print(response)

# 对话 3（继续关联）
response = chat_engine.chat("刚才推荐的那些资源，哪个最适合初学者？")
print(response)
```

#### 示例 2：文档 + 对话组合记忆

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.memory import ChatMemoryBuffer, VectorMemory, CompositeMemory
from llama_index.core import Settings
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

# 配置
Settings.llm = Ollama(model="llama3.2", base_url="http://localhost:11434")

# 1. 加载文档构建知识索引
documents = SimpleDirectoryReader("data").load_data()

# 使用 ChromaDB 作为本地向量存储
chroma_client = chromadb.PersistentClient(path="./chroma_db")
chroma_collection = chroma_client.get_or_create_collection("docs")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

index = VectorStoreIndex.from_documents(
    documents,
    vector_store=vector_store
)

# 2. 创建组合记忆
chat_memory = ChatMemoryBuffer.from_defaults(token_limit=2000)
vector_memory = VectorMemory.from_defaults(
    vector_store=vector_store,
    similarity_top_k=3
)

composite_memory = CompositeMemory.from_defaults(
    memory_buffers=[chat_memory, vector_memory]
)

# 3. 创建 Agent
from llama_index.core.agent import ReActAgent

agent = ReActAgent.from_tools(
    tools=[index.as_query_engine()],
    llm=Settings.llm,
    memory=composite_memory,
    verbose=True
)

# 4. 对话
response = agent.chat("总结一下文档的主要内容")
response = agent.chat("基于这些内容，生成一个实施计划")
```

#### 示例 3：带摘要的长期对话

```python
from llama_index.core.memory import ChatSummaryMemoryBuffer
from llama_index.core import Settings
from llama_index.llms.ollama import Ollama

Settings.llm = Ollama(model="llama3.2", base_url="http://localhost:11434")

# 创建摘要记忆（自动压缩历史）
memory = ChatSummaryMemoryBuffer.from_defaults(
    token_limit=2000,
    llm=Settings.llm
)

# 长期对话
from llama_index.core.chat_engine import SimpleChatEngine

chat_engine = SimpleChatEngine.from_defaults(memory=memory)

# 多轮对话...
for i in range(10):
    response = chat_engine.chat(f"问题 {i+1}: ...")
    print(response)
```

---

## 3. Cognee

**GitHub**: https://github.com/topoteretes/cognee  
**文档**: https://docs.cognee.ai  
**许可证**: Apache 2.0

### 核心特性

- 开源知识图谱记忆
- 结合嵌入、图谱和认知科学
- 支持多模态数据（文本、图片等）
- 自动路由检索策略
- 提供 remember/recall/forget/improve 四个 API
- 支持 Claude Code 插件集成

---

### 本地部署方式一：pip 安装（推荐）

#### 前置要求

- Python 3.10 - 3.14
- LLM API Key（OpenAI 或其他）

#### 步骤 1：安装

```bash
# 创建虚拟环境
python -m venv cognee-env
source cognee-env/bin/activate

# 安装 cognee
pip install cognee

# 或使用 uv（更快）
uv pip install cognee
```

#### 步骤 2：配置环境变量

```bash
# .env 文件
LLM_API_KEY=your-openai-api-key

# 使用本地 Ollama（可选）
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.2
```

#### 步骤 3：初始化数据库

```bash
# cognee 使用 PostgreSQL + Neo4j，首次运行会自动初始化
# 也可手动初始化
python -c "import cognee; import asyncio; asyncio.run(cognee.init())"
```

---

### 本地部署方式二：Docker Compose（完整栈）

```bash
# 克隆仓库
git clone https://github.com/topoteretes/cognee.git
cd cognee

# 配置环境变量
cp .env.example .env
# 编辑 .env 设置你的 API Key

# 启动所有服务
docker compose up -d

# 服务包括：
# - PostgreSQL（关系数据）
# - Neo4j（知识图谱）
# - Cognee API
# - Cognee UI（可选）
```

#### Docker Compose 配置参考

```yaml
# docker-compose.yml
services:
  cognee:
    image: cognee/cognee:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/cognee
      - NEO4J_URL=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=password
      - LLM_API_KEY=${LLM_API_KEY}
    depends_on:
      - postgres
      - neo4j

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=cognee
    volumes:
      - postgres_data:/var/lib/postgresql/data

  neo4j:
    image: neo4j:5.26.0-community
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/password
    volumes:
      - neo4j_data:/data

volumes:
  postgres_data:
  neo4j_data:
```

---

### 本地使用示例

#### 基础 API 使用

```python
import cognee
import asyncio

async def main():
    # 初始化
    await cognee.init()
    
    # 1. 存储记忆（永久存储到知识图谱）
    await cognee.remember("Cognee 可以将文档转换为 AI 记忆")
    await cognee.remember("用户偏好详细的技术解释")
    
    # 2. 会话记忆（快速缓存，后台同步到图谱）
    await cognee.remember("当前讨论的是部署方案", session_id="chat_1")
    
    # 3. 智能检索（自动选择最佳搜索策略）
    results = await cognee.recall("Cognee 是做什么的？")
    for result in results:
        print(f"- {result}")
    
    # 4. 会话记忆优先，图谱兜底
    results = await cognee.recall("当前讨论什么？", session_id="chat_1")
    
    # 5. 添加文档
    await cognee.add("path/to/your/documents/")
    # 执行认知处理（提取知识图谱）
    await cognee.cognify()
    
    # 6. 删除记忆
    await cognee.forget(dataset="main_dataset")
    
    # 7. 改进记忆（基于反馈）
    await cognee.improve()

asyncio.run(main())
```

#### CLI 使用

```bash
# 记忆
cognee-cli remember "Cognee 可以将文档转换为 AI 记忆"

# 检索
cognee-cli recall "Cognee 是做什么的？"

# 添加文档
cognee-cli add /path/to/documents/

# 处理文档（提取知识图谱）
cognee-cli cognify

# 清空所有记忆
cognee-cli forget --all

# 打开本地 UI
cognee-cli -ui
# 访问 http://localhost:8080
```

---

### 与 Claude Code 集成（本地插件）

```bash
# 1. 安装 cognee
pip install cognee

# 2. 配置环境变量
export LLM_API_KEY="your-openai-key"

# 3. 克隆集成插件
git clone https://github.com/topoteretes/cognee-integrations.git

# 4. 启动 Claude Code 并加载插件
claude --plugin-dir ./cognee-integrations/integrations/claude-code
```

**插件生命周期：**

| 事件 | 作用 |
|------|------|
| `SessionStart` | 初始化记忆系统 |
| `PostToolUse` | 捕获工具调用到会话记忆 |
| `UserPromptSubmit` | 注入相关上下文到对话 |
| `PreCompact` | 上下文压缩前保留关键记忆 |
| `SessionEnd` | 会话数据同步到永久知识图谱 |

#### 连接到本地 Cognee 服务

```python
import cognee

# 连接到本地运行的 Cognee 服务
await cognee.serve(
    url="http://localhost:8000",
    api_key="your-local-api-key"
)

# 现在所有 SDK 调用都路由到本地服务
await cognee.remember("重要上下文")
results = await cognee.recall("发生了什么？")

await cognee.disconnect()
```

---

## 4. 框架对比

### 本地部署对比表

| 特性 | Mem0 | Zep (Graphiti) | LlamaIndex Memory | Cognee |
|------|------|----------------|-------------------|--------|
| **本地部署** | ✅ Docker/pip | ✅ Docker | ✅ 纯 Python | ✅ Docker/pip |
| **外部依赖** | Qdrant | Neo4j | 无（可选 ChromaDB） | PostgreSQL + Neo4j |
| **最低内存** | 2GB | 4GB | 512MB | 4GB |
| **启动时间** | 1-2 分钟 | 2-3 分钟 | 即时 | 2-3 分钟 |
| **知识图谱** | 实体链接 | 核心特性 | 可选集成 | 核心特性 |
| **多模态** | ❌ | ❌ | ❌ | ✅ |
| **学习曲线** | 低 | 中 | 低 | 中 |
| **API 简洁度** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

### 选型建议

| 场景 | 推荐框架 | 原因 |
|------|----------|------|
| **快速原型/测试** | Mem0（库模式） | pip install 即用，5 分钟上手 |
| **纯 Python 环境** | LlamaIndex Memory | 无外部服务依赖 |
| **复杂关系推理** | Zep (Graphiti) | 时序知识图谱，关系追踪 |
| **多模态数据** | Cognee | 支持文本+图片+音频 |
| **长期对话** | LlamaIndex + Summary | 自动压缩历史 |
| **生产级 Agent** | Mem0 (Docker) 或 Cognee | 稳定、可扩展 |
| **最低资源消耗** | LlamaIndex Memory | 无外部数据库 |

### 本地部署复杂度排序

```
LlamaIndex (纯 Python) < Mem0 (库) < Cognee (pip) < Mem0 (Docker) < Zep (Neo4j) < Cognee (Docker)
       ↓                    ↓            ↓              ↓               ↓              ↓
    即时启动             1 分钟        2 分钟          3 分钟          4 分钟         5 分钟
```

---

## 快速开始清单

### 方案 A：最简部署（无外部依赖）

```bash
# LlamaIndex Memory - 纯 Python，无需任何服务
pip install llama-index-core llama-index-llms-ollama

# 验证
python -c "
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.llms.ollama import Ollama
llm = Ollama(model='llama3.2', base_url='http://localhost:11434')
memory = ChatMemoryBuffer.from_defaults(token_limit=4096)
print('✅ LlamaIndex Memory ready')
"
```

### 方案 B：轻量级 + 向量搜索

```bash
# Mem0 - 使用 Qdrant（Docker）
pip install mem0ai
docker run -d -p 6333:6333 qdrant/qdrant

python -c "
from mem0 import Memory
m = Memory()
m.add('测试记忆', user_id='test')
print(m.search('测试', user_id='test'))
print('✅ Mem0 ready')
"
```

### 方案 C：完整知识图谱

```bash
# Cognee - PostgreSQL + Neo4j
pip install cognee
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password postgres:16
docker run -d -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:5.26.0-community

python -c "
import cognee, asyncio
asyncio.run(cognee.init())
print('✅ Cognee ready')
"
```

---

## 参考资源

### 官方文档
- **Mem0**: https://docs.mem0.ai | https://github.com/mem0ai/mem0
- **Graphiti** (Zep 引擎): https://github.com/getzep/graphiti
- **LlamaIndex**: https://developers.llamaindex.ai | https://github.com/run-llama/llama_index
- **Cognee**: https://docs.cognee.ai | https://github.com/topoteretes/cognee

### 本地模型推荐
- **LLM**: Ollama + llama3.2 / qwen2.5
- **Embedding**: nomic-embed-text / bge-small
- **向量数据库**: Qdrant / ChromaDB / Milvus
- **图数据库**: Neo4j Community Edition

---

*文档生成时间: 2026-05-06*
*版本: v2.0 (本地部署专注版)*

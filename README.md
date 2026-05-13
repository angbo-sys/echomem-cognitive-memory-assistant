# EchoMem

[English README](README.en.md)


EchoMem 是一个面向学习场景的认知记忆助手。它不只是回答当前这一句话，而是会结合用户的长期目标、讲解偏好、薄弱知识点、情绪状态、历史对话和知识背景，生成更贴近个人状态的回答。

它也不是一个黑箱记忆系统。EchoMem 提供了可视化观测台，可以看到系统检索了哪些记忆、更新了什么画像、调用了哪些记忆框架、哪些内容被写回长期记忆。

## 项目能做什么

- 记住长期学习目标、讲解偏好、薄弱领域、近期关注和历史对话。
- 支持短期记忆、多会话恢复和会话切换。
- 形成并持续更新用户画像。
- 识别困惑、焦虑、疲惫、好奇、沮丧等学习情绪。
- 回答前主动检索相关历史记忆。
- 集成 Mem0、LlamaIndex Memory、Cognee 三个记忆框架。
- 在 Streamlit UI 中展示框架贡献、记忆写回、画像变化和系统状态。
- 支持 MiMo、DeepSeek、OpenAI、Qwen、Ollama 多个模型 Provider。

## 当前状态

当前已验证基线：

- 单元测试：`107 tests / 107 pass`
- 交付工作流：Compile / Unit Tests / Baseline Eval 全部通过
- 云端记忆框架：Mem0 Cloud、LlamaCloud、Cognee Cloud 已集成
- API 配置：统一通过 `config.load_config()` 管理
- 密钥策略：真实 API Key 只应放在 `.env` 或部署环境变量中

## 目录结构

```text
agent/        对话主编排流程和学习工具
config/       统一配置加载与运行时组件工厂
docs/         项目介绍、审查报告、测试说明和设计文档
experiments/  Baseline 评测脚本和指标
llm/          各模型 Provider 适配器
memory/       短期记忆、长期记忆、检索、向量后端和三框架整合
profile/      用户画像和情绪识别
scripts/      工作流、环境检查、密钥扫描和工具脚本
tests/        单元测试和集成测试
ui/           Streamlit 应用、可视化组件、主题和文本格式化
```

## 配置方式

复制环境变量模板：

```bash
cp .env.example .env
```

运行时配置读取优先级：

1. 当前进程环境变量
2. `.env`
3. `config/settings.toml`

`config/settings.toml` 只保留非敏感默认项和产品参数。真实 API Key 和 API Base URL 应放在 `.env` 或部署环境变量中。

常用配置项：

```bash
LLM_PROVIDER=mimo
LLM_MODEL=mimo-v2.5-pro

MIMO_API_KEY=
MIMO_BASE_URL=

DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=

MEM0_API_KEY=
LLAMA_CLOUD_API_KEY=
COGNEE_API_KEY=
COGNEE_BASE_URL=
```

## 上传仓库前的安全检查

不要上传这些文件或目录：

```text
.env
*.db
memory.db
stm.db
profile/profile.db
.context/
.deps/
node_modules/
chroma_db/
.mem0_faiss/
__pycache__/
```

它们已经写入 `.gitignore`，但如果你用网页拖拽整个文件夹上传，`.gitignore` 不一定会保护你。建议使用 Git 上传。

发布前运行：

```bash
conda run -n echomem-test python scripts/secret_scan.py --strict
```

如果真实 Key 曾经被粘贴到聊天、Issue、截图或公开页面里，请在公开仓库前先去对应平台轮换这些 Key。

## 启动应用

项目当前在本地 Conda 环境 `echomem-test` 中验证。

启动 Streamlit UI：

```bash
conda run -n echomem-test streamlit run ui/app.py
```

检查环境和配置：

```bash
conda run -n echomem-test python scripts/check_memory_frameworks_env.py
```

## 运行测试

运行全量测试：

```bash
conda run -n echomem-test python -m unittest discover tests -v
```

运行交付工作流：

```bash
conda run -n echomem-test python scripts/workflow.py
```

工作流会执行：

- Python 编译检查
- 单元测试
- Baseline 评测

可选严格密钥扫描：

```bash
conda run -n echomem-test python scripts/secret_scan.py --strict
```

## 三个记忆框架

EchoMem 同时整合三个记忆框架，它们承担不同角色：

| 框架 | 作用 |
| --- | --- |
| Mem0 | 用户事实、偏好和画像类记忆 |
| LlamaIndex Memory | 会话和文档知识上下文 |
| Cognee | 知识图谱关系和概念联想 |

UI 会展示每个框架的贡献和写回状态，方便判断框架是真的返回了有用内容，还是只是完成了接入。

## 配套文档

建议阅读：

- `docs/项目介绍.md`：面向非技术人员的项目介绍
- `docs/当前状态.md`：当前状态和最新验证基线
- `docs/项目审查报告.md`：审查报告、风险和后续计划
- `docs/本地测试手册.md`：本地测试流程
- `docs/端到端记忆测试手册.md`：端到端记忆测试流程
- `docs/开源记忆框架接入说明.md`：记忆框架接入说明
- `docs/mimo_api接入说明.md`：MiMo 与统一 API 配置说明

## 当前限制

- LLM 回复目前仍是完整返回，还不是逐 token 流式输出。
- UI 尚未接入自动截图级视觉回归。
- Orchestrator 仍偏集中式，后续可以拆成更清晰的 Pipeline。
- UI 尺寸、Prompt 权重等产品参数还可以继续集中治理。

## 仓库命名建议

推荐：

```text
echomem-cognitive-memory-assistant
```

备选：

```text
echomem
echomem-learning-memory-agent
echomem-ai-study-assistant
```

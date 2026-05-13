# EchoMem

[中文说明](README.md)

Recommended repository name: `echomem-cognitive-memory-assistant`

EchoMem is a cognitive memory assistant for learning scenarios. It is designed to remember a learner over time, track changing goals and weak points, and show how memory is used inside the answer process.

Unlike a normal one-off chatbot, EchoMem combines conversation, short-term memory, long-term memory, user profiling, emotion recognition, memory retrieval, and a visual observation dashboard.

## What It Does

- Remembers long-term learning goals, preferences, weak subjects, recent focus, and conversation history.
- Supports short-term memory and multi-session switching.
- Builds and updates a structured user profile.
- Detects learning-related emotional states such as confusion, anxiety, tiredness, curiosity, and discouragement.
- Retrieves relevant memories before answering.
- Integrates three memory frameworks: Mem0, LlamaIndex Memory, and Cognee.
- Shows framework contributions, memory writes, profile changes, and system status in a Streamlit UI.
- Supports multiple LLM providers: MiMo, DeepSeek, OpenAI, Qwen, and Ollama.

## Project Status

Current verified baseline:

- Unit tests: `107 tests / 107 pass`
- Delivery workflow: Compile / Unit Tests / Baseline Eval passed
- Memory framework cloud path: Mem0 Cloud, LlamaCloud, and Cognee Cloud are integrated
- API configuration: centralized through `config.load_config()`
- Secrets: real API keys should live only in `.env` or deployment environment variables

## Repository Structure

```text
agent/        Main orchestration flow and learning tools
config/       Unified configuration loader and runtime factories
docs/         Project introduction, review reports, testing notes, design docs
experiments/  Baseline evaluation scripts and metrics
llm/          LLM provider adapters
memory/       STM, LTM, retrieval, vector store, memory framework integration
profile/      User profile and emotion engine
scripts/      Workflow, environment check, secret scan, utility scripts
tests/        Unit and integration tests
ui/           Streamlit app, visual components, theme, text formatting
```

## Configuration

Copy the example environment file and fill in your own values:

```bash
cp .env.example .env
```

Runtime configuration priority:

1. Process environment variables
2. `.env`
3. `config/settings.toml`

`config/settings.toml` should only keep non-sensitive defaults and product parameters. Real API keys and API base URLs should be placed in `.env` or deployment environment variables.

Important variables include:

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

## Security Before Uploading

Do not upload these files or folders:

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

They are already listed in `.gitignore`, but if you upload by dragging a folder into a website, `.gitignore` may not protect you. Use Git whenever possible.

Before publishing, run:

```bash
conda run -n echomem-test python scripts/secret_scan.py --strict
```

If any real key has ever been pasted into a chat, issue, screenshot, or public page, rotate that key before publishing the repository.

## Run The App

The project has been verified in the local Conda environment `echomem-test`.

Start the Streamlit UI:

```bash
conda run -n echomem-test streamlit run ui/app.py
```

Run the environment/configuration check:

```bash
conda run -n echomem-test python scripts/check_memory_frameworks_env.py
```

## Run Tests

Run all tests:

```bash
conda run -n echomem-test python -m unittest discover tests -v
```

Run the delivery workflow:

```bash
conda run -n echomem-test python scripts/workflow.py
```

The workflow performs:

- Python compile check
- Unit tests
- Baseline evaluation

Optional strict secret scan:

```bash
conda run -n echomem-test python scripts/secret_scan.py --strict
```

## Memory Frameworks

EchoMem uses three memory frameworks with different roles:

| Framework | Role |
| --- | --- |
| Mem0 | User facts, preferences, and profile-like memories |
| LlamaIndex Memory | Conversation and document knowledge context |
| Cognee | Knowledge graph relations and concept associations |

The UI exposes framework contributions and write-back status, so you can see whether a framework is merely connected or actually returning useful content.

## Documentation

Useful documents:

- `docs/项目介绍.md`: non-technical project introduction
- `docs/当前状态.md`: current status and latest verification baseline
- `docs/项目审查报告.md`: review report, risks, and follow-up plan
- `docs/本地测试手册.md`: local testing guide
- `docs/端到端记忆测试手册.md`: end-to-end memory testing guide
- `docs/开源记忆框架接入说明.md`: memory framework integration notes
- `docs/mimo_api接入说明.md`: MiMo and unified API configuration notes

## Current Limitations

- LLM responses are still returned as full text, not token-by-token streaming.
- UI visual regression is not yet automated with screenshots.
- The orchestrator is still relatively centralized and can be split into clearer pipeline stages.
- Some product parameters, such as UI sizing and prompt weighting, can be further centralized.

## Suggested Repository Name

Use:

```text
echomem-cognitive-memory-assistant
```

Short alternatives:

```text
echomem
echomem-learning-memory-agent
echomem-ai-study-assistant
```

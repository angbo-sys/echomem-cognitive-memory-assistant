# MiMo API 接入说明

## 1. 统一配置位置
- 主配置文件：[settings.toml](/Users/yelainab/project/EchoMem/config/settings.toml)
- 本地密钥文件：`.env`（参考 [.env.example](/Users/yelainab/project/EchoMem/.env.example)）

统一读取优先级：
1. 当前运行环境变量
2. `.env`
3. `config/settings.toml`

推荐流程：
1. 复制 `.env.example` 为 `.env`
2. 填写 `MIMO_API_KEY`
3. 在 `.env` 中填写 `MIMO_BASE_URL`、模型路由和其他 API 地址
4. 按需修改 `config/settings.toml` 的非敏感默认参数

同一套配置机制也管理 DeepSeek、OpenAI、Qwen、Ollama、记忆分析模型和 Mem0 / LlamaCloud / Cognee Cloud 等云端记忆框架配置。

## 2. 模型建议
- 文本推理默认：`mimo-v2.5-pro`
- 多模态可改为：`mimo-v2.5`

## 3. 代码接入
```python
from config import build_llm_from_config, load_config

cfg = load_config()
llm = build_llm_from_config(cfg)

text = llm.generate("请根据我的目标生成一周学习计划")
print(text)
```

## 4. 认证方式
- 默认使用 `Authorization: Bearer <MIMO_API_KEY>`
- 如需切换 `api-key` 头，初始化时设置 `use_api_key_header=True`

## 5. 与当前工程的集成建议
- 在 `agent/orchestrator.py` 初始化 `llm` 时替换为 `MiMoAdapter`
- 保持 `BaseLLM.generate(prompt, **kwargs)` 接口不变，无需改动 orchestrator

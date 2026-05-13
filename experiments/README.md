# Experiments Evaluation Skeleton

`experiments/` 提供一个轻量可运行的 baseline 评测骨架：

- `run_baselines.py`: 运行 Baseline A/B/C/Proposed，并打印指标表格。
- `metrics.py`: 指标计算函数（基于记录列表）。

## 数据格式（JSONL）

每行一个 JSON 对象，建议字段：

```json
{
  "query": "I prefer concise technical answers",
  "memory_bank": [
    {"id": "m1", "text": "User likes concise replies", "timestamp": "2026-05-01T10:00:00"},
    {"id": "m2", "text": "User is preparing for interviews", "timestamp": "2026-04-20T09:00:00"}
  ],
  "relevant_ids": ["m1"],
  "gold_preference": "practical",
  "gold_emotion": "calm",
  "gold_persona_traits": ["concise", "practical"]
}
```

说明：
- `run_baselines.py` 会在运行时产出 `retrieved_ids/response/pred_*/*tokens` 等预测字段。
- 指标函数对缺失字段容错，缺失时会跳过或按 0 处理。

## 运行

```bash
python experiments/run_baselines.py --data path/to/eval.jsonl
```

内置样例可直接跑：

```bash
python experiments/run_baselines.py --data experiments/data/sample_eval.jsonl
```

可选参数：

```bash
python experiments/run_baselines.py \
  --data path/to/eval.jsonl \
  --baselines A B C Proposed \
  --recall-k 5 \
  --price-per-1k 0.15
```

## 当前 Baseline 说明

- Baseline A: 关键词匹配检索（规则）
- Baseline B: 按时间戳倒序检索（规则）
- Baseline C: 关键词 + 轻量时序 bonus（规则）
- Proposed: 使用本地 `Orchestrator + MemorySearch + EmotionAnalyzer` 确定性链路，不调用外部模型，也不读取 gold 标签

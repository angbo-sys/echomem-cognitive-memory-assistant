from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory import LongTermMemory, OpenSourceMemoryHub


def main() -> int:
    parser = argparse.ArgumentParser(description="Build user knowledge system and architecture graph.")
    parser.add_argument("--user-id", default="u_test", help="Target user id.")
    parser.add_argument("--query", default="总结当前用户的知识体系", help="Analysis query.")
    parser.add_argument("--db-path", default="memory.db", help="Path to memory sqlite db.")
    parser.add_argument("--out", default="docs/user_knowledge_map.md", help="Output markdown file.")
    parser.add_argument("--max-memories", type=int, default=300, help="Max active memories to inspect.")
    parser.add_argument(
        "--strict-user-scope",
        action="store_true",
        help="Only use memories tagged with [user=<user-id>] when available.",
    )
    args = parser.parse_args()

    ltm = LongTermMemory(db_path=args.db_path)
    rows = ltm.list_memories(status="active", limit=max(10, args.max_memories))
    tagged_rows = [r for r in rows if f"[user={args.user_id}]" in str(r.get("content", ""))]
    if args.strict_user_scope and tagged_rows:
        rows = tagged_rows
    hub = OpenSourceMemoryHub()
    hints = hub.collect_hints(
        user_id=args.user_id,
        query=args.query,
        stm_text="",
        ltm_rows=rows,
    )

    graph = hints.get("user_knowledge_system", {}).get("graph", {})
    mermaid = graph.get("mermaid", "graph TD\n  Empty[No Knowledge Yet]")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "\n".join(
            [
                f"# 用户知识体系分析（{args.user_id}）",
                "",
                "## 开源记忆框架分析输出",
                "```json",
                json.dumps(hints, ensure_ascii=False, indent=2, default=str),
                "```",
                "",
                "## 用户知识架构图（Mermaid）",
                "```mermaid",
                mermaid,
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

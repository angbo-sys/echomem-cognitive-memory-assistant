from __future__ import annotations

from config import build_llm_from_config, load_config


def main() -> None:
    cfg = load_config()
    if not cfg.mimo.api_key:
        raise RuntimeError("Missing MIMO_API_KEY. Please set it in .env or environment variables.")

    llm = build_llm_from_config(cfg)

    prompt = "你是学习教练，请给我一个 7 天英语复习计划。"
    reply = llm.generate(prompt)
    print(reply)


if __name__ == "__main__":
    main()

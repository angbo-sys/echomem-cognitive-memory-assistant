from __future__ import annotations

from agent import Orchestrator
from agent.tools import EmotionAnalyzer
from config import build_llm_from_config, build_memory_search_from_config, load_config
from memory import LongTermMemory, ShortTermMemory
from profile import ProfileManager


def main() -> None:
    cfg = load_config()
    llm = build_llm_from_config(cfg)
    memory_tool = build_memory_search_from_config(cfg)

    stm = ShortTermMemory(max_turns=6)
    profile = ProfileManager(db_path="profile/profile.db")
    ltm = LongTermMemory(db_path="memory.db")

    # Seed minimal data for demo.
    profile.update_field("demo_user", "preferred_style", "简洁", "seed", 0.9)
    ltm.add_memory(content="用户偏好：回答简洁", mtype="preference", importance=0.9, source="seed")

    orchestrator = Orchestrator(
        stm=stm,
        profile=profile,
        emotion_tool=EmotionAnalyzer(),
        memory_tool=memory_tool,
        llm=llm,
    )

    result = orchestrator.run("我下周考试，今晚该怎么复习？", user_id="demo_user")
    print(result.get("response", ""))


if __name__ == "__main__":
    main()


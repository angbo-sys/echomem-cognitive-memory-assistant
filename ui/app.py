import json
import html
import sqlite3
import sys
from pathlib import Path
from typing import Any
from datetime import datetime

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent import Orchestrator
from agent.tools import EmotionAnalyzer
from config import build_llm_from_config, build_memory_search_from_config, load_config
from config.factory import get_provider_capability
from memory import LongTermMemory, ShortTermMemory
from profile import ProfileManager
from ui.components import (
    render_capability_map,
    render_hit_card,
    render_masthead,
    render_memory_framework_lab,
    render_memory_composition,
    render_observation_header,
    render_panel_title,
    render_profile_constellation,
)
from ui.text_formatting import format_long_text_html
from ui.theme import inject_theme

PROFILE_DB = ROOT / "profile" / "profile.db"
MEMORY_DB = ROOT / "memory.db"
STM_DB = ROOT / "stm.db"


def read_sqlite_table(db_path: Path, query: str, params: tuple[Any, ...] = ()) -> pd.DataFrame:
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(query, conn, params=params)


def safe_query(db_path: Path, query: str, params: tuple[Any, ...] = ()) -> tuple[pd.DataFrame, str | None]:
    try:
        return read_sqlite_table(db_path, query, params=params), None
    except Exception as exc:
        return pd.DataFrame(), str(exc)


def load_user_options() -> tuple[list[str], str | None]:
    users_df, users_err = safe_query(PROFILE_DB, "SELECT user_id FROM profile_current ORDER BY updated_at DESC")
    if users_err:
        return ["demo_user"], users_err
    user_options = users_df["user_id"].dropna().astype(str).unique().tolist()
    if not user_options:
        return ["demo_user"], None
    return user_options, None


DEFAULT_SESSION_ID = "streamlit"


def load_persisted_chat_messages(user_id: str, session_id: str) -> list[dict[str, Any]]:
    stm = ShortTermMemory(max_turns=40, db_path=STM_DB, user_id=user_id, session_id=session_id)
    return [
        {"role": item.get("role", "assistant"), "content": item.get("content", "")}
        for item in stm.get_recent(40)
        if item.get("role") in {"user", "assistant"} and item.get("content")
    ]


def clear_persisted_chat_messages(user_id: str, session_id: str) -> None:
    ShortTermMemory(max_turns=40, db_path=STM_DB, user_id=user_id, session_id=session_id).clear()


def list_chat_sessions(user_id: str) -> list[dict[str, Any]]:
    sessions = ShortTermMemory(
        max_turns=40,
        db_path=STM_DB,
        user_id=user_id,
        session_id=DEFAULT_SESSION_ID,
    ).list_sessions(limit=30)
    if not sessions:
        return [
            {
                "session_id": DEFAULT_SESSION_ID,
                "title": "新会话",
                "message_count": 0,
                "updated_at": "",
            }
        ]
    return sessions


def create_chat_session_id() -> str:
    return "streamlit-" + datetime.now().strftime("%Y%m%d-%H%M%S")


def render_chat_card(message: dict[str, Any]) -> None:
    """Render chat without Streamlit's clipped chat-message wrapper."""
    role = str(message.get("role", "assistant"))
    is_user = role == "user"
    role_class = "user" if is_user else "assistant"
    role_label = "你" if is_user else "EchoMem"
    avatar = "你" if is_user else "E"
    content_html = format_long_text_html(message.get("content", ""))
    st.markdown(
        f"""
        <section class="echomem-chat-card {role_class}">
          <div class="echomem-chat-avatar">{avatar}</div>
          <div class="echomem-chat-body">
            <div class="echomem-chat-role">{role_label}</div>
            <div class="echomem-chat-content">{content_html}</div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


@st.cache_resource(show_spinner=False)
def build_runtime(
    user_id: str,
    session_id: str,
    retrieval_backend: str,
    candidate_k: int,
    top_k: int,
    decay_lambda: float,
) -> Orchestrator:
    cfg = load_config()
    cfg = cfg.__class__(
        llm=cfg.llm,
        mimo=cfg.mimo,
        deepseek=cfg.deepseek,
        openai=cfg.openai,
        qwen=cfg.qwen,
        ollama=cfg.ollama,
        retrieval=cfg.retrieval.__class__(
            backend=retrieval_backend,
            candidate_k=candidate_k,
            top_k=top_k,
            decay_lambda=decay_lambda,
        ),
        memory_frameworks=cfg.memory_frameworks,
        memory_analysis=cfg.memory_analysis,
    )
    llm = build_llm_from_config(cfg)
    memory_tool = build_memory_search_from_config(cfg)
    stm = ShortTermMemory(max_turns=40, db_path=STM_DB, user_id=user_id, session_id=session_id)
    profile = ProfileManager(db_path=PROFILE_DB)
    return Orchestrator(
        stm=stm,
        profile=profile,
        emotion_tool=EmotionAnalyzer(),
        memory_tool=memory_tool,
        llm=llm,
    )


def _process_message(
    prompt: str,
    selected_user: str,
    selected_session: str,
    task_mode: str,
    retrieval_backend: str,
    candidate_k: int,
    top_k: int,
    decay_lambda: float,
    status_filter: str,
    mtype_filter: str,
    persist_chat_memory: bool,
    enable_mimo_analysis: bool,
    fast_response_mode: bool,
) -> None:
    """Call LLM and persist to memory."""
    try:
        runtime = build_runtime(selected_user, selected_session, retrieval_backend, candidate_k, top_k, decay_lambda)
        response_token_budget = 520 if fast_response_mode else 900
        extra_context = {
            "status_filter": None if status_filter == "all" else status_filter,
            "mtype_filter": mtype_filter.strip() or None,
            "enable_mimo_analysis": enable_mimo_analysis and not fast_response_mode,
            "max_completion_tokens": response_token_budget,
            "max_prompt_chars": 12000 if fast_response_mode else 20000,
            "response_style": "fast_concise" if fast_response_mode else "full_detail",
        }
        result = runtime.run(prompt, user_id=selected_user, task=task_mode, extra_context=extra_context)
        if isinstance(result, dict):
            result["task_mode"] = task_mode
        profile_updates = result.get("profile_updates", []) if isinstance(result, dict) else []
        memory_evolution: list[dict[str, Any]] = []
        if isinstance(profile_updates, list) and profile_updates:
            ltm_for_profile = LongTermMemory(db_path=MEMORY_DB)
            for update in profile_updates:
                if not isinstance(update, dict) or not update.get("applied"):
                    continue
                try:
                    evo = ltm_for_profile.detect_conflict_and_update(
                        user_id=selected_user,
                        field=str(update.get("field", "")),
                        old_value=update.get("old_value"),
                        new_value=update.get("new_value"),
                        trigger=str(update.get("trigger", "profile_update")),
                        confidence=float(update.get("confidence", 0.6) or 0.6),
                    )
                    memory_evolution.append(
                        {
                            "field": update.get("field"),
                            "old_value": update.get("old_value"),
                            "new_value": update.get("new_value"),
                            **(evo if isinstance(evo, dict) else {}),
                        }
                    )
                except Exception as exc:
                    memory_evolution.append(
                        {
                            "field": update.get("field"),
                            "old_value": update.get("old_value"),
                            "new_value": update.get("new_value"),
                            "error": str(exc),
                        }
                    )
        if isinstance(result, dict):
            result["memory_evolution"] = memory_evolution
        st.session_state.latest_result = result
        reply = result.get("response", "") or "未生成有效回复。"
        if persist_chat_memory:
            ltm = LongTermMemory(db_path=MEMORY_DB)
            ltm.add_memory(
                user_id=selected_user,
                content=f"[user={selected_user}] {prompt}",
                mtype="conversation_user",
                importance=0.65,
                status="active",
                source="ui_chat",
            )
            ltm.add_memory(
                user_id=selected_user,
                content=f"[assistant={selected_user}] {reply}",
                mtype="conversation_assistant",
                importance=0.60,
                status="active",
                source="ui_chat",
            )
    except Exception as exc:
        reply = f"调用失败：{exc}"
        st.session_state.latest_result = {"error": str(exc)}

    st.session_state.chat_messages.append({"role": "assistant", "content": reply})


def run_memory_probe(
    *,
    query: str,
    selected_user: str,
    retrieval_backend: str,
    candidate_k: int,
    top_k: int,
    decay_lambda: float,
    status_filter: str,
    mtype_filter: str,
    enable_mimo_analysis: bool,
) -> dict[str, Any]:
    """Run an ad-hoc memory search from the observability UI."""
    cfg = load_config()
    cfg = cfg.__class__(
        llm=cfg.llm,
        mimo=cfg.mimo,
        deepseek=cfg.deepseek,
        openai=cfg.openai,
        qwen=cfg.qwen,
        ollama=cfg.ollama,
        retrieval=cfg.retrieval.__class__(
            backend=retrieval_backend,
            candidate_k=candidate_k,
            top_k=top_k,
            decay_lambda=decay_lambda,
        ),
        memory_frameworks=cfg.memory_frameworks,
        memory_analysis=cfg.memory_analysis,
    )
    memory_tool = build_memory_search_from_config(cfg)
    return memory_tool.run(
        query,
        context={
            "user_id": selected_user,
            "status_filter": None if status_filter == "all" else status_filter,
            "mtype_filter": mtype_filter.strip() or None,
            "enable_mimo_analysis": enable_mimo_analysis,
        },
    )


# ── Main ────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="EchoMem 认知观测台", layout="wide", initial_sidebar_state="expanded")

inject_theme()


# ── Session state init ──────────────────────────────────────────────────────

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "latest_result" not in st.session_state:
    st.session_state.latest_result = None
if "pending_suggestion" not in st.session_state:
    st.session_state.pending_suggestion = None
if "active_page" not in st.session_state:
    st.session_state.active_page = "chat"
if st.session_state.active_page == "dashboard":
    st.session_state.active_page = "overview"
if "retrieval_backend" not in st.session_state:
    st.session_state.retrieval_backend = "chroma"
if "candidate_k" not in st.session_state:
    st.session_state.candidate_k = 30
if "top_k" not in st.session_state:
    st.session_state.top_k = 5
if "decay_lambda" not in st.session_state:
    st.session_state.decay_lambda = 0.05
if "status_filter" not in st.session_state:
    st.session_state.status_filter = "active"
if "mtype_filter" not in st.session_state:
    st.session_state.mtype_filter = ""
if "persist_chat_memory" not in st.session_state:
    st.session_state.persist_chat_memory = True
if "enable_mimo_analysis" not in st.session_state:
    st.session_state.enable_mimo_analysis = False
if "fast_response_mode" not in st.session_state:
    st.session_state.fast_response_mode = True
if "selected_user_id" not in st.session_state:
    st.session_state.selected_user_id = "demo_user"
if "selected_user_load_error" not in st.session_state:
    st.session_state.selected_user_load_error = None
if "selected_session_id" not in st.session_state:
    st.session_state.selected_session_id = DEFAULT_SESSION_ID
if "task_mode" not in st.session_state:
    st.session_state.task_mode = "chat"
if "chat_reply_font_size" not in st.session_state:
    st.session_state.chat_reply_font_size = 0.90
if "chat_loaded_for_scope" not in st.session_state:
    st.session_state.chat_loaded_for_scope = None
if "memory_search_query" not in st.session_state:
    st.session_state.memory_search_query = ""
if "memory_search_results" not in st.session_state:
    st.session_state.memory_search_results = None


user_options, users_err = load_user_options()
st.session_state.selected_user_load_error = users_err
if st.session_state.selected_user_id not in user_options:
    st.session_state.selected_user_id = user_options[0]
session_options = list_chat_sessions(st.session_state.selected_user_id)
session_ids = [str(item["session_id"]) for item in session_options]
if st.session_state.selected_session_id not in session_ids:
    st.session_state.selected_session_id = session_ids[0] if session_ids else DEFAULT_SESSION_ID
active_scope = (st.session_state.selected_user_id, st.session_state.selected_session_id)
if st.session_state.chat_loaded_for_scope != active_scope:
    st.session_state.chat_messages = load_persisted_chat_messages(
        st.session_state.selected_user_id,
        st.session_state.selected_session_id,
    )
    st.session_state.latest_result = None
    st.session_state.chat_loaded_for_scope = active_scope


st.markdown(
    f"""
    <style>
      [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])
      [data-testid="stMarkdownContainer"],
      [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])
      [data-testid="stMarkdownContainer"] * {{
        font-size: {st.session_state.chat_reply_font_size:.2f}rem !important;
      }}
      .echomem-chat-card.assistant .echomem-chat-content,
      .echomem-chat-card.assistant .echomem-chat-content * {{
        font-size: {st.session_state.chat_reply_font_size:.2f}rem !important;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    cfg_preview = load_config()
    provider_status = get_provider_capability(cfg_preview.llm.provider)
    if provider_status.get("implemented"):
        st.success(f"LLM Provider: {cfg_preview.llm.provider} (fully implemented)")
    else:
        reason = str(provider_status.get("reason") or "未实现")
        st.error(f"LLM Provider: {cfg_preview.llm.provider} (not fully implemented)")
        st.caption(reason)

    st.markdown("### 页面")
    page_options = {
        "💬 会话": "chat",
        "📊 总览": "overview",
        "🧬 记忆框架": "frameworks",
        "👤 用户画像": "profile",
        "🛠 系统能力": "capability",
    }
    page_labels = list(page_options.keys())
    current_label = next(
        (label for label, page in page_options.items() if page == st.session_state.active_page),
        "💬 会话",
    )
    page_choice = st.radio(
        "导航",
        page_labels,
        index=page_labels.index(current_label),
        label_visibility="collapsed",
    )
    new_page = page_options[page_choice]
    if new_page != st.session_state.active_page:
        st.session_state.active_page = new_page
        st.rerun()

    st.markdown("---")
    st.markdown("### 界面显示")
    st.session_state.chat_reply_font_size = st.slider(
        "会话回复字号",
        min_value=0.72,
        max_value=1.08,
        value=float(st.session_state.chat_reply_font_size),
        step=0.02,
        help="只调整 assistant 回复内容的字号。",
    )

    st.markdown("---")
    st.markdown("### 当前用户")
    st.session_state.selected_user_id = st.selectbox(
        "User ID",
        user_options,
        index=user_options.index(st.session_state.selected_user_id),
        help="会话与观测台共享同一 user_id。",
    )
    if st.session_state.selected_user_load_error:
        st.warning(
            f"Profile 数据库读取失败，已降级到 demo_user。详情: {st.session_state.selected_user_load_error}"
        )
    st.markdown("---")
    st.markdown("### 会话历史")
    session_options = list_chat_sessions(st.session_state.selected_user_id)
    session_ids = [str(item["session_id"]) for item in session_options]
    session_labels = {
        str(item["session_id"]): (
            f"{item.get('title') or item.get('session_id')} · "
            f"{item.get('message_count', 0)} 条"
        )
        for item in session_options
    }
    if st.session_state.selected_session_id not in session_ids:
        st.session_state.selected_session_id = session_ids[0] if session_ids else DEFAULT_SESSION_ID
    selected_session_label = st.selectbox(
        "会话",
        session_ids,
        index=session_ids.index(st.session_state.selected_session_id) if st.session_state.selected_session_id in session_ids else 0,
        format_func=lambda sid: session_labels.get(str(sid), str(sid)),
    )
    if selected_session_label != st.session_state.selected_session_id:
        st.session_state.selected_session_id = selected_session_label
        st.session_state.chat_loaded_for_scope = None
        st.rerun()
    if st.button("新建会话", width="stretch"):
        st.session_state.selected_session_id = create_chat_session_id()
        st.session_state.chat_messages = []
        st.session_state.latest_result = None
        st.session_state.chat_loaded_for_scope = (
            st.session_state.selected_user_id,
            st.session_state.selected_session_id,
        )
        st.rerun()
    st.markdown("---")
    st.markdown("### 任务模式")
    task_options = {
        "常规对话": "chat",
        "学习计划": "study_plan",
        "复习建议": "review",
    }
    selected_task_label = st.selectbox(
        "模式",
        list(task_options.keys()),
        index=list(task_options.values()).index(st.session_state.task_mode)
        if st.session_state.task_mode in task_options.values()
        else 0,
    )
    st.session_state.task_mode = task_options[selected_task_label]
    st.markdown("---")

    st.markdown("### 检索参数")
    st.session_state.retrieval_backend = st.selectbox(
        "检索后端",
        ["none", "chroma"],
        index=1 if st.session_state.retrieval_backend == "chroma" else 0,
    )
    st.session_state.candidate_k = st.slider(
        "候选数 Candidate K", min_value=5, max_value=100, value=st.session_state.candidate_k, step=5
    )
    st.session_state.top_k = st.slider(
        "返回数 Top K", min_value=1, max_value=20, value=st.session_state.top_k, step=1
    )
    st.session_state.decay_lambda = st.slider(
        "时间衰减 λ", min_value=0.01, max_value=0.20, value=st.session_state.decay_lambda, step=0.01
    )
    st.markdown("---")
    st.markdown("### 记忆过滤")
    status_options = ["active", "deprecated", "all"]
    st.session_state.status_filter = st.selectbox(
        "状态",
        status_options,
        index=status_options.index(st.session_state.status_filter) if st.session_state.status_filter in status_options else 0,
    )
    st.session_state.mtype_filter = st.text_input(
        "类型过滤", value=st.session_state.mtype_filter, placeholder="例如 preference"
    )
    st.markdown("---")
    st.session_state.fast_response_mode = st.toggle(
        "快速回复模式（减少思考时间）",
        value=st.session_state.fast_response_mode,
        help="开启后会跳过较慢的知识分析，并降低单次生成长度，让会话更快返回。",
    )
    st.session_state.persist_chat_memory = st.toggle("聊天写入长期记忆", value=st.session_state.persist_chat_memory)
    analysis_provider_label = load_config().memory_analysis.provider.upper()
    st.session_state.enable_mimo_analysis = st.toggle(
        f"开启 AI 知识分析（{analysis_provider_label}，较慢）",
        value=st.session_state.enable_mimo_analysis,
        disabled=st.session_state.fast_response_mode,
        help="快速回复模式开启时，聊天会自动跳过该分析；关闭快速模式后可用于更完整的知识分析。",
    )
    if st.button("清空当前会话", width="stretch"):
        st.session_state.chat_messages = []
        st.session_state.latest_result = None
        clear_persisted_chat_messages(st.session_state.selected_user_id, st.session_state.selected_session_id)
        st.rerun()


# ── Handle pending suggestion ───────────────────────────────────────────────

if st.session_state.pending_suggestion:
    suggestion = st.session_state.pending_suggestion
    st.session_state.pending_suggestion = None
    st.session_state.chat_messages.append({"role": "user", "content": suggestion})

    _process_message(
        suggestion, st.session_state.selected_user_id, st.session_state.selected_session_id, st.session_state.task_mode,
        st.session_state.retrieval_backend, st.session_state.candidate_k,
        st.session_state.top_k, st.session_state.decay_lambda,
        st.session_state.status_filter, st.session_state.mtype_filter,
        st.session_state.persist_chat_memory,
        st.session_state.enable_mimo_analysis,
        st.session_state.fast_response_mode,
    )
    st.rerun()


# ── Chat page ───────────────────────────────────────────────────────────────

if st.session_state.active_page == "chat":
    msg_count = len(st.session_state.chat_messages)
    active_session_meta = next(
        (item for item in list_chat_sessions(st.session_state.selected_user_id)
         if str(item.get("session_id")) == st.session_state.selected_session_id),
        {"title": "新会话"},
    )
    st.markdown(
        f"""
        <div class="chat-page-header">
          <div class="chat-page-title">
            <span class="chat-page-dot"></span>
            EchoMem · {html.escape(str(active_session_meta.get("title") or "新会话"))}
          </div>
          <div class="chat-page-meta">{msg_count} 条消息</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state.chat_messages:
        st.markdown(
            """
            <div class="welcome-card">
              <div class="welcome-greeting">
                你好！我是 EchoMem，你的认知记忆助手。<br>
                我可以帮你整理学习思路、回顾知识要点、分析薄弱环节。随便聊点什么吧。
              </div>
              <div class="welcome-hint">试试这些问题</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        suggestions = [
            ("📝", "帮我整理今天的错题"),
            ("🎯", "我最近哪些知识点薄弱？"),
            ("💡", "给我讲讲阅读理解的技巧"),
            ("📊", "分析一下我的学习进度"),
        ]

        cols = st.columns(2)
        for i, (icon, text) in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(f"{icon}  {text}", key=f"suggestion_{i}", width="stretch"):
                    st.session_state.pending_suggestion = text
                    st.rerun()

    st.markdown('<div class="echomem-chat-thread">', unsafe_allow_html=True)
    for msg in st.session_state.chat_messages:
        render_chat_card(msg)
    st.markdown("</div>", unsafe_allow_html=True)

    latest = st.session_state.latest_result if isinstance(st.session_state.latest_result, dict) else {}
    profile_updates = latest.get("profile_updates", []) if isinstance(latest.get("profile_updates"), list) else []
    memory_evolution = latest.get("memory_evolution", []) if isinstance(latest.get("memory_evolution"), list) else []
    if profile_updates or memory_evolution:
        with st.expander("本轮画像与记忆演化", expanded=False):
            if profile_updates:
                st.caption("画像更新")
                st.json(profile_updates)
            if memory_evolution:
                st.caption("记忆演化")
                st.json(memory_evolution)

    prompt = st.chat_input("说点什么...")
    if prompt:
        st.session_state.chat_messages.append({"role": "user", "content": prompt})

        _process_message(
            prompt, st.session_state.selected_user_id, st.session_state.selected_session_id, st.session_state.task_mode,
            st.session_state.retrieval_backend, st.session_state.candidate_k,
            st.session_state.top_k, st.session_state.decay_lambda,
            st.session_state.status_filter, st.session_state.mtype_filter,
            st.session_state.persist_chat_memory,
            st.session_state.enable_mimo_analysis,
            st.session_state.fast_response_mode,
        )
        st.rerun()


# ── Dashboard page ──────────────────────────────────────────────────────────

else:
    cfg_preview = load_config()
    api_mode = "API 已配置" if cfg_preview.mimo.api_key else "API 未配置"
    render_masthead(
        st,
        provider=cfg_preview.llm.provider,
        model=cfg_preview.llm.model,
        retrieval_backend=st.session_state.retrieval_backend,
        api_mode=api_mode,
    )
    selected_user = st.session_state.selected_user_id

    active_observation_page = st.session_state.active_page

    if active_observation_page == "overview":
        render_observation_header(
            st,
            eyebrow="Overview",
            title="总览",
            subtitle="先看系统运行状态、最近检索结果和记忆库走势，适合快速判断这一轮回答用到了什么。",
            chips=["检索命中", "记忆统计", "时间线", "衰减重排"],
        )
        upper_left, upper_right = st.columns(2, gap="large")

        with upper_left:
            render_panel_title(st, "记忆搜索台", "直接搜索当前用户记忆，核对召回、排序和三框架查询扩展")
            search_col, action_col = st.columns([4, 1], gap="small")
            with search_col:
                st.session_state.memory_search_query = st.text_input(
                    "搜索记忆",
                    value=st.session_state.memory_search_query,
                    placeholder="例如：我的偏好、雅思阅读、条件概率、最近压力",
                    label_visibility="collapsed",
                )
            with action_col:
                do_probe = st.button("搜索", width="stretch", type="primary")
            if do_probe and st.session_state.memory_search_query.strip():
                try:
                    st.session_state.memory_search_results = run_memory_probe(
                        query=st.session_state.memory_search_query,
                        selected_user=selected_user,
                        retrieval_backend=st.session_state.retrieval_backend,
                        candidate_k=st.session_state.candidate_k,
                        top_k=st.session_state.top_k,
                        decay_lambda=st.session_state.decay_lambda,
                        status_filter=st.session_state.status_filter,
                        mtype_filter=st.session_state.mtype_filter,
                        enable_mimo_analysis=False,
                    )
                except Exception as exc:
                    st.session_state.memory_search_results = {"error": str(exc), "hits": []}

            probe = st.session_state.memory_search_results
            if isinstance(probe, dict) and probe.get("error"):
                st.warning(f"搜索失败：{probe.get('error')}")
            elif isinstance(probe, dict) and isinstance(probe.get("hits"), list):
                st.caption(
                    f"当前搜索：{probe.get('query', '')} · backend={probe.get('backend', 'unknown')} · "
                    f"命中 {len(probe.get('hits', []))} 条"
                )
                for i, hit in enumerate(probe.get("hits", [])[:5], start=1):
                    if isinstance(hit, dict):
                        render_hit_card(
                            st,
                            hit=hit,
                            index=i,
                            backend=str(probe.get("backend", "unknown")),
                            s_filter=str(probe.get("status_filter", "active")),
                            t_filter=str(probe.get("mtype_filter", "") or "all"),
                        )

            render_panel_title(st, "上一轮检索解释", "命中结果按时间衰减重排，展示关键打分因子")
            latest = st.session_state.latest_result
            if isinstance(latest, dict):
                retrieval = latest.get("retrieval") if isinstance(latest.get("retrieval"), dict) else {}
                hits = retrieval.get("hits") if isinstance(retrieval, dict) else None
                if isinstance(hits, list) and hits:
                    for i, hit in enumerate(hits[:5], start=1):
                        backend = retrieval.get("backend", "unknown")
                        s_filter = retrieval.get("status_filter", "active")
                        t_filter = retrieval.get("mtype_filter", "")
                        render_hit_card(st, hit=hit, index=i, backend=backend, s_filter=s_filter, t_filter=t_filter)
                else:
                    st.markdown(
                        '<div class="empty-state">'
                        '<div class="empty-state-icon">🔍</div>'
                        '<div class="empty-state-text">暂无检索命中。先在「会话」页发送一条消息。</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    '<div class="empty-state">'
                    '<div class="empty-state-icon">📡</div>'
                    '<div class="empty-state-text">暂无运行结果。</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )

        with upper_right:
            render_panel_title(st, "检索仪表盘", "全局记忆结构统计")
            mem_stats_df, mem_stats_err = safe_query(
                MEMORY_DB,
                """
                SELECT type, status, COUNT(*) AS count, ROUND(AVG(importance), 2) AS avg_importance
                FROM memories
                GROUP BY type, status
                ORDER BY count DESC
                """,
            )
            if mem_stats_err:
                st.info(f"检索统计读取失败：{mem_stats_err}")
                mem_stats_df = pd.DataFrame([{"type": "preference", "status": "active", "count": 0, "avg_importance": 0.0}])

            total_mem = int(mem_stats_df["count"].sum()) if not mem_stats_df.empty else 0
            active_mem = int(mem_stats_df[mem_stats_df["status"] == "active"]["count"].sum()) if not mem_stats_df.empty else 0
            avg_imp = float(mem_stats_df["avg_importance"].mean()) if not mem_stats_df.empty else 0.0

            render_memory_composition(st, mem_stats_df.to_dict("records"))

            type_count = mem_stats_df.groupby("type", as_index=False)["count"].sum() if not mem_stats_df.empty else pd.DataFrame()
            if not type_count.empty:
                with st.expander("查看记忆类型柱状图", expanded=False):
                    st.bar_chart(type_count.set_index("type"))
            with st.expander("查看记忆统计明细", expanded=False):
                st.dataframe(mem_stats_df, width="stretch", hide_index=True, height=220)

        render_panel_title(st, "记忆时间线", "最近 80 条记忆的时序与重要性走势")
        timeline_df, timeline_err = safe_query(
            MEMORY_DB,
            """
            SELECT id, ts, type, importance, status, source, content
            FROM memories
            ORDER BY ts DESC
            LIMIT 80
            """,
        )
        if timeline_err:
            st.info(f"memory 读取失败：{timeline_err}")
            timeline_df = pd.DataFrame(
                [{"ts": "N/A", "type": "preference", "importance": 0.8, "status": "active", "content": "示例记忆"}]
            )

        if "importance" in timeline_df.columns and "ts" in timeline_df.columns:
            chart_df = timeline_df[["ts", "importance"]].copy()
            chart_df["ts"] = chart_df["ts"].astype(str)
            chart_df = chart_df.iloc[::-1]
            st.line_chart(chart_df.set_index("ts"))
        st.dataframe(timeline_df, width="stretch", hide_index=True, height=260)

        latest_retrieval = (
            latest.get("retrieval", {})
            if isinstance(latest, dict) and isinstance(latest.get("retrieval"), dict)
            else {}
        )
        latest_hits = latest_retrieval.get("hits", []) if isinstance(latest_retrieval.get("hits"), list) else []
        if latest_hits:
            decay_rows: list[dict[str, Any]] = []
            for idx, hit in enumerate(latest_hits[:10], start=1):
                if not isinstance(hit, dict):
                    continue
                decay_rows.append(
                    {
                        "rank": idx,
                        "similarity": float(hit.get("similarity", 0.0) or 0.0),
                        "importance": float(hit.get("importance", 0.0) or 0.0),
                        "decayed_score": float(hit.get("decayed_score", 0.0) or 0.0),
                    }
                )
            if decay_rows:
                render_panel_title(st, "时间衰减驱动检索", "相似度/重要性/衰减后得分对比")
                decay_df = pd.DataFrame(decay_rows)
                st.line_chart(decay_df.set_index("rank")[["similarity", "importance", "decayed_score"]])
                st.dataframe(decay_df, width="stretch", hide_index=True, height=220)

    elif active_observation_page == "frameworks":
        render_observation_header(
            st,
            eyebrow="Memory Frameworks",
            title="记忆框架",
            subtitle="专门比较 Mem0、LlamaIndex、Cognee 三条记忆通道的命中、来源、写回和知识分析效果。",
            chips=["Mem0", "LlamaIndex", "Cognee", "写回状态"],
        )
        latest = st.session_state.latest_result if isinstance(st.session_state.latest_result, dict) else {}
        retrieval = latest.get("retrieval", {}) if isinstance(latest.get("retrieval"), dict) else {}
        osm = retrieval.get("open_source_memory", {}) if isinstance(retrieval.get("open_source_memory"), dict) else {}
        if not osm:
            st.info("暂无框架分析结果。请先在「会话」页发送一条消息。")
        else:
            render_memory_framework_lab(st, osm)

            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.subheader("框架信号明细")
                contributions = (
                    osm.get("framework_contributions", [])
                    if isinstance(osm.get("framework_contributions"), list)
                    else []
                )
                if contributions:
                    framework_signal_rows = []
                    writes = osm.get("framework_writes", {}) if isinstance(osm.get("framework_writes"), dict) else {}
                    for item in contributions:
                        if not isinstance(item, dict):
                            continue
                        name = str(item.get("framework", ""))
                        write_info = writes.get(name, {}) if isinstance(writes.get(name), dict) else {}
                        framework_signal_rows.append(
                            {
                                "framework": name,
                                "role": item.get("role", ""),
                                "source": item.get("signal_source", ""),
                                "signals": item.get("signal_count", 0),
                                "stored": write_info.get("stored", ""),
                                "preview": " / ".join(str(x)[:42] for x in item.get("signals", [])[:2])
                                if isinstance(item.get("signals"), list)
                                else "",
                            }
                        )
                    st.dataframe(pd.DataFrame(framework_signal_rows), width="stretch", hide_index=True)
                else:
                    framework_cards = [
                        ("mem0", "偏好事实", len(osm.get("mem0", {}).get("facts", []) if isinstance(osm.get("mem0", {}), dict) else [])),
                        ("llamaindex", "文档命中", len(osm.get("llamaindex_memory", {}).get("doc_hits", []) if isinstance(osm.get("llamaindex_memory", {}), dict) else [])),
                        ("cognee", "关联概念", len(osm.get("cognee", {}).get("related_concepts", []) if isinstance(osm.get("cognee", {}), dict) else [])),
                    ]
                    framework_signal_rows: list[dict[str, Any]] = []
                    for name, label, score in framework_cards:
                        framework_signal_rows.append({"framework": name, "signal_type": label, "signal_count": score})
                    st.dataframe(pd.DataFrame(framework_signal_rows), width="stretch", hide_index=True)
                with st.expander("查看原始框架信号 JSON", expanded=False):
                    st.json(
                        {
                            "mem0": osm.get("mem0", {}),
                            "llamaindex_memory": osm.get("llamaindex_memory", {}),
                            "cognee": osm.get("cognee", {}),
                            "framework_contributions": osm.get("framework_contributions", []),
                            "framework_writes": osm.get("framework_writes", {}),
                            "query_expansion": osm.get("query_expansion", []),
                        }
                    )
            with c2:
                st.subheader("用户知识体系图")
                graph = osm.get("user_knowledge_system", {}).get("graph", {})
                if isinstance(graph, dict) and graph.get("mermaid"):
                    st.caption(
                        f"nodes={len(graph.get('nodes', []))} · edges={len(graph.get('edges', []))}"
                    )
                    st.code(graph.get("mermaid", ""), language="mermaid")
                else:
                    st.info("暂无可展示的知识图。")

            st.subheader("MiMo 知识分析")
            mimo_analysis = osm.get("mimo_analysis", {})
            if isinstance(mimo_analysis, dict):
                if mimo_analysis.get("summary"):
                    summary_html = format_long_text_html(mimo_analysis["summary"])
                    st.markdown(
                        f'<div class="mimo-analysis-card">{summary_html}</div>',
                        unsafe_allow_html=True,
                    )
                elif mimo_analysis.get("enabled"):
                    reason = str(mimo_analysis.get("reason", "")).strip().lower()
                    if reason == "timeout_degraded":
                        st.caption("知识分析仍在后台生成；主回复已先返回。再次触发相同查询时可命中缓存结果。")
                    else:
                        st.warning(f"MiMo 分析未产出内容：{mimo_analysis.get('error', 'unknown error')}")
                else:
                    analysis_provider = str(
                        mimo_analysis.get("provider", cfg_preview.memory_analysis.provider)
                    ).strip().lower()
                    reason = str(mimo_analysis.get("reason", "")).strip().lower()
                    if reason == "disabled_by_ui_toggle":
                        st.caption("知识分析已关闭（侧边栏可开启“AI 知识分析”开关）。")
                    elif analysis_provider == "deepseek":
                        st.caption("知识分析未就绪（请检查 DEEPSEEK_API_KEY 或 config/settings.toml 的 [deepseek].api_key）。")
                    else:
                        st.caption("知识分析未就绪（请检查 MIMO_API_KEY 或 config/settings.toml 的 [mimo].api_key）。")
            else:
                st.caption("MiMo 分析结果不可用。")

    elif active_observation_page == "profile":
        render_observation_header(
            st,
            eyebrow="User Profile",
            title="用户画像",
            subtitle="聚焦当前用户状态、画像字段变化和演化轨迹，帮助判断助手是否真正记住了用户。",
            chips=["当前画像", "本轮更新", "历史记录", "演化时间轴"],
        )
        render_panel_title(st, "用户画像快照", "当前用户画像 + 演化过程")
        profile_df, profile_err = safe_query(
            PROFILE_DB,
            "SELECT profile_json, updated_at FROM profile_current WHERE user_id = ? LIMIT 1",
            (selected_user,),
        )
        if profile_err or profile_df.empty:
            profile_obj = {
                "learning_goal": "考研英语",
                "preferred_style": "简洁分步骤",
                "weak_subject": "阅读",
                "emotion_state": "anxious",
                "knowledge_level": "intermediate",
                "recent_focus": "真题错题复盘",
            }
            st.caption("画像数据缺失，展示默认结构。")
            updated_at = "N/A"
        else:
            row = profile_df.iloc[0]
            try:
                profile_obj = json.loads(row["profile_json"])
            except Exception:
                profile_obj = {"raw_profile_json": row["profile_json"]}
            updated_at = row.get("updated_at", "N/A")

        preferred_order = [
            "learning_goal", "preferred_style", "weak_subject",
            "emotion_state", "knowledge_level", "recent_focus",
        ]
        ordered_items = []
        for field in preferred_order:
            if field in profile_obj:
                ordered_items.append((field, profile_obj[field]))
        for k, v in profile_obj.items():
            if k not in preferred_order:
                ordered_items.append((k, v))

        render_profile_constellation(st, ordered_items)
        st.caption(f"更新时间：{updated_at}")

        latest_result = st.session_state.latest_result if isinstance(st.session_state.latest_result, dict) else {}
        memory_evolution = latest_result.get("memory_evolution", []) if isinstance(latest_result.get("memory_evolution"), list) else []
        profile_updates = latest_result.get("profile_updates", []) if isinstance(latest_result.get("profile_updates"), list) else []

        evolution_preview_rows: list[dict[str, Any]] = []
        for item in profile_updates:
            if not isinstance(item, dict):
                continue
            evolution_preview_rows.append(
                {
                    "field": item.get("field", ""),
                    "old_value": item.get("old_value", ""),
                    "new_value": item.get("new_value", ""),
                    "applied": bool(item.get("applied")),
                    "confidence": item.get("confidence", ""),
                }
            )
        for item in memory_evolution:
            if not isinstance(item, dict):
                continue
            evolution_preview_rows.append(
                {
                    "field": item.get("field", ""),
                    "old_value": item.get("old_value", ""),
                    "new_value": item.get("new_value", ""),
                    "applied": item.get("conflict", ""),
                    "confidence": item.get("reason", ""),
                }
            )
        if evolution_preview_rows:
            render_panel_title(st, "本轮演化轨迹", "本轮对话触发的画像/记忆变化")
            st.dataframe(pd.DataFrame(evolution_preview_rows), width="stretch", hide_index=True)

        render_panel_title(st, "画像变化记录", "最近 12 条画像变更事件")
        history_df, history_err = safe_query(
            PROFILE_DB,
            """
            SELECT user_id, field, old_value, new_value, confidence, changed_at
            FROM profile_history
            ORDER BY changed_at DESC
            LIMIT 12
            """,
        )
        if history_err:
            st.info(f"profile_history 读取失败：{history_err}")
        else:
            st.dataframe(history_df, width="stretch", hide_index=True)
            if not history_df.empty and "field" in history_df.columns:
                field_count_df = history_df["field"].value_counts().rename_axis("field").reset_index(name="count")
                st.caption("画像字段演化频次（最近 12 条）")
                st.bar_chart(field_count_df.set_index("field"))

            timeline_render_df = history_df.copy()
            if not timeline_render_df.empty and "changed_at" in timeline_render_df.columns:
                timeline_render_df = timeline_render_df.iloc[::-1]
                timeline_html = '<div class="evolution-timeline">'
                for _, row in timeline_render_df.iterrows():
                    field = str(row.get("field", ""))
                    old_v = str(row.get("old_value", ""))
                    new_v = str(row.get("new_value", ""))
                    changed_at = str(row.get("changed_at", ""))
                    timeline_html += (
                        '<div class="timeline-item">'
                        f'<div class="timeline-time">{changed_at}</div>'
                        f'<div class="timeline-body"><b>{field}</b>：{old_v} → {new_v}</div>'
                        "</div>"
                    )
                timeline_html += "</div>"
                render_panel_title(st, "画像演化时间轴", "按 changed_at 连续展示字段迁移轨迹")
                st.markdown(timeline_html, unsafe_allow_html=True)

    elif active_observation_page == "capability":
        render_observation_header(
            st,
            eyebrow="System Capability",
            title="系统能力",
            subtitle="把编排链路拆开观察：短期记忆、长期检索、情绪感知、画像演化和工具调用是否协同工作。",
            chips=["STM/LTM", "情绪", "画像演化", "工具调用"],
        )
        latest = st.session_state.latest_result if isinstance(st.session_state.latest_result, dict) else {}
        retrieval = latest.get("retrieval", {}) if isinstance(latest.get("retrieval"), dict) else {}
        profile_updates = latest.get("profile_updates", []) if isinstance(latest.get("profile_updates"), list) else []
        memory_evolution = latest.get("memory_evolution", []) if isinstance(latest.get("memory_evolution"), list) else []
        emotion = latest.get("emotion", {}) if isinstance(latest.get("emotion"), dict) else {}
        tool_output = latest.get("tool_output")
        stm_data = latest.get("stm")

        render_panel_title(st, "能力观测总览", "长短期记忆协同 / 画像演化 / 衰减检索 / 情绪风格 / 工具调用")
        stm_count = len(stm_data) if isinstance(stm_data, list) else (1 if stm_data else 0)
        ltm_count = len(retrieval.get("hits", [])) if isinstance(retrieval.get("hits"), list) else 0
        render_capability_map(
            st,
            {
                "stm": stm_count,
                "ltm": ltm_count,
                "profile": len(profile_updates),
                "evolution": len(memory_evolution),
                "emotion": 1 if emotion else 0,
                "tool": 1 if tool_output else 0,
            },
        )

        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.subheader("长短期记忆协同")
            if stm_data:
                st.caption("STM（近期上下文）")
                st.write(stm_data)
            else:
                st.caption("STM 暂无内容")
            if retrieval.get("hits"):
                st.caption("LTM Top Hits")
                ltm_preview = [
                    {
                        "type": h.get("type", ""),
                        "content": str(h.get("content", ""))[:120],
                        "decayed_score": h.get("decayed_score", 0),
                    }
                    for h in retrieval.get("hits", [])[:5]
                    if isinstance(h, dict)
                ]
                st.dataframe(pd.DataFrame(ltm_preview), width="stretch", hide_index=True)
            else:
                st.caption("LTM 暂无命中")

        with c2:
            st.subheader("情绪感知与风格调节")
            if emotion:
                st.write(
                    {
                        "emotion_label": emotion.get("label"),
                        "confidence": emotion.get("confidence"),
                        "suggested_tone": emotion.get("tone"),
                    }
                )
            else:
                st.caption("暂无情绪分析结果")
            style_updates = [u for u in profile_updates if isinstance(u, dict) and u.get("field") == "preferred_style"]
            if style_updates:
                st.caption("本轮风格调节")
                st.dataframe(pd.DataFrame(style_updates), width="stretch", hide_index=True)
            else:
                st.caption("本轮无风格字段变更")

        st.subheader("工具调用能力")
        task_mode = latest.get("task_mode", st.session_state.task_mode)
        st.caption(f"当前任务模式：{task_mode}")
        if tool_output:
            st.json(tool_output)
        else:
            st.caption("当前轮未触发额外工具输出（可切换侧边栏任务模式为“学习计划/复习建议”）。")

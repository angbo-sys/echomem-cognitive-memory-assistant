from __future__ import annotations

from html import escape
from typing import Any


__all__ = [
    "render_panel_title",
    "render_capability_map",
    "render_hit_card",
    "render_memory_framework_lab",
    "render_memory_composition",
    "render_masthead",
    "render_observation_header",
    "render_profile_constellation",
]


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def render_panel_title(st: Any, title: str, subtitle: str = "") -> None:
    """Render a reusable panel title block.

    Keeps compatibility with existing `.panel` / `.panel-subtitle` styles.
    """
    safe_title = escape(str(title))
    safe_subtitle = escape(str(subtitle)) if subtitle else ""
    subtitle_html = f'<div class="panel-subtitle">{safe_subtitle}</div>' if safe_subtitle else ""
    st.markdown(f'<div class="panel"><h3>{safe_title}</h3>{subtitle_html}</div>', unsafe_allow_html=True)


def render_hit_card(
    st: Any,
    hit: dict[str, Any],
    index: int,
    backend: str,
    s_filter: str,
    t_filter: str,
) -> None:
    """Render one retrieval hit card with consistent metric hierarchy."""
    raw_content = str(hit.get("content", "") or "")
    content = escape(raw_content)
    preview = escape(raw_content[:72])
    ellipsis = "…" if len(raw_content) > 72 else ""

    sim = _to_float(hit.get("similarity", 0.0))
    imp = _to_float(hit.get("importance", 0.0))
    dsc = _to_float(hit.get("decayed_score", 0.0))

    safe_backend = escape(str(backend or "unknown"))
    safe_status = escape(str(s_filter or "active"))
    safe_type = escape(str(t_filter or "all"))

    st.markdown(
        f"""
        <div class="hit-card">
          <div class="hit-head">
            <span class="hit-index">#{index}</span>
            <span class="hit-content-preview">{preview}{ellipsis}</span>
            <span class="hit-backend">{safe_backend}</span>
          </div>
          <div class="hit-body">{content}</div>
          <div class="hit-metrics">
            <span class="metric"><span class="metric-label">SIM</span> {sim:.3f}</span>
            <span class="metric"><span class="metric-label">IMP</span> {imp:.3f}</span>
            <span class="metric"><span class="metric-label">DSC</span> {dsc:.3f}</span>
          </div>
          <div class="hit-filter">status={safe_status} · type={safe_type}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _short_text(value: Any, limit: int = 64) -> str:
    text = str(value or "").strip()
    return text if len(text) <= limit else f"{text[:limit]}…"


def render_memory_composition(st: Any, rows: list[dict[str, Any]]) -> None:
    """Render memory table statistics as a visual composition map."""
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        count = int(_to_float(row.get("count", 0), 0))
        normalized.append(
            {
                "type": str(row.get("type", "unknown") or "unknown"),
                "status": str(row.get("status", "unknown") or "unknown"),
                "count": count,
                "avg_importance": _to_float(row.get("avg_importance", 0.0), 0.0),
            }
        )
    if not normalized:
        normalized = [{"type": "empty", "status": "none", "count": 0, "avg_importance": 0.0}]

    max_count = max(1, max(item["count"] for item in normalized))
    total = sum(item["count"] for item in normalized)
    active = sum(item["count"] for item in normalized if item["status"] == "active")
    avg_importance = sum(item["avg_importance"] for item in normalized) / max(1, len(normalized))

    cards = ""
    for item in normalized[:8]:
        width = max(8, int(item["count"] / max_count * 100)) if item["count"] else 8
        status_class = "active" if item["status"] == "active" else "muted"
        cards += f"""
        <article class="memory-composition-card {status_class}">
          <div class="memory-composition-top">
            <span>{escape(item["type"])}</span>
            <strong>{item["count"]}</strong>
          </div>
          <div class="memory-composition-status">{escape(item["status"])}</div>
          <div class="memory-composition-bar"><div style="width:{width}%"></div></div>
          <div class="memory-composition-foot">importance {item["avg_importance"]:.2f}</div>
        </article>
        """

    st.markdown(
        f"""
        <section class="memory-composition-shell">
          <div class="memory-composition-summary">
            <div><span>总记忆</span><strong>{total}</strong></div>
            <div><span>活跃</span><strong>{active}</strong></div>
            <div><span>平均重要性</span><strong>{avg_importance:.2f}</strong></div>
          </div>
          <div class="memory-composition-grid">{cards}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_profile_constellation(st: Any, items: list[tuple[str, Any]]) -> None:
    """Render user profile fields as a constellation of identity cards."""
    icon_map = {
        "learning_goal": "目标",
        "preferred_style": "风格",
        "weak_subject": "薄弱",
        "emotion_state": "情绪",
        "knowledge_level": "水平",
        "recent_focus": "焦点",
    }
    cards = ""
    for index, (key, value) in enumerate(items):
        label = icon_map.get(str(key), "字段")
        cards += f"""
        <article class="profile-orbit-card" style="--orbit-delay:{index * 55}ms;">
          <div class="profile-orbit-label">{escape(label)}</div>
          <div class="profile-orbit-key">{escape(str(key))}</div>
          <div class="profile-orbit-value">{escape(_short_text(value, 96))}</div>
        </article>
        """
    if not cards:
        cards = """
        <article class="profile-orbit-card">
          <div class="profile-orbit-label">空</div>
          <div class="profile-orbit-key">profile</div>
          <div class="profile-orbit-value">暂无画像字段</div>
        </article>
        """

    st.markdown(
        f"""
        <section class="profile-constellation">
          <div class="profile-constellation-core">
            <span>USER</span>
            <strong>Profile</strong>
          </div>
          <div class="profile-orbit-grid">{cards}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_capability_map(st: Any, metrics: dict[str, Any]) -> None:
    """Render orchestration capability status as a visual system map."""
    nodes = [
        ("STM", "短期上下文", int(_to_float(metrics.get("stm", 0), 0))),
        ("LTM", "长期检索", int(_to_float(metrics.get("ltm", 0), 0))),
        ("Profile", "画像更新", int(_to_float(metrics.get("profile", 0), 0))),
        ("Evolution", "记忆演化", int(_to_float(metrics.get("evolution", 0), 0))),
        ("Emotion", "情绪风格", int(_to_float(metrics.get("emotion", 0), 0))),
        ("Tool", "工具调用", int(_to_float(metrics.get("tool", 0), 0))),
    ]
    node_html = ""
    for index, (name, label, value) in enumerate(nodes):
        state = "active" if value else "idle"
        node_html += f"""
        <article class="capability-node {state}" style="--cap-delay:{index * 45}ms;">
          <div class="capability-node-name">{escape(name)}</div>
          <div class="capability-node-value">{value}</div>
          <div class="capability-node-label">{escape(label)}</div>
        </article>
        """

    st.markdown(
        f"""
        <section class="capability-map">
          <div class="capability-map-rail">
            <span>输入</span><span>记忆</span><span>画像</span><span>回复</span>
          </div>
          <div class="capability-node-grid">{node_html}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _display_framework_name(name: str) -> str:
    labels = {
        "mem0": "Mem0",
        "llamaindex_memory": "LlamaIndex",
        "llamaindex": "LlamaIndex",
        "cognee": "Cognee",
    }
    return labels.get(name, name or "Unknown")


def _framework_mark(name: str) -> str:
    marks = {
        "mem0": "M0",
        "llamaindex_memory": "LI",
        "llamaindex": "LI",
        "cognee": "CG",
    }
    return marks.get(name, "--")


def _framework_fallback_contributions(osm: dict[str, Any]) -> list[dict[str, Any]]:
    mem0 = osm.get("mem0", {}) if isinstance(osm.get("mem0"), dict) else {}
    llama = osm.get("llamaindex_memory", {}) if isinstance(osm.get("llamaindex_memory"), dict) else {}
    cognee = osm.get("cognee", {}) if isinstance(osm.get("cognee"), dict) else {}
    return [
        {
            "framework": "mem0",
            "role": "用户偏好/画像事实",
            "signal_source": mem0.get("signal_source", "unknown"),
            "signal_count": len(_as_list(mem0.get("facts"))),
            "signals": _as_list(mem0.get("facts")),
        },
        {
            "framework": "llamaindex_memory",
            "role": "文档/会话知识命中",
            "signal_source": llama.get("signal_source", "unknown"),
            "signal_count": len(_as_list(llama.get("doc_hits"))),
            "signals": _as_list(llama.get("doc_hits")),
        },
        {
            "framework": "cognee",
            "role": "知识图谱关联概念",
            "signal_source": cognee.get("signal_source", "unknown"),
            "signal_count": len(_as_list(cognee.get("related_concepts"))),
            "signals": _as_list(cognee.get("related_concepts")),
        },
    ]


def render_memory_framework_lab(st: Any, osm: dict[str, Any]) -> None:
    """Render the open-source memory framework observatory as visual lanes."""
    if not isinstance(osm, dict):
        return

    contributions = _as_list(osm.get("framework_contributions")) or _framework_fallback_contributions(osm)
    writes = osm.get("framework_writes", {}) if isinstance(osm.get("framework_writes"), dict) else {}
    expansion = _as_list(osm.get("query_expansion"))
    scenario_obj = osm.get("scenario_routing", {}) if isinstance(osm.get("scenario_routing"), dict) else {}
    scenario = escape(str(scenario_obj.get("scenario", "general")))

    normalized: list[dict[str, Any]] = []
    max_count = 1
    stored_count = 0
    for raw in contributions:
        if not isinstance(raw, dict):
            continue
        framework = str(raw.get("framework", ""))
        signals = [str(item) for item in _as_list(raw.get("signals")) if str(item).strip()]
        signal_count = int(_to_float(raw.get("signal_count", len(signals)), 0.0))
        signal_count = max(signal_count, len(signals))
        write_info = writes.get(framework, {}) if isinstance(writes.get(framework), dict) else {}
        stored = bool(write_info.get("stored"))
        stored_count += 1 if stored else 0
        max_count = max(max_count, signal_count)
        normalized.append(
            {
                "framework": framework,
                "label": _display_framework_name(framework),
                "mark": _framework_mark(framework),
                "role": str(raw.get("role", "")),
                "source": str(raw.get("signal_source", "unknown")),
                "signal_count": signal_count,
                "signals": signals,
                "stored": stored,
            }
        )

    summary_html = f"""
    <section class="memory-lab-shell">
      <div class="memory-lab-head">
        <div>
          <div class="memory-lab-kicker">Framework Signal Lab</div>
          <div class="memory-lab-title">三条记忆通道正在协同</div>
          <div class="memory-lab-sub">把偏好事实、会话知识与图谱关联拆开看，再合并进 Prompt 与写回链路。</div>
        </div>
        <div class="memory-lab-meters">
          <div class="memory-lab-meter"><span>场景</span><strong>{scenario}</strong></div>
          <div class="memory-lab-meter"><span>扩展词</span><strong>{len(expansion)}</strong></div>
          <div class="memory-lab-meter"><span>写回</span><strong>{stored_count}/{len(normalized) or 3}</strong></div>
        </div>
      </div>
    """

    lanes_html = '<div class="memory-lane-grid">'
    for index, item in enumerate(normalized[:3]):
        percent = min(100, max(8, int((item["signal_count"] / max_count) * 100))) if item["signal_count"] else 8
        state_label = "已写回" if item["stored"] else "待写回"
        state_class = "stored" if item["stored"] else "pending"
        safe_framework = escape(str(item["framework"]))
        signal_chips = ""
        for signal in item["signals"][:4]:
            signal_chips += f'<span class="memory-signal-chip">{escape(signal[:64])}</span>'
        if not signal_chips:
            signal_chips = '<span class="memory-signal-chip muted">暂无命中信号</span>'
        lanes_html += f"""
        <article class="memory-lane lane-{safe_framework}" style="--lane-delay:{index * 80}ms;">
          <div class="memory-lane-top">
            <div class="memory-lane-mark">{escape(item["mark"])}</div>
            <div>
              <div class="memory-lane-name">{escape(item["label"])}</div>
              <div class="memory-lane-role">{escape(item["role"])}</div>
            </div>
            <div class="memory-write-state {state_class}">{state_label}</div>
          </div>
          <div class="memory-intensity">
            <div class="memory-intensity-meta">
              <span>信号强度</span>
              <strong>{item["signal_count"]}</strong>
            </div>
            <div class="memory-intensity-track"><div style="width:{percent}%"></div></div>
          </div>
          <div class="memory-source-line">source={escape(item["source"])}</div>
          <div class="memory-signal-cloud">{signal_chips}</div>
        </article>
        """
    lanes_html += "</div>"

    flow_html = """
      <div class="memory-flow">
        <div class="memory-flow-node">用户输入</div>
        <div class="memory-flow-line"></div>
        <div class="memory-flow-node wide">三框架观察</div>
        <div class="memory-flow-line"></div>
        <div class="memory-flow-node">Prompt/UI</div>
        <div class="memory-flow-line"></div>
        <div class="memory-flow-node">对话写回</div>
      </div>
    """

    expansion_html = ""
    if expansion:
        chips = "".join(f'<span class="query-chip">{escape(str(item)[:48])}</span>' for item in expansion[:12])
        expansion_html = f"""
        <div class="query-expansion-board">
          <div class="query-expansion-title">查询扩展胶囊</div>
          <div class="query-expansion-chips">{chips}</div>
        </div>
        """

    st.markdown(summary_html + lanes_html + flow_html + expansion_html + "</section>", unsafe_allow_html=True)


def render_observation_header(
    st: Any,
    *,
    eyebrow: str,
    title: str,
    subtitle: str,
    chips: list[str] | None = None,
) -> None:
    """Render a page-level header for one focused observatory page."""
    safe_eyebrow = escape(str(eyebrow))
    safe_title = escape(str(title))
    safe_subtitle = escape(str(subtitle))
    chip_html = ""
    if chips:
        chip_html = '<div class="observation-header-chips">'
        for chip in chips[:6]:
            chip_html += f'<span>{escape(str(chip))}</span>'
        chip_html += "</div>"

    st.markdown(
        f"""
        <section class="observation-header">
          <div>
            <div class="observation-eyebrow">{safe_eyebrow}</div>
            <div class="observation-title">{safe_title}</div>
            <div class="observation-subtitle">{safe_subtitle}</div>
          </div>
          {chip_html}
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_masthead(
    st: Any,
    provider: str,
    model: str,
    retrieval_backend: str,
    api_mode: str,
) -> None:
    """Render dashboard masthead with primary title and runtime status."""
    safe_provider = escape(str(provider or "unknown"))
    safe_model = escape(str(model or "unknown"))
    safe_backend = escape(str(retrieval_backend or "unknown"))
    safe_api_mode = escape(str(api_mode or "unknown"))

    st.markdown(
        f"""
        <div class="masthead">
          <div class="hero">
            <div class="hero-kicker">EchoMem Control Room</div>
            <div class="hero-title">EchoMem 认知观测台</div>
            <div class="hero-sub">长期记忆 · 画像演化 · 检索信号 · 编排决策可解释</div>
          </div>
          <div class="status-stack">
            <div class="status-row"><div class="status-key">Provider</div><div class="status-value">{safe_provider}</div></div>
            <div class="status-row"><div class="status-key">Model</div><div class="status-value">{safe_model}</div></div>
            <div class="status-row"><div class="status-key">Retrieval</div><div class="status-value">{safe_backend}</div></div>
            <div class="status-row"><div class="status-key">Auth</div><div class="status-value">{safe_api_mode}</div></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

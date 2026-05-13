"""EchoMem Streamlit UI theme injector."""

from __future__ import annotations

import streamlit as st


THEME_CSS = """
<style>
  :root {
    --paper: #f4efe4;
    --paper-2: #fffaf0;
    --ink: #171a20;
    --ink-soft: #4d5666;
    --ink-muted: #7b8494;
    --clay: #b94722;
    --clay-soft: rgba(185, 71, 34, 0.12);
    --teal: #006d77;
    --teal-soft: rgba(0, 109, 119, 0.13);
    --gold: #d79a2b;
    --line: rgba(32, 37, 48, 0.14);
    --line-strong: rgba(32, 37, 48, 0.24);
    --glass: rgba(255, 250, 240, 0.78);
    --shadow: 0 22px 70px rgba(50, 41, 28, 0.13);
    --shadow-soft: 0 10px 30px rgba(50, 41, 28, 0.08);
    --radius: 18px;
    --radius-sm: 12px;
    --serif: "Songti SC", "STSong", "Noto Serif CJK SC", Georgia, serif;
    --sans: "Avenir Next", "Gill Sans", "Trebuchet MS", sans-serif;
    --mono: "SF Mono", "Menlo", "Consolas", monospace;
  }

  .stApp {
    color: var(--ink);
    background:
      radial-gradient(circle at 8% 6%, rgba(215, 154, 43, 0.22), transparent 28rem),
      radial-gradient(circle at 92% 12%, rgba(0, 109, 119, 0.16), transparent 26rem),
      linear-gradient(135deg, #f8f0df 0%, #f1eadf 45%, #e8efe9 100%);
  }

  .stApp::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    opacity: 0.28;
    background-image:
      linear-gradient(rgba(23, 26, 32, 0.035) 1px, transparent 1px),
      linear-gradient(90deg, rgba(23, 26, 32, 0.035) 1px, transparent 1px);
    background-size: 34px 34px;
    mask-image: linear-gradient(to bottom, black, transparent 82%);
  }

  [data-testid="stAppViewContainer"],
  [data-testid="stMain"],
  [data-testid="stMainBlockContainer"] {
    min-width: 0 !important;
  }

  .block-container {
    width: min(100%, 1360px) !important;
    max-width: 1360px !important;
    padding: clamp(1rem, 2vw, 2.2rem) clamp(0.9rem, 2.4vw, 2.6rem) 7rem !important;
    position: relative;
    z-index: 1;
  }

  .stApp p,
  .stApp span,
  .stApp label,
  .stApp li,
  .stApp td,
  .stApp th,
  .stApp div {
    font-family: var(--serif);
  }

  .stApp h1,
  .stApp h2,
  .stApp h3,
  .stApp h4,
  .stApp button,
  .stApp [role="tab"],
  .stApp [data-testid="stMetricLabel"],
  .stApp [data-testid="stMetricValue"] {
    font-family: var(--sans) !important;
  }

  header[data-testid="stHeader"] {
    background: transparent !important;
  }

  section[data-testid="stSidebar"] {
    background:
      radial-gradient(circle at top left, rgba(215, 154, 43, 0.18), transparent 15rem),
      linear-gradient(180deg, #14202a 0%, #0e161f 100%) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.12) !important;
    box-shadow: 18px 0 50px rgba(8, 13, 18, 0.18);
  }

  section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
    padding-top: 1rem;
  }

  section[data-testid="stSidebar"] h3,
  section[data-testid="stSidebar"] p,
  section[data-testid="stSidebar"] span,
  section[data-testid="stSidebar"] label,
  section[data-testid="stSidebar"] div {
    color: #edf3ee !important;
  }

  section[data-testid="stSidebar"] h3 {
    margin-top: 0.7rem !important;
    color: #f8e7b7 !important;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    font-size: 0.78rem !important;
  }

  section[data-testid="stSidebar"] hr {
    border-color: rgba(255, 255, 255, 0.12) !important;
    margin: 0.85rem 0 !important;
  }

  section[data-testid="stSidebar"] [data-baseweb="select"] > div,
  section[data-testid="stSidebar"] input,
  section[data-testid="stSidebar"] textarea {
    background: rgba(255, 255, 255, 0.08) !important;
    border-color: rgba(255, 255, 255, 0.16) !important;
    border-radius: 12px !important;
  }

  section[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    border-radius: 999px !important;
    border: 1px solid rgba(248, 231, 183, 0.25) !important;
    background: rgba(248, 231, 183, 0.08) !important;
    color: #fff8df !important;
  }

  section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(248, 231, 183, 0.16) !important;
    border-color: rgba(248, 231, 183, 0.44) !important;
  }

  .chat-page-header,
  .masthead,
  .observation-header,
  .panel,
  .welcome-card,
  .hit-card,
  .kpi-card,
  .framework-card,
  .memory-lab-shell,
  .memory-lane,
  .memory-composition-shell,
  .memory-composition-card,
  .profile-constellation,
  .profile-orbit-card,
  .capability-map,
  .capability-node,
  .profile-field,
  [data-testid="stChatMessage"],
  [data-testid="stAlert"] {
    backdrop-filter: blur(14px);
  }

  .chat-page-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1rem;
    margin: 0 0 1rem;
    padding: 1.1rem 1.2rem;
    border: 1px solid var(--line);
    border-radius: calc(var(--radius) + 4px);
    background: linear-gradient(135deg, rgba(255, 250, 240, 0.88), rgba(232, 239, 233, 0.78));
    box-shadow: var(--shadow-soft);
  }

  .chat-page-title {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    font-size: clamp(1.55rem, 3.2vw, 2.35rem);
    font-weight: 850;
    letter-spacing: -0.05em;
    color: var(--ink);
  }

  .observation-header {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 1rem;
    align-items: end;
    margin: 0 0 1rem;
    padding: 1rem 1.1rem;
    border: 1px solid var(--line);
    border-radius: calc(var(--radius) + 4px);
    background:
      radial-gradient(circle at 8% 0%, rgba(215, 154, 43, 0.16), transparent 16rem),
      linear-gradient(135deg, rgba(255, 250, 240, 0.86), rgba(232, 239, 233, 0.7));
    box-shadow: var(--shadow-soft);
  }

  .observation-eyebrow {
    color: var(--teal);
    font-family: var(--mono) !important;
    font-size: 0.72rem;
    font-weight: 900;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .observation-title {
    margin-top: 0.1rem;
    color: var(--ink);
    font-family: var(--sans) !important;
    font-size: clamp(1.55rem, 3vw, 2.35rem);
    font-weight: 950;
    letter-spacing: -0.055em;
  }

  .observation-subtitle {
    max-width: 50rem;
    margin-top: 0.22rem;
    color: var(--ink-soft);
    line-height: 1.65;
  }

  .observation-header-chips {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 0.4rem;
  }

  .observation-header-chips span {
    border: 1px solid rgba(0, 109, 119, 0.18);
    border-radius: 999px;
    padding: 0.25rem 0.62rem;
    background: rgba(255, 250, 240, 0.72);
    color: var(--ink-soft);
    font-size: 0.75rem;
    font-weight: 800;
    white-space: nowrap;
  }

  .chat-page-dot {
    width: 0.8rem;
    height: 0.8rem;
    border-radius: 999px;
    background: var(--teal);
    box-shadow: 0 0 0 7px var(--teal-soft), 0 0 28px rgba(0, 109, 119, 0.45);
  }

  .chat-page-meta {
    color: var(--ink-muted);
    font-family: var(--sans) !important;
    font-size: 0.85rem;
    white-space: nowrap;
  }

  .welcome-card {
    position: relative;
    overflow: hidden;
    border: 1px solid var(--line);
    border-radius: calc(var(--radius) + 8px);
    padding: clamp(1.2rem, 4vw, 2.3rem);
    margin-bottom: 1rem;
    background:
      linear-gradient(135deg, rgba(255, 250, 240, 0.94), rgba(255, 247, 224, 0.76)),
      radial-gradient(circle at 100% 0%, rgba(185, 71, 34, 0.18), transparent 18rem);
    box-shadow: var(--shadow);
  }

  .welcome-card::after {
    content: "MEMORY / SIGNAL / STYLE";
    position: absolute;
    right: -1rem;
    bottom: 0.4rem;
    font-family: var(--sans);
    font-weight: 900;
    letter-spacing: 0.18em;
    font-size: clamp(1.2rem, 5vw, 3.8rem);
    color: rgba(23, 26, 32, 0.045);
    white-space: nowrap;
  }

  .welcome-greeting {
    position: relative;
    z-index: 1;
    max-width: 56rem;
    color: var(--ink);
    font-size: clamp(1rem, 1.6vw, 1.24rem);
    line-height: 1.85;
    font-weight: 650;
  }

  .welcome-hint {
    position: relative;
    z-index: 1;
    margin-top: 1rem;
    font-family: var(--sans) !important;
    color: var(--teal);
    font-size: 0.75rem;
    font-weight: 850;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  .stButton > button {
    min-height: 2.8rem;
    border-radius: 16px !important;
    border: 1px solid var(--line) !important;
    background: rgba(255, 250, 240, 0.72) !important;
    color: var(--ink) !important;
    box-shadow: 0 6px 18px rgba(50, 41, 28, 0.06) !important;
    transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease !important;
    white-space: normal !important;
  }

  .stButton > button:hover {
    transform: translateY(-1px);
    border-color: rgba(0, 109, 119, 0.45) !important;
    box-shadow: 0 14px 28px rgba(0, 109, 119, 0.1) !important;
    color: var(--teal) !important;
  }

  [data-testid="stHorizontalBlock"] {
    gap: clamp(0.75rem, 1.6vw, 1.2rem) !important;
  }

  [data-testid="column"] {
    min-width: 0 !important;
  }

  [data-testid="stChatMessage"] {
    border: 1px solid var(--line) !important;
    border-radius: 22px !important;
    padding: 0.85rem 1rem !important;
    margin: 0.8rem 0 !important;
    max-width: min(820px, 92%) !important;
    background: rgba(255, 250, 240, 0.82) !important;
    box-shadow: var(--shadow-soft) !important;
    animation: rise 260ms ease both;
  }

  [data-testid="stChatMessage"] p,
  [data-testid="stChatMessage"] li {
    color: var(--ink) !important;
    font-size: clamp(0.96rem, 1.6vw, 1.06rem) !important;
    line-height: 1.75 !important;
  }

  [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    margin-left: auto !important;
    background: linear-gradient(135deg, rgba(255, 245, 229, 0.92), rgba(255, 250, 240, 0.82)) !important;
    border-color: rgba(185, 71, 34, 0.22) !important;
  }

  [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    margin-right: auto !important;
    background: linear-gradient(135deg, rgba(234, 247, 244, 0.92), rgba(255, 250, 240, 0.82)) !important;
    border-color: rgba(0, 109, 119, 0.22) !important;
  }

  [data-testid="stChatMessageAvatarUser"],
  [data-testid="stChatMessageAvatarAssistant"] {
    border-radius: 999px !important;
  }

  .stChatInput {
    z-index: 20 !important;
  }

  .stChatInput [data-baseweb="base-input"] {
    border: 1px solid var(--line-strong) !important;
    border-radius: 20px !important;
    background: rgba(255, 250, 240, 0.92) !important;
    box-shadow: 0 18px 45px rgba(50, 41, 28, 0.16) !important;
  }

  .stChatInput [data-baseweb="base-input"]:focus-within {
    border-color: rgba(0, 109, 119, 0.55) !important;
    box-shadow: 0 0 0 5px var(--teal-soft), 0 18px 45px rgba(50, 41, 28, 0.16) !important;
  }

  .stChatInput textarea,
  .stChatInput input,
  .stChatInput [data-baseweb="base-input"] * {
    color: var(--ink) !important;
    font-family: var(--serif) !important;
    font-size: 1rem !important;
  }

  .masthead {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(250px, 360px);
    gap: 1rem;
    margin-bottom: 1rem;
  }

  .hero,
  .status-stack,
  .panel,
  .kpi-card,
  .framework-card,
  .profile-field {
    border: 1px solid var(--line);
    background: var(--glass);
    box-shadow: var(--shadow-soft);
  }

  .hero {
    overflow: hidden;
    position: relative;
    border-radius: calc(var(--radius) + 10px);
    padding: clamp(1.2rem, 3vw, 2rem);
  }

  .hero::before {
    content: "";
    position: absolute;
    width: 18rem;
    height: 18rem;
    right: -7rem;
    top: -8rem;
    border-radius: 999px;
    background: radial-gradient(circle, rgba(0, 109, 119, 0.2), transparent 68%);
  }

  .hero-kicker,
  .kpi-label,
  .framework-key,
  .profile-field-key,
  .hit-index,
  .hit-backend,
  .metric,
  .status-key,
  .panel-subtitle {
    font-family: var(--sans) !important;
  }

  .hero-kicker {
    position: relative;
    color: var(--teal);
    font-size: 0.75rem;
    font-weight: 900;
    letter-spacing: 0.18em;
    text-transform: uppercase;
  }

  .hero-title {
    position: relative;
    margin-top: 0.4rem;
    color: var(--ink);
    font-family: var(--sans) !important;
    font-size: clamp(2rem, 5vw, 4.4rem);
    line-height: 0.98;
    font-weight: 950;
    letter-spacing: -0.075em;
  }

  .hero-sub {
    position: relative;
    margin-top: 0.8rem;
    color: var(--ink-soft);
    font-size: clamp(0.95rem, 1.5vw, 1.08rem);
  }

  .status-stack {
    display: grid;
    gap: 0.55rem;
    border-radius: var(--radius);
    padding: 0.9rem;
  }

  .status-row {
    display: grid;
    grid-template-columns: 0.82fr 1.18fr;
    overflow: hidden;
    border-radius: 13px;
    border: 1px solid var(--line);
  }

  .status-key {
    padding: 0.55rem 0.7rem;
    background: #18303a;
    color: #f4e9ca;
    font-size: 0.7rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 850;
  }

  .status-value {
    padding: 0.55rem 0.7rem;
    background: rgba(255, 255, 255, 0.42);
    color: var(--ink);
    overflow-wrap: anywhere;
  }

  .panel {
    border-radius: var(--radius);
    padding: 1rem 1.1rem;
    margin: 1rem 0 0.85rem;
  }

  .panel h3 {
    margin: 0;
    color: var(--ink);
    font-size: clamp(1.15rem, 2vw, 1.45rem);
    font-weight: 900;
    letter-spacing: -0.04em;
  }

  .panel-subtitle {
    margin-top: 0.25rem;
    color: var(--ink-muted);
    font-size: 0.82rem;
  }

  .kpi-grid,
  .framework-grid,
  .profile-grid {
    display: grid;
    gap: 0.75rem;
  }

  .kpi-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin-bottom: 0.9rem;
  }

  .framework-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .profile-grid {
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  }

  .kpi-card,
  .framework-card,
  .profile-field,
  .hit-card {
    border-radius: var(--radius-sm);
    transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
  }

  .kpi-card,
  .framework-card,
  .profile-field {
    padding: 0.95rem;
  }

  .kpi-card:hover,
  .framework-card:hover,
  .profile-field:hover,
  .hit-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow);
    border-color: rgba(0, 109, 119, 0.28);
  }

  .kpi-icon {
    font-size: 1.15rem;
  }

  .kpi-label,
  .framework-key,
  .profile-field-key {
    color: var(--ink-muted);
    font-size: 0.7rem;
    font-weight: 850;
    letter-spacing: 0.11em;
    text-transform: uppercase;
  }

  .kpi-value,
  .framework-score {
    color: var(--ink);
    font-family: var(--sans) !important;
    font-weight: 950;
    line-height: 1;
  }

  .kpi-value {
    margin-top: 0.35rem;
    font-size: clamp(1.8rem, 4vw, 2.5rem);
    letter-spacing: -0.06em;
  }

  .kpi-value.accent,
  .framework-score {
    color: var(--clay);
  }

  .kpi-value.accent-2 {
    color: var(--teal);
  }

  .framework-label,
  .profile-field-value {
    margin-top: 0.25rem;
    color: var(--ink-soft);
    overflow-wrap: anywhere;
  }

  .framework-score {
    margin-top: 0.55rem;
    font-size: 2rem;
  }

  .memory-composition-shell {
    position: relative;
    overflow: hidden;
    padding: 0.95rem;
    border: 1px solid var(--line);
    border-radius: calc(var(--radius) + 6px);
    background:
      radial-gradient(circle at 0% 0%, rgba(185, 71, 34, 0.14), transparent 14rem),
      linear-gradient(135deg, rgba(255, 250, 240, 0.84), rgba(232, 239, 233, 0.68));
    box-shadow: var(--shadow-soft);
  }

  .memory-composition-summary {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.55rem;
    margin-bottom: 0.75rem;
  }

  .memory-composition-summary > div {
    border-radius: 16px;
    padding: 0.65rem 0.72rem;
    background: rgba(23, 26, 32, 0.84);
    color: #fff8df;
  }

  .memory-composition-summary span,
  .memory-composition-foot,
  .memory-composition-status {
    color: var(--ink-muted);
    font-size: 0.7rem;
    font-weight: 850;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .memory-composition-summary > div span {
    display: block;
    color: rgba(255, 248, 223, 0.72);
  }

  .memory-composition-summary strong {
    display: block;
    margin-top: 0.15rem;
    font-family: var(--sans) !important;
    font-size: clamp(1.2rem, 2.6vw, 1.85rem);
    line-height: 1;
  }

  .memory-composition-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 0.55rem;
  }

  .memory-composition-card {
    padding: 0.7rem;
    border: 1px solid var(--line);
    border-radius: 16px;
    background: rgba(255, 250, 240, 0.72);
  }

  .memory-composition-card.active {
    border-color: rgba(0, 109, 119, 0.25);
  }

  .memory-composition-card.muted {
    opacity: 0.74;
  }

  .memory-composition-top {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.55rem;
  }

  .memory-composition-top span {
    color: var(--ink);
    font-weight: 900;
    overflow-wrap: anywhere;
  }

  .memory-composition-top strong {
    color: var(--clay);
    font-family: var(--sans) !important;
    font-size: 1.35rem;
    line-height: 1;
  }

  .memory-composition-bar {
    overflow: hidden;
    height: 0.5rem;
    margin: 0.48rem 0;
    border-radius: 999px;
    background: rgba(23, 26, 32, 0.08);
  }

  .memory-composition-bar > div {
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, var(--clay), var(--gold), var(--teal));
  }

  .profile-constellation {
    position: relative;
    display: grid;
    grid-template-columns: minmax(160px, 0.42fr) minmax(0, 1fr);
    gap: 0.9rem;
    align-items: stretch;
    margin-bottom: 0.85rem;
    padding: 0.9rem;
    border: 1px solid var(--line);
    border-radius: calc(var(--radius) + 8px);
    background:
      radial-gradient(circle at 13% 24%, rgba(0, 109, 119, 0.16), transparent 14rem),
      linear-gradient(135deg, rgba(255, 250, 240, 0.84), rgba(255, 247, 224, 0.58));
    box-shadow: var(--shadow-soft);
  }

  .profile-constellation-core {
    display: grid;
    place-items: center;
    min-height: 12rem;
    border-radius: calc(var(--radius) + 2px);
    background: #171a20;
    color: #fff8df;
    text-align: center;
    box-shadow: 0 16px 34px rgba(23, 26, 32, 0.2);
  }

  .profile-constellation-core span {
    display: block;
    color: rgba(255, 248, 223, 0.64);
    font-family: var(--mono) !important;
    font-size: 0.75rem;
    letter-spacing: 0.18em;
  }

  .profile-constellation-core strong {
    display: block;
    font-family: var(--sans) !important;
    font-size: clamp(1.4rem, 3vw, 2.2rem);
    letter-spacing: -0.06em;
  }

  .profile-orbit-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 0.65rem;
  }

  .profile-orbit-card {
    position: relative;
    overflow: hidden;
    padding: 0.78rem;
    border: 1px solid var(--line);
    border-radius: 18px;
    background: rgba(255, 250, 240, 0.74);
    animation: rise 300ms ease both;
    animation-delay: var(--orbit-delay);
  }

  .profile-orbit-card::before {
    content: "";
    position: absolute;
    inset: 0 auto 0 0;
    width: 4px;
    background: linear-gradient(180deg, var(--teal), var(--gold));
  }

  .profile-orbit-label {
    color: var(--teal);
    font-family: var(--sans) !important;
    font-size: 0.76rem;
    font-weight: 950;
  }

  .profile-orbit-key {
    margin-top: 0.12rem;
    color: var(--ink-muted);
    font-family: var(--mono) !important;
    font-size: 0.68rem;
  }

  .profile-orbit-value {
    margin-top: 0.35rem;
    color: var(--ink);
    line-height: 1.55;
    overflow-wrap: anywhere;
  }

  .capability-map {
    position: relative;
    overflow: hidden;
    margin-bottom: 1rem;
    padding: 0.9rem;
    border: 1px solid var(--line);
    border-radius: calc(var(--radius) + 8px);
    background:
      radial-gradient(circle at 92% 10%, rgba(215, 154, 43, 0.16), transparent 14rem),
      linear-gradient(135deg, rgba(255, 250, 240, 0.84), rgba(232, 239, 233, 0.72));
    box-shadow: var(--shadow-soft);
  }

  .capability-map-rail {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.45rem;
    margin-bottom: 0.75rem;
  }

  .capability-map-rail span {
    border-radius: 999px;
    padding: 0.32rem 0.6rem;
    background: rgba(23, 26, 32, 0.84);
    color: #fff8df;
    font-family: var(--sans) !important;
    font-size: 0.72rem;
    font-weight: 850;
    text-align: center;
  }

  .capability-node-grid {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 0.55rem;
  }

  .capability-node {
    padding: 0.78rem 0.62rem;
    border: 1px solid var(--line);
    border-radius: 18px;
    background: rgba(255, 250, 240, 0.72);
    text-align: center;
    animation: rise 300ms ease both;
    animation-delay: var(--cap-delay);
  }

  .capability-node.active {
    border-color: rgba(0, 109, 119, 0.32);
    box-shadow: 0 10px 26px rgba(0, 109, 119, 0.08);
  }

  .capability-node.idle {
    opacity: 0.66;
  }

  .capability-node-name {
    color: var(--ink);
    font-family: var(--sans) !important;
    font-weight: 950;
    letter-spacing: -0.035em;
  }

  .capability-node-value {
    margin-top: 0.2rem;
    color: var(--clay);
    font-family: var(--sans) !important;
    font-size: 1.75rem;
    font-weight: 950;
    line-height: 1;
  }

  .capability-node-label {
    margin-top: 0.22rem;
    color: var(--ink-muted);
    font-size: 0.74rem;
  }

  .memory-lab-shell {
    position: relative;
    overflow: hidden;
    margin: 0.15rem 0 1.15rem;
    padding: clamp(1rem, 2vw, 1.35rem);
    border: 1px solid var(--line);
    border-radius: calc(var(--radius) + 8px);
    background:
      radial-gradient(circle at 7% 10%, rgba(185, 71, 34, 0.16), transparent 17rem),
      radial-gradient(circle at 92% 2%, rgba(0, 109, 119, 0.16), transparent 20rem),
      linear-gradient(135deg, rgba(255, 250, 240, 0.88), rgba(232, 239, 233, 0.72));
    box-shadow: var(--shadow-soft);
  }

  .memory-lab-shell::before {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    opacity: 0.34;
    background-image:
      linear-gradient(90deg, rgba(23, 26, 32, 0.05) 1px, transparent 1px),
      linear-gradient(rgba(23, 26, 32, 0.04) 1px, transparent 1px);
    background-size: 28px 28px;
    mask-image: linear-gradient(120deg, black, transparent 78%);
  }

  .memory-lab-head,
  .memory-lane-grid,
  .memory-flow,
  .query-expansion-board {
    position: relative;
    z-index: 1;
  }

  .memory-lab-head {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 1rem;
    align-items: end;
    margin-bottom: 1rem;
  }

  .memory-lab-kicker,
  .query-expansion-title,
  .memory-source-line {
    color: var(--ink-muted);
    font-family: var(--mono) !important;
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .memory-lab-title {
    margin-top: 0.15rem;
    color: var(--ink);
    font-family: var(--sans) !important;
    font-size: clamp(1.45rem, 3vw, 2.25rem);
    font-weight: 950;
    letter-spacing: -0.055em;
  }

  .memory-lab-sub {
    max-width: 45rem;
    margin-top: 0.25rem;
    color: var(--ink-soft);
    line-height: 1.65;
  }

  .memory-lab-meters {
    display: grid;
    grid-template-columns: repeat(3, minmax(5.5rem, auto));
    gap: 0.5rem;
  }

  .memory-lab-meter {
    padding: 0.65rem 0.75rem;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: rgba(255, 250, 240, 0.68);
    box-shadow: 0 8px 24px rgba(50, 41, 28, 0.06);
    white-space: nowrap;
  }

  .memory-lab-meter span {
    display: block;
    color: var(--ink-muted);
    font-size: 0.65rem;
    font-weight: 850;
  }

  .memory-lab-meter strong {
    display: block;
    color: var(--ink);
    font-family: var(--sans) !important;
    font-size: 0.92rem;
    line-height: 1.1;
  }

  .memory-lane-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.85rem;
  }

  .memory-lane {
    position: relative;
    overflow: hidden;
    min-height: 14.5rem;
    padding: 0.9rem;
    border: 1px solid var(--line);
    border-radius: calc(var(--radius-sm) + 6px);
    background: rgba(255, 250, 240, 0.76);
    box-shadow: var(--shadow-soft);
    animation: rise 320ms ease both;
    animation-delay: var(--lane-delay);
  }

  .memory-lane::after {
    content: "";
    position: absolute;
    inset: auto -20% -35% 30%;
    height: 8rem;
    border-radius: 999px;
    background: rgba(0, 109, 119, 0.08);
    filter: blur(2px);
    transform: rotate(-14deg);
  }

  .lane-mem0::before,
  .lane-llamaindex_memory::before,
  .lane-cognee::before {
    content: "";
    position: absolute;
    inset: 0 0 auto;
    height: 4px;
  }

  .lane-mem0::before {
    background: linear-gradient(90deg, var(--clay), #e2a13a);
  }

  .lane-llamaindex_memory::before {
    background: linear-gradient(90deg, var(--teal), #4aa79d);
  }

  .lane-cognee::before {
    background: linear-gradient(90deg, #283b63, var(--gold));
  }

  .memory-lane-top {
    position: relative;
    z-index: 1;
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    gap: 0.65rem;
    align-items: start;
  }

  .memory-lane-mark {
    display: grid;
    place-items: center;
    width: 2.65rem;
    height: 2.65rem;
    border-radius: 16px;
    background: #171a20;
    color: #fff8df;
    font-family: var(--sans) !important;
    font-weight: 950;
    letter-spacing: -0.04em;
    box-shadow: 0 12px 26px rgba(23, 26, 32, 0.18);
  }

  .memory-lane-name {
    color: var(--ink);
    font-family: var(--sans) !important;
    font-size: 1.05rem;
    font-weight: 950;
    letter-spacing: -0.035em;
  }

  .memory-lane-role {
    margin-top: 0.12rem;
    color: var(--ink-soft);
    font-size: 0.78rem;
    line-height: 1.35;
  }

  .memory-write-state {
    border-radius: 999px;
    padding: 0.2rem 0.55rem;
    font-size: 0.68rem;
    font-weight: 900;
    white-space: nowrap;
  }

  .memory-write-state.stored {
    background: var(--teal-soft);
    color: var(--teal);
  }

  .memory-write-state.pending {
    background: rgba(215, 154, 43, 0.16);
    color: #8a5c07;
  }

  .memory-intensity {
    position: relative;
    z-index: 1;
    margin-top: 1rem;
  }

  .memory-intensity-meta {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    color: var(--ink-muted);
    font-size: 0.72rem;
  }

  .memory-intensity-meta strong {
    color: var(--clay);
    font-family: var(--sans) !important;
    font-size: 1.85rem;
    line-height: 1;
  }

  .memory-intensity-track {
    overflow: hidden;
    height: 0.56rem;
    margin-top: 0.35rem;
    border-radius: 999px;
    background: rgba(23, 26, 32, 0.08);
  }

  .memory-intensity-track > div {
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, var(--clay), var(--gold), var(--teal));
    box-shadow: 0 0 24px rgba(215, 154, 43, 0.24);
  }

  .memory-source-line {
    position: relative;
    z-index: 1;
    margin-top: 0.65rem;
    overflow-wrap: anywhere;
  }

  .memory-signal-cloud {
    position: relative;
    z-index: 1;
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-top: 0.75rem;
  }

  .memory-signal-chip,
  .query-chip {
    border: 1px solid rgba(0, 109, 119, 0.18);
    border-radius: 999px;
    padding: 0.25rem 0.55rem;
    background: rgba(255, 250, 240, 0.7);
    color: var(--ink-soft);
    font-size: 0.74rem;
    line-height: 1.35;
    overflow-wrap: anywhere;
  }

  .memory-signal-chip.muted {
    border-style: dashed;
    color: var(--ink-muted);
  }

  .memory-flow {
    display: grid;
    grid-template-columns: auto minmax(1.2rem, 1fr) auto minmax(1.2rem, 1fr) auto minmax(1.2rem, 1fr) auto;
    gap: 0.5rem;
    align-items: center;
    margin: 1rem 0 0.2rem;
  }

  .memory-flow-node {
    border: 1px solid var(--line);
    border-radius: 999px;
    padding: 0.42rem 0.7rem;
    background: rgba(23, 26, 32, 0.84);
    color: #fff8df;
    font-family: var(--sans) !important;
    font-size: 0.76rem;
    font-weight: 850;
    text-align: center;
    white-space: nowrap;
  }

  .memory-flow-node.wide {
    background: linear-gradient(135deg, var(--clay), var(--teal));
  }

  .memory-flow-line {
    height: 2px;
    min-width: 1rem;
    background: linear-gradient(90deg, rgba(185, 71, 34, 0.55), rgba(0, 109, 119, 0.4));
  }

  .query-expansion-board {
    margin-top: 0.9rem;
    padding-top: 0.85rem;
    border-top: 1px dashed var(--line-strong);
  }

  .query-expansion-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-top: 0.45rem;
  }

  .hit-card {
    position: relative;
    overflow: hidden;
    padding: 0.85rem 0.9rem;
    margin-bottom: 0.7rem;
    border: 1px solid var(--line);
    background: rgba(255, 250, 240, 0.82);
    box-shadow: var(--shadow-soft);
  }

  .hit-card::before {
    content: "";
    position: absolute;
    inset: 0 auto 0 0;
    width: 5px;
    background: linear-gradient(180deg, var(--clay), var(--teal));
  }

  .hit-head {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-width: 0;
    padding-left: 0.35rem;
  }

  .hit-index {
    color: var(--clay);
    font-weight: 950;
  }

  .hit-content-preview {
    min-width: 0;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--ink);
    font-weight: 700;
  }

  .hit-backend {
    border-radius: 999px;
    padding: 0.15rem 0.55rem;
    background: var(--teal-soft);
    color: var(--teal);
    font-size: 0.68rem;
    font-weight: 850;
    white-space: nowrap;
  }

  .hit-body,
  .hit-filter {
    padding-left: 0.35rem;
    color: var(--ink-soft);
    overflow-wrap: anywhere;
  }

  .hit-body {
    margin: 0.45rem 0;
    line-height: 1.65;
  }

  .hit-metrics {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    padding-left: 0.35rem;
  }

  .metric {
    border-radius: 999px;
    padding: 0.18rem 0.55rem;
    background: rgba(23, 26, 32, 0.06);
    color: var(--ink-soft);
    font-size: 0.72rem;
  }

  .metric-label {
    color: var(--ink-muted);
    font-size: 0.65rem;
    font-weight: 900;
  }

  .empty-state {
    display: grid;
    place-items: center;
    gap: 0.45rem;
    min-height: 13rem;
    border: 1px dashed var(--line-strong);
    border-radius: var(--radius);
    background: rgba(255, 250, 240, 0.42);
    color: var(--ink-muted);
    text-align: center;
  }

  .empty-state-icon {
    font-size: 2.2rem;
    opacity: 0.7;
  }

  .stTabs [role="tablist"] {
    gap: 0.35rem !important;
    overflow-x: auto !important;
    scrollbar-width: none;
    border-bottom: 1px solid var(--line) !important;
  }

  .stTabs [role="tab"] {
    flex: 0 0 auto !important;
    border: 1px solid var(--line) !important;
    border-bottom: none !important;
    border-radius: 16px 16px 0 0 !important;
    background: rgba(255, 250, 240, 0.55) !important;
    color: var(--ink-soft) !important;
    font-weight: 850 !important;
    letter-spacing: 0.02em !important;
    min-height: 2.7rem !important;
  }

  .stTabs [aria-selected="true"] {
    background: rgba(255, 250, 240, 0.9) !important;
    color: var(--ink) !important;
    box-shadow: var(--shadow-soft) !important;
  }

  [data-testid="stDataFrame"],
  .stDataFrame,
  .stBarChart,
  .stLineChart,
  [data-testid="stVegaLiteChart"] {
    border-radius: var(--radius-sm) !important;
    overflow: hidden !important;
    border: 1px solid var(--line) !important;
    box-shadow: var(--shadow-soft) !important;
    background: rgba(255, 250, 240, 0.68) !important;
  }

  [data-testid="stMetric"] {
    border: 1px solid var(--line);
    border-radius: var(--radius-sm);
    padding: 0.85rem 0.9rem;
    background: rgba(255, 250, 240, 0.72);
    box-shadow: var(--shadow-soft);
  }

  [data-testid="stMetricValue"] {
    color: var(--teal) !important;
    font-weight: 950 !important;
  }

  [data-testid="stAlert"] {
    border-radius: var(--radius-sm) !important;
    border: 1px solid rgba(215, 154, 43, 0.48) !important;
    background: rgba(255, 244, 208, 0.8) !important;
    color: #5f4310 !important;
  }

  [data-testid="stAlert"] * {
    color: #5f4310 !important;
  }

  .evolution-timeline {
    border-left: 2px solid rgba(0, 109, 119, 0.32);
    margin: 0.8rem 0 0.2rem 0.4rem;
    padding-left: 1rem;
  }

  .timeline-item {
    position: relative;
    margin-bottom: 0.75rem;
    padding: 0.65rem 0.8rem;
    border-radius: var(--radius-sm);
    background: rgba(255, 250, 240, 0.68);
    border: 1px solid var(--line);
  }

  .timeline-item::before {
    content: "";
    position: absolute;
    left: -1.35rem;
    top: 0.95rem;
    width: 0.72rem;
    height: 0.72rem;
    border-radius: 999px;
    background: var(--teal);
    box-shadow: 0 0 0 5px var(--teal-soft);
  }

  .timeline-time {
    font-family: var(--mono) !important;
    color: var(--ink-muted);
    font-size: 0.76rem;
  }

  .timeline-body {
    margin-top: 0.2rem;
    color: var(--ink);
    line-height: 1.6;
    overflow-wrap: anywhere;
  }

  @keyframes rise {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }

  @media (max-width: 980px) {
    .masthead {
      grid-template-columns: 1fr;
    }
    .observation-header {
      grid-template-columns: 1fr;
    }
    .observation-header-chips {
      justify-content: flex-start;
    }
    .kpi-grid,
    .framework-grid,
    .memory-lane-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .profile-constellation {
      grid-template-columns: 1fr;
    }
    .capability-node-grid {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
    .memory-lab-head {
      grid-template-columns: 1fr;
    }
    .memory-lab-meters {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
    [data-testid="stHorizontalBlock"] {
      flex-wrap: wrap !important;
    }
    [data-testid="stHorizontalBlock"] > [data-testid="column"] {
      min-width: min(100%, 300px) !important;
      flex: 1 1 300px !important;
    }
  }

  @media (max-width: 720px) {
    .block-container {
      padding: 0.75rem 0.72rem 7rem !important;
    }
    .chat-page-header {
      align-items: flex-start;
      flex-direction: column;
    }
    .status-row {
      grid-template-columns: 1fr;
    }
    .kpi-grid,
    .framework-grid,
    .memory-lane-grid,
    .memory-composition-summary,
    .capability-map-rail,
    .capability-node-grid,
    .profile-grid {
      grid-template-columns: 1fr;
    }
    .memory-lab-meters,
    .memory-flow {
      grid-template-columns: 1fr;
    }
    .memory-flow-line {
      width: 2px;
      min-width: 0;
      height: 1rem;
      justify-self: center;
      background: linear-gradient(180deg, rgba(185, 71, 34, 0.55), rgba(0, 109, 119, 0.4));
    }
    [data-testid="stChatMessage"] {
      max-width: 100% !important;
      border-radius: 18px !important;
    }
    .hit-head {
      align-items: flex-start;
      flex-wrap: wrap;
    }
    .hit-content-preview {
      white-space: normal;
    }
    .stTabs [role="tab"] {
      min-width: max-content !important;
      padding-inline: 0.9rem !important;
    }
  }

  @media (max-width: 480px) {
    .hero,
    .welcome-card,
    .chat-page-header,
    .observation-header,
    .panel {
      border-radius: 16px;
      padding: 0.9rem;
    }
    .hero-title {
      letter-spacing: -0.055em;
    }
    section[data-testid="stSidebar"] {
      min-width: min(88vw, 22rem) !important;
    }
  }

  @media (prefers-color-scheme: dark) {
    :root {
      --paper: #0f151a;
      --paper-2: #151d22;
      --ink: #edf2e8;
      --ink-soft: #c8d1c8;
      --ink-muted: #98a89f;
      --line: rgba(237, 242, 232, 0.16);
      --line-strong: rgba(237, 242, 232, 0.26);
      --glass: rgba(21, 29, 34, 0.78);
      --shadow: 0 22px 70px rgba(0, 0, 0, 0.33);
      --shadow-soft: 0 10px 30px rgba(0, 0, 0, 0.23);
    }

    .stApp {
      background:
        radial-gradient(circle at 8% 6%, rgba(215, 154, 43, 0.14), transparent 28rem),
        radial-gradient(circle at 92% 12%, rgba(0, 109, 119, 0.22), transparent 26rem),
        linear-gradient(135deg, #0f151a 0%, #121a20 55%, #16201d 100%);
    }

    .welcome-card,
    [data-testid="stChatMessage"],
    .stChatInput [data-baseweb="base-input"],
    .stButton > button,
    .status-value,
    .empty-state,
    .timeline-item,
    [data-testid="stMetric"] {
      background: rgba(21, 29, 34, 0.78) !important;
    }

    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
      background: linear-gradient(135deg, rgba(57, 33, 25, 0.86), rgba(21, 29, 34, 0.78)) !important;
    }

    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
      background: linear-gradient(135deg, rgba(17, 47, 49, 0.86), rgba(21, 29, 34, 0.78)) !important;
    }

    [data-testid="stAlert"] {
      background: rgba(67, 47, 13, 0.78) !important;
      color: #ffe9a8 !important;
    }

    [data-testid="stAlert"] * {
      color: #ffe9a8 !important;
    }
  }

  /* Keep narrow screens clear of Streamlit's collapsed sidebar rail and top toolbar. */
  @media (max-width: 720px) {
    .block-container {
      padding-top: 4.4rem !important;
      padding-left: calc(56px + 0.72rem) !important;
    }
    .stChatInput {
      padding-left: 56px !important;
    }
  }

  @media (max-width: 480px) {
    .block-container {
      padding-left: calc(52px + 0.55rem) !important;
    }
    .stChatInput {
      padding-left: 52px !important;
    }
  }


  /* Streamlit renders Material icon names as text in some embedded browsers. */
  [data-testid="stExpandSidebarButton"],
  [data-testid="stSidebarCollapseButton"] {
    overflow: hidden !important;
    color: transparent !important;
  }

  [data-testid="stExpandSidebarButton"] *,
  [data-testid="stSidebarCollapseButton"] * {
    max-width: 1.8rem !important;
    overflow: hidden !important;
    color: transparent !important;
    text-indent: -999px !important;
  }

  [data-testid="stExpandSidebarButton"] svg,
  [data-testid="stSidebarCollapseButton"] svg {
    color: currentColor !important;
    fill: currentColor !important;
    text-indent: 0 !important;
  }

  @media (max-width: 720px) {
    .chat-page-header {
      margin-top: 4.2rem !important;
    }
  }


  @media (max-width: 720px) {
    [data-testid="stMainBlockContainer"] {
      padding-top: 4rem !important;
    }
  }

  /* Readability and overflow repair pass */
  .stApp,
  [data-testid="stMain"],
  [data-testid="stMainBlockContainer"],
  [data-testid="stVerticalBlock"],
  [data-testid="column"],
  .element-container,
  .stMarkdown,
  [data-testid="stMarkdownContainer"] {
    min-width: 0 !important;
    max-width: 100% !important;
  }

  [data-testid="stMarkdownContainer"],
  [data-testid="stMarkdownContainer"] *,
  [data-testid="stChatMessage"],
  [data-testid="stChatMessage"] *,
  .hit-card,
  .hit-card *,
  .mimo-analysis-card,
  .mimo-analysis-card * {
    overflow-wrap: anywhere !important;
    word-break: break-word !important;
    white-space: normal !important;
  }

  [data-testid="stChatMessage"] {
    overflow: visible !important;
    height: auto !important;
    max-height: none !important;
  }

  [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
    overflow: visible !important;
    height: auto !important;
    max-height: none !important;
  }

  .hit-card {
    background: rgba(18, 28, 33, 0.94) !important;
    border-color: rgba(113, 210, 209, 0.34) !important;
  }

  .hit-content-preview,
  .hit-body,
  .hit-filter,
  .metric,
  .metric-label {
    color: #edf7f1 !important;
  }

  .hit-content-preview {
    white-space: normal !important;
    text-overflow: clip !important;
    overflow: visible !important;
  }

  .hit-backend {
    background: rgba(113, 210, 209, 0.18) !important;
    color: #71d2d1 !important;
  }

  .metric {
    background: rgba(237, 247, 241, 0.12) !important;
  }

  .mimo-analysis-card {
    max-width: 100%;
    overflow-x: auto;
    overflow-y: visible;
    padding: clamp(1rem, 2.5vw, 1.4rem);
    border: 1px solid rgba(113, 210, 209, 0.28);
    border-radius: var(--radius);
    background: rgba(18, 28, 33, 0.72);
    color: #edf7f1;
    box-shadow: var(--shadow-soft);
    font-family: var(--serif);
    font-size: clamp(0.78rem, 1.1vw, 0.92rem);
    line-height: 1.75;
  }

  .mimo-analysis-card br {
    display: block;
    content: "";
    margin-bottom: 0.35rem;
  }

  [data-testid="stExpander"] summary,
  [data-testid="stExpander"] summary * {
    color: #edf7f1 !important;
    text-indent: 0 !important;
  }

  [data-testid="stExpander"] summary svg,
  [data-testid="stExpander"] summary [data-testid="stIconMaterial"] {
    max-width: 1.2rem !important;
    overflow: hidden !important;
    color: transparent !important;
  }

  [data-testid="stExpander"] {
    overflow: visible !important;
  }

  [data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"],
  [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"],
  [data-testid="stHeaderActionElements"] [data-testid="stIconMaterial"] {
    font-size: 0 !important;
    line-height: 0 !important;
  }

  [data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"]::before,
  [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"]::before {
    content: "☰";
    color: #edf7f1;
    font-size: 1.1rem;
    line-height: 1;
    text-indent: 0;
  }

  @media (prefers-color-scheme: dark) {
    .panel,
    .observation-header,
    .kpi-card,
    .framework-card,
    .memory-lab-shell,
    .memory-lane,
    .memory-lab-meter,
    .memory-composition-shell,
    .memory-composition-card,
    .profile-constellation,
    .profile-orbit-card,
    .capability-map,
    .capability-node,
    .memory-signal-chip,
    .query-chip,
    .profile-field,
    .status-stack,
    .hero {
      background: rgba(18, 28, 33, 0.78) !important;
    }
    .hit-card,
    .mimo-analysis-card {
      background: rgba(18, 28, 33, 0.94) !important;
    }
  }

  @media (max-width: 720px) {
    .mimo-analysis-card {
      font-size: 0.85rem;
      line-height: 1.65;
    }
    .hit-card {
      padding: 0.8rem 0.75rem;
    }
  }

  /* Hide Streamlit chrome that was overlapping content in screenshots. */
  [data-testid="stToolbar"],
  [data-testid="stDecoration"],
  [data-testid="stStatusWidget"] {
    display: none !important;
    visibility: hidden !important;
  }

  header[data-testid="stHeader"] {
    height: 0 !important;
    min-height: 0 !important;
    background: transparent !important;
  }

  section[data-testid="stSidebar"] [data-testid="stAlert"] {
    background: rgba(255, 229, 138, 0.16) !important;
    border-color: rgba(255, 229, 138, 0.45) !important;
  }

  section[data-testid="stSidebar"] [data-testid="stAlert"] *,
  section[data-testid="stSidebar"] [data-testid="stAlert"] p {
    color: #fff3be !important;
    opacity: 1 !important;
  }

  [data-testid="stExpander"] details,
  [data-testid="stExpander"] summary {
    overflow: hidden !important;
  }

  [data-testid="stExpander"] summary p {
    margin: 0 !important;
  }

  [data-testid="stExpander"] summary [data-testid="stIconMaterial"] {
    display: none !important;
  }

  /* Keep the sidebar open: hide only the collapse control inside the sidebar. */
  [data-testid="stSidebarCollapseButton"],
  section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] button,
  section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] [role="button"] {
    display: none !important;
    visibility: hidden !important;
    pointer-events: none !important;
  }

  /* If a browser remembered a collapsed sidebar, keep the expand control usable. */
  [data-testid="stExpandSidebarButton"] {
    display: flex !important;
    visibility: visible !important;
    pointer-events: auto !important;
    color: #edf7f1 !important;
  }

  [data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"] {
    font-size: 0 !important;
    line-height: 0 !important;
  }

  [data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"]::before {
    content: "☰";
    color: #edf7f1;
    font-size: 1.1rem;
    line-height: 1;
  }

  /* Sidebar readability repair: do not inherit aggressive content wrapping into controls. */
  section[data-testid="stSidebar"] {
    width: 21.5rem !important;
    min-width: 21.5rem !important;
  }

  section[data-testid="stSidebar"] *,
  section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
  section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] * {
    word-break: normal !important;
    overflow-wrap: normal !important;
    white-space: normal !important;
  }

  section[data-testid="stSidebar"] [data-baseweb="slider"] p,
  section[data-testid="stSidebar"] [data-baseweb="slider"] span,
  section[data-testid="stSidebar"] [role="slider"] ~ *,
  section[data-testid="stSidebar"] [data-testid="stTickBar"] *,
  section[data-testid="stSidebar"] [data-testid="stThumbValue"] * {
    white-space: nowrap !important;
    word-break: keep-all !important;
    overflow-wrap: normal !important;
    font-family: var(--mono) !important;
    font-size: 0.78rem !important;
    line-height: 1.1 !important;
  }

  section[data-testid="stSidebar"] label,
  section[data-testid="stSidebar"] h3,
  section[data-testid="stSidebar"] p {
    line-height: 1.45 !important;
  }

  section[data-testid="stSidebar"] [data-testid="stAlert"] p {
    white-space: normal !important;
    overflow-wrap: break-word !important;
  }

  @media (max-width: 720px) {
    section[data-testid="stSidebar"] {
      width: min(86vw, 21.5rem) !important;
      min-width: min(86vw, 21.5rem) !important;
    }
  }

  /* Final sidebar/layout repair.
     Streamlit can remember a collapsed sidebar in the browser. Previous mobile
     compensation left a large empty gutter when that happened, so reset all
     rail offsets and expose a clear recovery button only while collapsed. */
  @media (max-width: 720px) {
    .block-container {
      padding-top: 0.8rem !important;
      padding-left: 0.72rem !important;
      padding-right: 0.72rem !important;
    }

    [data-testid="stMainBlockContainer"] {
      padding-top: 0 !important;
    }

    .chat-page-header {
      margin-top: 0 !important;
    }

    .stChatInput {
      padding-left: 0 !important;
      padding-right: 0 !important;
    }
  }

  @media (max-width: 480px) {
    .block-container {
      padding-left: 0.55rem !important;
      padding-right: 0.55rem !important;
    }
  }

  [data-testid="stSidebarCollapseButton"],
  section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] button,
  section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] [role="button"] {
    display: none !important;
    visibility: hidden !important;
    pointer-events: none !important;
  }

  [data-testid="stExpandSidebarButton"],
  [data-testid="stSidebarCollapsedControl"] {
    align-items: center !important;
    justify-content: center !important;
    display: flex !important;
    visibility: visible !important;
    pointer-events: auto !important;
    position: fixed !important;
    top: 0.82rem !important;
    left: 0.82rem !important;
    z-index: 99999 !important;
    width: 3.6rem !important;
    min-width: 3.6rem !important;
    height: 2.65rem !important;
    min-height: 2.65rem !important;
    padding: 0 !important;
    border-radius: 16px !important;
    border: 1px solid rgba(113, 210, 209, 0.44) !important;
    background:
      radial-gradient(circle at 22% 20%, rgba(113, 210, 209, 0.28), transparent 1.5rem),
      rgba(17, 35, 42, 0.96) !important;
    box-shadow: 0 14px 34px rgba(0, 0, 0, 0.38) !important;
    color: transparent !important;
    text-indent: 0 !important;
    overflow: hidden !important;
  }

  [data-testid="stExpandSidebarButton"] *,
  [data-testid="stSidebarCollapsedControl"] * {
    display: none !important;
  }

  [data-testid="stExpandSidebarButton"]::after,
  [data-testid="stSidebarCollapsedControl"]::after {
    content: "侧栏";
    color: #edf7f1 !important;
    font-family: var(--sans) !important;
    font-size: 0.78rem !important;
    font-weight: 850 !important;
    letter-spacing: 0.02em !important;
    line-height: 1 !important;
  }

  section[data-testid="stSidebar"] {
    width: 21.5rem !important;
    min-width: 21.5rem !important;
    max-width: 21.5rem !important;
  }

  @media (max-width: 720px) {
    section[data-testid="stSidebar"] {
      width: min(88vw, 21.5rem) !important;
      min-width: min(88vw, 21.5rem) !important;
      max-width: min(88vw, 21.5rem) !important;
    }
  }

  /* Wide-screen alignment: keep the workspace anchored to the sidebar instead
     of centering a 1360px canvas and leaving a dead gutter on the left. */
  [data-testid="stMain"],
  [data-testid="stMainBlockContainer"] {
    overflow-x: hidden !important;
  }

  [data-testid="stMain"] .block-container {
    width: 100% !important;
    max-width: none !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
    padding-left: clamp(1rem, 1.8vw, 2rem) !important;
    padding-right: clamp(1rem, 1.8vw, 2rem) !important;
  }

  .stChatInput > div {
    width: 100% !important;
    max-width: none !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
    padding-left: clamp(1rem, 1.8vw, 2rem) !important;
    padding-right: clamp(1rem, 1.8vw, 2rem) !important;
  }

  @media (max-width: 720px) {
    [data-testid="stMain"] .block-container {
      padding-left: 0.72rem !important;
      padding-right: 0.72rem !important;
    }

    .stChatInput > div {
      padding-left: 0.72rem !important;
      padding-right: 0.72rem !important;
    }
  }

  /* Long-answer repair: chat replies and analysis panels must grow with their
     content instead of being clipped by Streamlit wrappers or fixed chat input. */
  [data-testid="stChatMessage"],
  [data-testid="stChatMessage"] > div,
  [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
  [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] > div,
  [data-testid="stChatMessageContent"],
  [data-testid="stExpander"],
  [data-testid="stExpander"] details,
  [data-testid="stExpander"] [data-testid="stVerticalBlock"],
  [data-testid="stExpander"] [data-testid="stMarkdownContainer"],
  .mimo-analysis-card {
    height: auto !important;
    min-height: 0 !important;
    max-height: none !important;
    overflow: visible !important;
  }

  [data-testid="stChatMessage"] {
    contain: none !important;
    padding-bottom: 1.15rem !important;
  }

  [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
  [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li,
  [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] ol,
  [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] ul,
  .mimo-analysis-card p,
  .mimo-analysis-card li,
  .mimo-analysis-card ol,
  .mimo-analysis-card ul {
    margin-bottom: 0.78rem !important;
    line-height: 1.78 !important;
  }

  [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
    padding-bottom: 0.3rem !important;
  }

  [data-testid="stMain"] .block-container {
    padding-bottom: 11rem !important;
  }

  .mimo-analysis-card {
    display: block !important;
    white-space: pre-wrap !important;
    word-break: break-word !important;
    overflow-wrap: anywhere !important;
    padding-bottom: 1.6rem !important;
  }

  .mimo-analysis-card::after {
    content: "";
    display: block;
    height: 0.75rem;
  }

  /* Structured long-form layout: own the chat/analysis cards instead of relying
     on Streamlit chat wrappers, which can clip long Markdown on some viewports. */
  .echomem-chat-thread {
    display: grid;
    gap: 1rem;
    width: 100%;
    margin: 1rem 0 1.35rem;
  }

  .echomem-chat-card {
    display: grid;
    grid-template-columns: 2.55rem minmax(0, 1fr);
    gap: 0.9rem;
    width: min(100%, 72rem);
    height: auto;
    min-height: unset;
    max-height: none;
    overflow: visible;
    padding: clamp(1rem, 2vw, 1.35rem);
    border: 1px solid rgba(113, 210, 209, 0.28);
    border-radius: 24px;
    background:
      linear-gradient(135deg, rgba(18, 28, 33, 0.9), rgba(15, 24, 29, 0.78)),
      radial-gradient(circle at 100% 0%, rgba(113, 210, 209, 0.12), transparent 18rem);
    box-shadow: 0 18px 48px rgba(0, 0, 0, 0.18);
    word-break: break-word !important;
    white-space: normal !important;
  }

  .echomem-chat-card.user {
    margin-left: auto;
    border-color: rgba(255, 111, 92, 0.32);
    background:
      linear-gradient(135deg, rgba(58, 31, 25, 0.9), rgba(18, 28, 33, 0.8)),
      radial-gradient(circle at 0% 0%, rgba(255, 111, 92, 0.13), transparent 16rem);
  }

  .echomem-chat-card.assistant {
    margin-right: auto;
  }

  .echomem-chat-avatar {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2.35rem;
    height: 2.35rem;
    border-radius: 999px;
    background: rgba(113, 210, 209, 0.16);
    color: #edf7f1;
    font-family: var(--sans) !important;
    font-weight: 900;
    box-shadow: inset 0 0 0 1px rgba(113, 210, 209, 0.28);
  }

  .echomem-chat-card.user .echomem-chat-avatar {
    background: rgba(255, 111, 92, 0.2);
    box-shadow: inset 0 0 0 1px rgba(255, 111, 92, 0.3);
  }

  .echomem-chat-body {
    min-width: 0;
    max-width: 100%;
    overflow: visible;
  }

  .echomem-chat-content {
    min-width: 0;
    max-width: 100%;
    width: 100%;
    overflow: visible;
    white-space: pre-wrap !important;
    word-break: break-word !important;
    overflow-wrap: break-word !important;
    hyphens: auto !important;
  }

  .echomem-chat-role {
    margin-bottom: 0.45rem;
    color: #71d2d1;
    font-family: var(--sans) !important;
    font-size: 0.78rem;
    font-weight: 850;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .echomem-chat-card.user .echomem-chat-role {
    color: #ffb19f;
  }

  .echomem-chat-content {
    color: #edf7f1;
    font-family: var(--serif);
    line-height: 1.75;
    white-space: pre-wrap !important;
    overflow-wrap: break-word !important;
    word-break: break-word !important;
    width: 100%;
    max-width: 100%;
  }

  .echomem-chat-content strong,
  .mimo-analysis-card strong {
    color: #fff8df;
    font-weight: 900;
  }

  .math-inline,
  .math-block {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    color: #fff8df;
    background: rgba(255, 248, 223, 0.08);
    border: 1px solid rgba(255, 248, 223, 0.18);
    overflow-wrap: anywhere;
  }

  .math-inline {
    display: inline;
    padding: 0.08rem 0.28rem;
    border-radius: 6px;
  }

  .math-block {
    display: block;
    margin: 0.65rem 0;
    padding: 0.7rem 0.85rem;
    border-radius: 8px;
    white-space: pre-wrap;
  }

  .mimo-analysis-card {
    width: 100%;
    max-width: none;
    margin-top: 0.65rem;
    border-radius: 24px;
    line-height: 1.86;
  }

  /* 2026-05-12 UI polish pass: calm workbench palette, smaller hierarchy,
     and searchable memory surfaces. Keep this late so it overrides older
     repair styles without rewriting the whole theme. */
  :root {
    --paper: #f6f4ee;
    --paper-2: #ffffff;
    --ink: #172027;
    --ink-soft: #46535b;
    --ink-muted: #728087;
    --clay: #a85439;
    --clay-soft: rgba(168, 84, 57, 0.11);
    --teal: #1f756f;
    --teal-soft: rgba(31, 117, 111, 0.12);
    --gold: #b88a36;
    --line: rgba(23, 32, 39, 0.12);
    --line-strong: rgba(23, 32, 39, 0.2);
    --glass: rgba(255, 255, 255, 0.72);
    --shadow: 0 18px 48px rgba(31, 42, 48, 0.12);
    --shadow-soft: 0 8px 22px rgba(31, 42, 48, 0.08);
    --radius: 14px;
    --radius-sm: 10px;
    --serif: "Songti SC", "STSong", "Noto Serif CJK SC", Georgia, serif;
    --sans: "Avenir Next", "Gill Sans", "Trebuchet MS", sans-serif;
  }

  .stApp {
    background:
      linear-gradient(180deg, rgba(246, 244, 238, 0.96), rgba(238, 243, 241, 0.96)),
      linear-gradient(135deg, #f6f4ee 0%, #eef3f1 100%) !important;
  }

  .stApp::before {
    opacity: 0.16;
    background-size: 40px 40px;
  }

  .stApp p,
  .stApp span,
  .stApp label,
  .stApp li,
  .stApp td,
  .stApp th,
  .stApp div {
    font-size: 0.93rem;
    font-family: var(--sans) !important;
  }

  .welcome-greeting,
  .echomem-chat-content,
  .echomem-chat-content *,
  .mimo-analysis-card,
  .mimo-analysis-card * {
    font-family: var(--serif) !important;
  }

  section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #14252c 0%, #102027 100%) !important;
    box-shadow: 12px 0 32px rgba(16, 32, 39, 0.18);
  }

  section[data-testid="stSidebar"] h3 {
    color: #cce4dc !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.08em;
  }

  section[data-testid="stSidebar"] p,
  section[data-testid="stSidebar"] span,
  section[data-testid="stSidebar"] label,
  section[data-testid="stSidebar"] div {
    font-size: 0.86rem !important;
  }

  .chat-page-header,
  .observation-header,
  .panel,
  .welcome-card,
  .memory-lab-shell,
  .memory-lane,
  .memory-composition-shell,
  .memory-composition-card,
  .profile-constellation,
  .profile-orbit-card,
  .capability-map,
  .capability-node,
  .status-stack,
  .hero,
  [data-testid="stMetric"] {
    border-radius: var(--radius) !important;
    border-color: var(--line) !important;
    background: var(--glass) !important;
    box-shadow: var(--shadow-soft) !important;
  }

  .chat-page-title,
  .observation-title,
  .memory-lab-title {
    font-size: clamp(1.18rem, 1.8vw, 1.65rem) !important;
    letter-spacing: 0 !important;
  }

  .hero-title {
    font-size: clamp(1.55rem, 3.2vw, 2.65rem) !important;
    line-height: 1.05 !important;
    letter-spacing: 0 !important;
  }

  .panel h3 {
    font-size: clamp(1rem, 1.4vw, 1.18rem) !important;
    letter-spacing: 0 !important;
  }

  .kpi-value {
    font-size: clamp(1.35rem, 2.4vw, 1.85rem) !important;
    letter-spacing: 0 !important;
  }

  .framework-score,
  .capability-node-value,
  .memory-intensity-meta strong {
    font-size: 1.35rem !important;
  }

  .echomem-chat-card,
  .echomem-chat-card.user,
  .echomem-chat-card.assistant,
  .hit-card,
  .mimo-analysis-card {
    border-color: var(--line) !important;
    background: rgba(255, 255, 255, 0.74) !important;
    color: var(--ink) !important;
    box-shadow: var(--shadow-soft) !important;
  }

  .echomem-chat-card.user {
    background: linear-gradient(135deg, rgba(255, 249, 242, 0.9), rgba(255, 255, 255, 0.74)) !important;
  }

  .echomem-chat-card.assistant {
    background: linear-gradient(135deg, rgba(241, 249, 247, 0.9), rgba(255, 255, 255, 0.74)) !important;
  }

  .echomem-chat-content,
  .echomem-chat-content *,
  .hit-content-preview,
  .hit-body,
  .hit-filter,
  .metric,
  .metric-label,
  .mimo-analysis-card,
  .mimo-analysis-card * {
    color: var(--ink) !important;
  }

  .echomem-chat-role,
  .echomem-chat-card.user .echomem-chat-role,
  .hit-index,
  .kpi-value.accent,
  .framework-score {
    color: var(--teal) !important;
  }

  .echomem-chat-avatar,
  .echomem-chat-card.user .echomem-chat-avatar {
    background: var(--teal-soft);
    color: var(--teal);
    box-shadow: inset 0 0 0 1px rgba(31, 117, 111, 0.22);
  }

  .hit-card::before {
    background: var(--teal) !important;
  }

  .hit-backend,
  .metric,
  .memory-signal-chip,
  .query-chip {
    background: rgba(31, 117, 111, 0.08) !important;
    color: var(--ink-soft) !important;
    border-color: rgba(31, 117, 111, 0.16) !important;
  }

  .stButton > button {
    min-height: 2.35rem;
    border-radius: 10px !important;
  }

  .stButton > button:focus-visible,
  input:focus-visible,
  textarea:focus-visible,
  [data-baseweb="select"]:focus-within {
    outline: 2px solid rgba(31, 117, 111, 0.72) !important;
    outline-offset: 2px !important;
  }

  /* 2026-05-13 contrast repair: Streamlit/BaseWeb can repaint controls in
     dark gray while keeping inherited dark text. Keep main workbench controls
     light and force every nested label layer to a readable ink color. */
  [data-testid="stMain"] .stButton > button,
  [data-testid="stMain"] div[data-testid="stButton"] > button {
    background: #ffffff !important;
    color: #172027 !important;
    border: 1px solid rgba(31, 117, 111, 0.26) !important;
    box-shadow: 0 10px 26px rgba(23, 32, 39, 0.08) !important;
  }

  [data-testid="stMain"] .stButton > button *,
  [data-testid="stMain"] div[data-testid="stButton"] > button *,
  [data-testid="stMain"] .stButton > button p,
  [data-testid="stMain"] .stButton > button span {
    color: #172027 !important;
    opacity: 1 !important;
  }

  [data-testid="stMain"] .stButton > button:hover,
  [data-testid="stMain"] div[data-testid="stButton"] > button:hover {
    background: #f2faf8 !important;
    border-color: rgba(31, 117, 111, 0.52) !important;
    color: #145f5b !important;
  }

  [data-testid="stMain"] .stButton > button:hover *,
  [data-testid="stMain"] div[data-testid="stButton"] > button:hover * {
    color: #145f5b !important;
  }

  [data-testid="stMain"] .stButton > button[kind="primary"],
  [data-testid="stMain"] div[data-testid="stButton"] > button[kind="primary"] {
    background: #1f756f !important;
    border-color: #145f5b !important;
    color: #ffffff !important;
  }

  [data-testid="stMain"] .stButton > button[kind="primary"] *,
  [data-testid="stMain"] div[data-testid="stButton"] > button[kind="primary"] * {
    color: #ffffff !important;
  }

  .stChatInput [data-baseweb="base-input"],
  .stChatInput [data-baseweb="base-input"] > div,
  .stChatInput textarea,
  .stChatInput input {
    background: #ffffff !important;
    color: #172027 !important;
    caret-color: #1f756f !important;
  }

  .stChatInput [data-baseweb="base-input"] *,
  .stChatInput textarea *,
  .stChatInput input * {
    color: #172027 !important;
    opacity: 1 !important;
  }

  .stChatInput textarea::placeholder,
  .stChatInput input::placeholder {
    color: #6c7780 !important;
    opacity: 1 !important;
  }

  .stChatInput button {
    background: #e9eef2 !important;
    color: #5f6872 !important;
  }

  .stChatInput button *,
  .stChatInput button svg {
    color: #5f6872 !important;
    fill: currentColor !important;
    stroke: currentColor !important;
  }

  .stTextInput input,
  .stSelectbox [data-baseweb="select"] > div,
  .stTextArea textarea,
  .stNumberInput input {
    border-radius: 10px !important;
    border-color: var(--line-strong) !important;
    background: rgba(255, 255, 255, 0.76) !important;
    color: var(--ink) !important;
  }

  .memory-lane {
    min-height: 12rem;
  }

  .memory-flow-node,
  .capability-map-rail span,
  .status-key,
  .profile-constellation-core {
    background: #172027 !important;
  }

  .math-inline,
  .math-block {
    color: var(--ink) !important;
    background: rgba(31, 117, 111, 0.08) !important;
    border-color: rgba(31, 117, 111, 0.16) !important;
  }

  @media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
      animation-duration: 0.001ms !important;
      animation-iteration-count: 1 !important;
      scroll-behavior: auto !important;
      transition-duration: 0.001ms !important;
    }
  }

  @media (max-width: 720px) {
    .echomem-chat-card {
      grid-template-columns: 1fr;
      width: 100%;
      border-radius: 20px;
    }

    .echomem-chat-card.user,
    .echomem-chat-card.assistant {
      margin-left: 0;
      margin-right: 0;
    }
  }

</style>
"""


def inject_theme() -> None:
    """Inject global Streamlit CSS theme and KaTeX math rendering for EchoMem UI."""
    st.markdown(THEME_CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css" crossorigin="anonymous">
        <script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js" crossorigin="anonymous"></script>
        <script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js" crossorigin="anonymous"></script>
        <script>
        (function() {
            var KATEX_DELIMITERS = [
                {left: '$$', right: '$$', display: true},
                {left: '$', right: '$', display: false}
            ];
            function katexRender() {
                if (typeof renderMathInElement !== 'function') {
                    setTimeout(katexRender, 300);
                    return;
                }
                try {
                    renderMathInElement(document.body, {delimiters: KATEX_DELIMITERS, throwOnError: false});
                } catch(e) {}
            }
            katexRender();
            var observer = new MutationObserver(function() {
                if (typeof renderMathInElement === 'function') {
                    try {
                        renderMathInElement(document.body, {delimiters: KATEX_DELIMITERS, throwOnError: false});
                    } catch(e) {}
                }
            });
            observer.observe(document.body, {childList: true, subtree: true});
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )


__all__ = ["inject_theme"]

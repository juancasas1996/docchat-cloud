import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")
IS_LOCAL = "localhost" in API_URL or "127.0.0.1" in API_URL

st.set_page_config(
    page_title="DocChat Cloud",
    page_icon="💬",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Branded chrome (hero banner + pill badges), same design language as a
# production demo UI: dark gradient header, right-aligned status pills.
# ---------------------------------------------------------------------------

def render_badges(api_online: bool, agent_ready: bool) -> None:
    env_text, env_fg, env_bg = (
        ("LOCAL", "#1E40AF", "#DBEAFE") if IS_LOCAL else ("AZURE", "#5B21B6", "#EDE9FE")
    )
    if api_online and agent_ready:
        api_text, api_fg, api_bg = "AGENT READY", "#065F46", "#D1FAE5"
    elif api_online:
        api_text, api_fg, api_bg = "API ONLINE · NO CREDENTIALS", "#92400E", "#FEF3C7"
    else:
        api_text, api_fg, api_bg = "API OFFLINE", "#991B1B", "#FEE2E2"

    pill = (
        '<span style="background:{bg};color:{fg};padding:0.25rem 0.75rem;'
        "border-radius:999px;font-size:0.8rem;font-weight:600;"
        'letter-spacing:0.05em;margin-left:0.5rem;">{text}</span>'
    )
    st.markdown(
        '<div style="display:flex;justify-content:flex-end;margin-bottom:0.5rem;">'
        + pill.format(bg=env_bg, fg=env_fg, text=f"ENV · {env_text}")
        + pill.format(bg=api_bg, fg=api_fg, text=api_text)
        + "</div>",
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    st.markdown(
        '<div style="background: linear-gradient(135deg, #1F2937 0%, #374151 100%); '
        "color: #F9FAFB; padding: 1.25rem 1.75rem; border-radius: 8px; "
        'margin-bottom: 1.25rem;">'
        '<div style="display: flex; align-items: center;">'
        '<span style="font-size: 2rem; margin-right: 0.5rem;">💬</span>'
        '<div style="font-size: 1.9rem; font-weight: 700;">DocChat Cloud</div></div>'
        '<div style="font-size: 0.95rem; opacity: 0.85; margin-top: 0.25rem;">'
        "Agentic RAG chat — every answer is verified against the source before "
        "you see it. LangGraph · NVIDIA · Azure Container Apps.</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_divider() -> None:
    st.markdown(
        '<hr style="margin: 1rem 0 1.25rem; border: none; '
        'border-top: 1px solid rgba(128, 128, 128, 0.25);">',
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=30, show_spinner=False)
def api_health() -> dict:
    try:
        # Generous timeout: with scale-to-zero the API may need a cold start
        # (~10-20s) before it can answer the probe.
        r = requests.get(f"{API_URL}/health", timeout=45)
        r.raise_for_status()
        return {"online": True, **r.json()}
    except requests.RequestException:
        return {"online": False, "agent_ready": False}


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

health = api_health()
render_badges(health["online"], health.get("agent_ready", False))
render_hero()

if "chat_messages" not in st.session_state:
    st.session_state["chat_messages"] = []

# Status strip
cols = st.columns(3)
with cols[0]:
    st.metric("API", "🟢 Online" if health["online"] else "🔴 Offline")
    if not health["online"] and st.button("🔄 Retry", key="retry_health"):
        api_health.clear()
        st.rerun()
with cols[1]:
    st.metric(
        "Agent",
        "Ready" if health.get("agent_ready") else "No credentials",
        help="The LangGraph workflow: triage → answer → verify (1 retry max).",
    )
with cols[2]:
    st.metric("Messages", len(st.session_state["chat_messages"]) or "—")

render_divider()

# Agent mode: verified doc-chat vs ReAct over the MCP calculator tools
mode = st.radio(
    "Agent mode",
    [
        "📄 Documents (verified answers)",
        "🧮 Calculator (ReAct + MCP tools)",
        "📜 RAG (simulated agentic workflow)",
    ],
    horizontal=True,
    label_visibility="collapsed",
)
is_calc = mode.startswith("🧮")
is_rag = mode.startswith("📜")

if is_calc:
    st.caption(
        "ReAct agent: the LLM decides when to call the calculator tools, "
        "discovered live from the remote MCP server. Ask it some math."
    )
elif is_rag:
    st.caption(
        "Agentic workflow with SIMULATED retrieval: router → investigator "
        "(judges bad results and rewrites the query) → drafter ⇄ critic. "
        "Try: '¿Qué dice la ley sobre manejar borracho?'"
    )
else:
    # Optional custom context (documents mode only)
    with st.expander("📄 Context — what the agent answers from", expanded=False):
        st.caption(
            "By default the agent answers questions about this very project "
            "(architecture, CI/CD, agent design, roadmap). Paste your own text "
            "below to chat over it instead — document upload arrives in phase 6."
        )
        custom_context = st.text_area(
            "Custom context",
            key="custom_context",
            height=160,
            placeholder="Paste any text here and ask questions about it...",
            label_visibility="collapsed",
        )

# Chat history
for msg in st.session_state["chat_messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("verification"):
            with st.expander("🔍 Verification report"):
                st.text(msg["verification"])
                st.caption(f"Model: {msg.get('model', '?')}")
        if msg.get("trace"):
            with st.expander("🎬 Agent trace"):
                for step in msg["trace"]:
                    st.code(step, language=None)
                st.caption(f"Model: {msg.get('model', '?')}")

# Input + agent call
# Never disabled: asking a question is itself what wakes a scaled-to-zero API.
question = st.chat_input(
    "Ask something — e.g. how does the CI/CD of this project work?"
)
if question:
    st.session_state["chat_messages"].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            if is_calc:
                spinner_text = "ReAct agent: reason → act (MCP tools) → observe..."
                endpoint, payload = "/api/react", {"question": question}
            elif is_rag:
                spinner_text = "Workflow: router → investigator → drafter ⇄ critic..."
                endpoint, payload = "/api/rag", {"question": question}
            else:
                spinner_text = "Agent thinking: triage → answer → verify..."
                endpoint, payload = "/api/chat", {"question": question}
                if (st.session_state.get("custom_context") or "").strip():
                    payload["context"] = st.session_state["custom_context"].strip()
            with st.spinner(spinner_text):
                r = requests.post(f"{API_URL}{endpoint}", json=payload, timeout=120)
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as exc:
            data = {"answer": f"❌ Request failed: {exc}"}

        st.markdown(data["answer"])
        if data.get("verification"):
            with st.expander("🔍 Verification report"):
                st.text(data["verification"])
                st.caption(f"Model: {data.get('model', '?')}")
        if data.get("trace"):
            with st.expander("🎬 Agent trace"):
                for step in data["trace"]:
                    st.code(step, language=None)
                st.caption(f"Model: {data.get('model', '?')}")

    st.session_state["chat_messages"].append(
        {
            "role": "assistant",
            "content": data["answer"],
            "verification": data.get("verification", ""),
            "trace": data.get("trace", []),
            "model": data.get("model", ""),
        }
    )

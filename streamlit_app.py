"""Baba_Jee - an agentic data analyst.

Entry point: wires navigation, shared state and the agent control panel.
The workflow itself lives in `app_pages/`, one file per stage:

    upload -> preprocess -> analyse -> visualise -> report
"""

from __future__ import annotations

import streamlit as st

from agent import AGENT_NAME, AGENT_TAGLINE, __version__, llm, ui
from agent.state import STEPS, init_state, is_done, progress, reset_from

st.set_page_config(
    page_title=f"{AGENT_NAME} · AI data analyst",
    page_icon=":material/neurology:",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"about": f"{AGENT_NAME} v{__version__} — {AGENT_TAGLINE}"},
)

init_state()
if not st.session_state.model:
    st.session_state.model = llm.default_model()

ui.inject_styles()

pages = st.navigation(
    {
        "": [st.Page("app_pages/home.py", title="Overview", icon=":material/space_dashboard:", default=True)],
        "Workflow": [
            st.Page("app_pages/upload.py", title="Data upload", icon=":material/upload_file:"),
            st.Page("app_pages/preprocess.py", title="Data preprocessing", icon=":material/cleaning_services:"),
            st.Page("app_pages/analysis.py", title="Data analysis", icon=":material/query_stats:"),
            st.Page("app_pages/visualize.py", title="Data visualization", icon=":material/insights:"),
            st.Page("app_pages/report.py", title="Final report", icon=":material/description:"),
        ],
        "Agent": [st.Page("app_pages/chat.py", title="Ask Baba Jee", icon=":material/forum:")],
    },
    position="top",
)

# ---------------------------------------------------------------- control panel
with st.sidebar:
    ready = llm.is_ready()

    ui.sidebar_section("1", "Connect OpenAI")
    st.text_input(
        "OpenAI API key",
        key="api_key",
        type="password",
        placeholder="sk-...",
        label_visibility="collapsed",
        help="Kept in this browser session only. On Streamlit Cloud, set OPENAI_API_KEY in Secrets instead.",
    )
    options = llm.MODELS if st.session_state.model in llm.MODELS else [st.session_state.model, *llm.MODELS]
    st.selectbox("Model", options, key="model", accept_new_options=True, label_visibility="collapsed")
    if ready:
        st.badge(f"Connected · {st.session_state.model}", icon=":material/bolt:", color="green")
    else:
        st.badge("Local mode · no model key", icon=":material/offline_bolt:", color="orange")
        st.caption("Without a key Baba Jee still profiles, cleans, charts and reports — using rules instead of a model.")

    ui.sidebar_section("2", "Workflow progress")
    bar = progress()
    st.progress(bar.ratio, text=bar.label)
    for key, label, icon in STEPS:
        done = is_done(key)
        mark = ":material/check_circle:" if done else ":material/radio_button_unchecked:"
        colour = "green" if done else "gray"
        st.markdown(f":{colour}[{mark}] {label}")

    ui.sidebar_section("3", "Session")
    with st.expander("Advanced settings", icon=":material/tune:"):
        st.slider(
            "Temperature", 0.0, 1.0, key="temperature", step=0.1,
            help="Lower is more literal and repeatable — recommended for analysis.",
        )
        st.toggle(
            "Use the language model", key="use_llm",
            help="Turn off to run purely on the deterministic statistics engine.",
        )
    if st.button("Start a new session", icon=":material/restart_alt:", width="stretch"):
        reset_from("upload")
        st.session_state.messages = []
        st.toast("Session cleared. Upload a fresh dataset.", icon=":material/restart_alt:")
        st.rerun()
    st.caption(f"{AGENT_NAME} v{__version__}")

pages.run()

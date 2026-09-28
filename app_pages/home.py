"""Overview: what Baba Jee is, and where to start."""

from __future__ import annotations

import streamlit as st

from agent import AGENT_NAME, llm, ui
from agent.state import progress

ui.hero(
    AGENT_NAME,
    "Upload a dataset and get an instant profile, a cleaning plan you control, real statistics, "
    "charts chosen for your columns, and a report you can send. Every number is computed in Python — "
    "the model only explains what the numbers already say.",
    eyebrow="AI data analyst",
    pills=["OpenAI", "Streamlit", "pandas", "Altair", "5-stage pipeline"],
)

ui.step_strip([
    ("upload", "Data upload", "CSV, Excel, JSON"),
    ("preprocess", "Preprocessing", "Auditable cleaning"),
    ("analysis", "Data analysis", "Stats & correlations"),
    ("visualize", "Visualization", "Charts that fit"),
    ("report", "Final report", "Download & share"),
])

st.space("small")

ui.feature_tiles([
    (
        "&#128193;",
        "Bring your data",
        "CSV, Excel, JSON, TSV or Parquet up to 200 MB — or load the bundled sample dataset in one click.",
    ),
    (
        "&#128269;",
        "Instant profiling",
        "Types, missing values, duplicates, cardinality and distributions, checked the moment the file lands.",
    ),
    (
        "&#129518;",
        "The agent analyses",
        "Descriptive statistics, correlations and outlier fences — then a written interpretation of them.",
    ),
    (
        "&#128196;",
        "Answers and a report",
        "Ask follow-up questions in chat, then export one markdown report with the full audit trail.",
    ),
])

st.space("medium")

left, right = st.columns([3, 2], gap="large")

with left:
    with st.container(border=True):
        st.subheader("What happens at each stage", anchor=False)
        st.table(
            {
                "Stage": ["Data upload", "Data preprocessing", "Data analysis", "Data visualization", "Final report"],
                "Work performed": [
                    "Reads the file, infers types, and flags structural problems on arrival.",
                    "Applies auditable cleaning steps — headers, duplicates, dates, missing values, outliers.",
                    "Computes descriptive statistics, correlations and outlier fences, then explains them.",
                    "Recommends charts that suit the columns found, and renders them interactively.",
                    "Assembles everything into one markdown report you can download and circulate.",
                ],
            }
        )
        st.caption(
            "Each stage writes its result into the session and the next stage picks it up, so the final "
            "report is assembled from work you have already seen — not from a black box."
        )

with right:
    bar = progress()
    with st.container(border=True):
        st.subheader("Start here", anchor=False)
        st.progress(bar.ratio, text=bar.label)
        if st.button("Upload a dataset", icon=":material/upload_file:", type="primary", width="stretch"):
            st.switch_page("app_pages/upload.py")
        if st.button("Ask Baba Jee a question", icon=":material/forum:", width="stretch"):
            st.switch_page("app_pages/chat.py")
        st.caption("No dataset handy? The upload page ships with a sample file.")

    with st.container(border=True):
        st.subheader("Reasoning engine", anchor=False)
        if llm.is_ready():
            st.success(f"Connected to `{st.session_state.model}`.", icon=":material/bolt:")
            st.caption("Narrative sections are written by the model, grounded in computed statistics only.")
        else:
            st.warning("Running in local mode.", icon=":material/offline_bolt:")
            st.caption(
                "Every statistic, chart and report still works. Add an OpenAI key under "
                "**Connect OpenAI** in the sidebar to switch on model-written commentary."
            )

    with st.container(border=True):
        st.subheader("Privacy", anchor=False)
        st.caption(
            "Your raw rows are never sent to the model. Baba Jee reduces the dataset to aggregate "
            "statistics first, and only that profile leaves the session."
        )

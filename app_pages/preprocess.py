"""Stage 2 — Data preprocessing."""

from __future__ import annotations

import streamlit as st

from agent.preprocessing import run_pipeline
from agent.state import mark_done, reset_from
from agent.ui import kpi_row, page_header, preview, require

page_header(
    "Data preprocessing",
    "Choose the cleaning steps. Every one is applied in a fixed, safe order and written to an audit trail.",
    eyebrow="Stage 2 of 5",
)

if not require("upload", "Baba Jee needs a dataset before he can clean anything.", "app_pages/upload.py"):
    st.stop()

raw = st.session_state.raw_df

with st.form("preprocessing", border=True):
    st.markdown("**Cleaning plan**")
    structure, missing, outliers = st.columns(3, gap="large")

    with structure:
        st.caption("Structure")
        standardise_headers = st.checkbox("Standardise column names", value=True, help="Lowercase snake_case, no punctuation.")
        trim_whitespace = st.checkbox("Trim whitespace in text", value=True)
        coerce_dates = st.checkbox("Parse date-like columns", value=True, help="Text columns named like dates become real datetimes.")
        drop_duplicates = st.checkbox("Drop duplicate rows", value=True)

    with missing:
        st.caption("Missing data")
        numeric_strategy = st.selectbox(
            "Numeric columns", ["median", "mean", "zero", "none"],
            format_func=lambda s: {"none": "Leave as missing"}.get(s, f"Fill with {s}"),
        )
        categorical_strategy = st.selectbox(
            "Categorical columns", ["mode", "unknown", "none"],
            format_func=lambda s: {"mode": "Fill with most frequent", "unknown": "Fill with 'unknown'", "none": "Leave as missing"}[s],
        )
        drop_empty_columns = st.checkbox("Drop mostly-empty columns", value=True)
        empty_threshold = st.slider("Drop above this missing share", 0.5, 1.0, 0.9, 0.05, format="%.0f%%")

    with outliers:
        st.caption("Noise")
        drop_constant_columns = st.checkbox("Drop zero-variance columns", value=True)
        remove_outliers = st.checkbox("Remove outlier rows", value=False, help="Tukey fence on any numeric column. Off by default — outliers are often the story.")
        outlier_factor = st.slider("IQR multiplier", 1.0, 3.0, 1.5, 0.5, disabled=not remove_outliers)

    submitted = st.form_submit_button("Run preprocessing", icon=":material/play_arrow:", type="primary")

if submitted:
    options = {
        "standardise_headers": standardise_headers,
        "trim_whitespace": trim_whitespace,
        "coerce_dates": coerce_dates,
        "drop_duplicates": drop_duplicates,
        "drop_empty_columns": drop_empty_columns,
        "empty_threshold": empty_threshold,
        "drop_constant_columns": drop_constant_columns,
        "numeric_strategy": numeric_strategy,
        "categorical_strategy": categorical_strategy,
        "remove_outliers": remove_outliers,
        "outlier_factor": outlier_factor,
    }
    reset_from("preprocess")
    with st.status(":shimmer[Cleaning the dataset]", type="compact") as status:
        cleaned, log = run_pipeline(raw, options)
        for line in log:
            st.write(f"- {line}")
        status.update(label=f"Applied {len(log)} preprocessing step(s)", state="complete")
    st.session_state.clean_df = cleaned
    st.session_state.preprocess_log = log
    mark_done("preprocess")
    st.toast("Dataset cleaned.", icon=":material/check_circle:")

clean = st.session_state.clean_df
if clean is None:
    st.caption("Pick your steps above and run the pipeline. You can re-run it as often as you like — it always starts from the original upload.")
    st.stop()

rows_delta = len(clean) - len(raw)
cols_delta = clean.shape[1] - raw.shape[1]
missing_before = int(raw.isna().sum().sum())
missing_after = int(clean.isna().sum().sum())

kpi_row([
    ("Rows", f"{len(clean):,}", f"{rows_delta:+,} versus upload"),
    ("Columns", f"{clean.shape[1]}", f"{cols_delta:+d} versus upload"),
    ("Missing cells", f"{missing_after:,}", f"{missing_after - missing_before:+,} versus upload"),
    ("Duplicate rows", f"{int(clean.duplicated().sum()):,}", None),
])

clean_tab, audit_tab = st.tabs(["Cleaned data", "Audit trail"])

with clean_tab:
    preview(clean, key="clean_preview")

with audit_tab:
    for index, line in enumerate(st.session_state.preprocess_log, start=1):
        st.markdown(f"**{index}.** {line}")
    st.caption("This trail is reproduced verbatim in the final report, so a reader can see exactly what changed.")

with st.container(horizontal=True, horizontal_alignment="right"):
    if st.button("Continue to analysis", icon=":material/arrow_forward:", type="primary"):
        st.switch_page("app_pages/analysis.py")

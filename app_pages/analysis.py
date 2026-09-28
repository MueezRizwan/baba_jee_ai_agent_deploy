"""Stage 3 — Data analysis."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from agent import llm
from agent.analysis import analyse, build_prompt, fallback_narrative
from agent.state import active_df, mark_done
from agent.ui import flag_list, kpi_row, model_note, page_header, require

page_header(
    "Data analysis",
    "Statistics are computed first; the commentary is written from those numbers, never around them.",
    eyebrow="Stage 3 of 5",
)

if not require("upload", "Baba Jee needs a dataset before he can analyse anything.", "app_pages/upload.py"):
    st.stop()

df = active_df()
using_clean = st.session_state.clean_df is not None
st.caption(
    f"Analysing the **cleaned** dataset ({len(df):,} rows)."
    if using_clean
    else f"Analysing the **raw upload** ({len(df):,} rows) — no preprocessing has been applied yet."
)

controls = st.container(border=True)
with controls:
    left, right = st.columns([2, 1], gap="large")
    with left:
        threshold = st.slider(
            "Correlation reporting threshold", 0.1, 0.9, 0.5, 0.05,
            help="Only numeric pairs at or above this absolute Pearson r are reported.",
        )
    with right:
        st.write("")
        run = st.button("Run analysis", icon=":material/play_arrow:", type="primary", width="stretch")

if run:
    with st.status(":shimmer[Baba Jee is reading your data]", type="compact") as status:
        with st.status("Profiling columns and data quality", type="step"):
            result = analyse(df, st.session_state.source_name, threshold)
            st.write(f"{result['profile']['n_columns']} columns profiled.")
        with st.status("Measuring correlations and outliers", type="step"):
            st.write(f"{len(result['corr_pairs'])} correlated pair(s), {len(result['outliers'])} column(s) with outlier tails.")
        with st.status("Writing the interpretation", type="step"):
            if llm.is_ready():
                try:
                    insights = llm.complete(build_prompt(result))
                    used_model = True
                except RuntimeError as exc:
                    st.warning(str(exc), icon=":material/warning:")
                    insights, used_model = fallback_narrative(result), False
            else:
                insights, used_model = fallback_narrative(result), False
            st.write("Interpretation ready.")
        status.update(label="Analysis complete", state="complete")

    st.session_state.analysis = result
    st.session_state.insights = insights
    st.session_state.used_model = used_model
    mark_done("analysis")

result = st.session_state.analysis
if result is None:
    st.caption("Set your threshold and run the analysis.")
    st.stop()

prof = result["profile"]
groups = result["groups"]
kpi_row([
    ("Records", f"{prof['rows']:,}", None),
    ("Numeric fields", str(len(groups["numeric"])), None),
    ("Categorical fields", str(len(groups["categorical"])), None),
    ("Strong relationships", str(len(result["corr_pairs"])), "Pairs above the chosen threshold"),
    ("Columns with outliers", str(len(result["outliers"])), "1.5x IQR rule"),
])

findings, stats_tab, corr_tab, outlier_tab = st.tabs(["Findings", "Descriptive statistics", "Correlations", "Outliers"])

with findings:
    with st.container(border=True):
        st.markdown(st.session_state.insights)
        model_note(st.session_state.get("used_model", False))
    with st.container(border=True):
        st.markdown("**Data quality flags**")
        flag_list(result["flags"])

with stats_tab:
    if result["describe"].empty:
        st.caption("No numeric columns to describe.")
    else:
        st.dataframe(result["describe"].round(3), height=360)

with corr_tab:
    if result["corr_matrix"].empty:
        st.caption("At least two varying numeric columns are needed to compute correlations.")
    else:
        pairs = pd.DataFrame(result["corr_pairs"])
        if pairs.empty:
            st.caption(f"No pair reached |r| >= {threshold}. The numeric columns move largely independently.")
        else:
            st.dataframe(
                pairs.rename(columns={"a": "Column A", "b": "Column B", "r": "Pearson r", "direction": "Direction", "strength": "Strength"}),
                hide_index=True,
                column_config={"Pearson r": st.column_config.NumberColumn(format="%.3f")},
            )
            st.caption("Association only. Nothing here demonstrates that one column causes the other.")
        with st.expander("Full correlation matrix", icon=":material/grid_on:"):
            st.dataframe(result["corr_matrix"].round(3))

with outlier_tab:
    if not result["outliers"]:
        st.success("No column shows a meaningful outlier tail under the 1.5x IQR rule.", icon=":material/check_circle:")
    else:
        st.dataframe(
            pd.DataFrame(result["outliers"]).rename(
                columns={"column": "Column", "outliers": "Outliers", "pct": "Share %", "lower_fence": "Lower fence", "upper_fence": "Upper fence"}
            ),
            hide_index=True,
        )
        st.caption("Outliers are reported, not deleted. Remove them on the preprocessing page only if you know they are errors.")

with st.container(horizontal=True, horizontal_alignment="right"):
    if st.button("Continue to visualization", icon=":material/arrow_forward:", type="primary"):
        st.switch_page("app_pages/visualize.py")

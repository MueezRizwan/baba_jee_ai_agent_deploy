"""Stage 4 — Data visualization."""

from __future__ import annotations

import streamlit as st

from agent import charts
from agent.state import active_df, mark_done
from agent.ui import page_header, require

page_header(
    "Data visualization",
    "Baba Jee proposes charts that fit the columns he actually found, then draws the ones you keep.",
    eyebrow="Stage 4 of 5",
)

if not require("analysis", "Run the analysis first — the chart choices depend on what it found.", "app_pages/analysis.py"):
    st.stop()

df = active_df()
result = st.session_state.analysis
suggestions = charts.recommend(df, result["corr_pairs"])

if not suggestions:
    st.warning("This dataset has no chartable structure — no numeric, categorical or datetime columns were found.", icon=":material/warning:")
    st.stop()

titles = {spec["id"]: spec["title"] for spec in suggestions}
default = [spec["id"] for spec in suggestions[:4]]
stored = [chart["id"] for chart in st.session_state.charts if chart["id"] in titles]

with st.container(border=True):
    st.markdown("**Recommended charts**")
    st.caption("Each suggestion is justified below. Deselect anything that does not earn its place in the report.")
    chosen = st.pills(
        "Charts to render",
        options=list(titles),
        format_func=lambda key: titles[key],
        selection_mode="multi",
        default=stored or default,
        label_visibility="collapsed",
        key="chart_selection",
    )

selected = [spec for spec in suggestions if spec["id"] in (chosen or [])]

if not selected:
    st.caption("Select at least one chart to continue.")
    st.stop()

notes: dict[str, str] = {}
columns = st.columns(2, gap="large")
for index, spec in enumerate(selected):
    with columns[index % 2]:
        with st.container(border=True):
            st.markdown(f"**{spec['title']}**")
            chart = charts.build(spec, df)
            if chart is None:
                st.caption("This chart could not be drawn — the columns it needs are no longer in the dataset.")
                continue
            st.altair_chart(chart, key=f"chart_{spec['id']}")
            note = charts.describe(spec, df)
            notes[spec["id"]] = note
            st.caption(note)
            with st.expander("Why this chart", icon=":material/help:"):
                st.write(spec["why"])

st.session_state.charts = selected
st.session_state.chart_notes = notes
mark_done("visualize")

with st.expander("Build your own chart", icon=":material/tune:"):
    numeric = result["groups"]["numeric"]
    categorical = result["groups"]["categorical"]
    datetime_cols = result["groups"]["datetime"]
    kind = st.segmented_control("Chart type", ["scatter", "bar", "line", "histogram", "count"], default="scatter")
    axis_x, axis_y = st.columns(2)
    spec: dict = {"id": "custom", "type": kind, "title": "Custom chart", "why": "Built manually by the analyst."}
    if kind == "scatter":
        spec["x"] = axis_x.selectbox("X axis", numeric, key="cx")
        spec["y"] = axis_y.selectbox("Y axis", numeric, index=min(1, len(numeric) - 1) if numeric else 0, key="cy")
    elif kind == "line":
        spec["x"] = axis_x.selectbox("X axis (time)", datetime_cols or numeric, key="cx")
        spec["y"] = axis_y.selectbox("Y axis", numeric, key="cy")
    elif kind == "bar":
        spec["x"] = axis_x.selectbox("Group by", categorical, key="cx")
        spec["y"] = axis_y.selectbox("Measure", numeric, key="cy")
        spec["agg"] = st.selectbox("Aggregation", ["mean", "sum", "median", "max", "min"], key="cagg")
    elif kind == "histogram":
        spec["x"] = axis_x.selectbox("Column", numeric, key="cx")
    else:
        spec["x"] = axis_x.selectbox("Column", categorical or list(df.columns), key="cx")

    if all(spec.get(axis) for axis in ("x",)):
        spec["title"] = f"{kind.capitalize()} · {spec.get('y') or spec['x']}"
        custom = charts.build(spec, df)
        if custom is None:
            st.caption("Those columns cannot be combined into that chart type.")
        else:
            st.altair_chart(custom, key="chart_custom")
            if st.button("Add to report", icon=":material/add:"):
                existing = [c for c in st.session_state.charts if c["id"] != "custom"]
                st.session_state.charts = [*existing, spec]
                st.session_state.chart_notes["custom"] = charts.describe(spec, df)
                st.toast("Custom chart added to the report.", icon=":material/check_circle:")
    else:
        st.caption("This chart type needs a column that the dataset does not have.")

with st.container(horizontal=True, horizontal_alignment="right"):
    if st.button("Continue to the final report", icon=":material/arrow_forward:", type="primary"):
        st.switch_page("app_pages/report.py")

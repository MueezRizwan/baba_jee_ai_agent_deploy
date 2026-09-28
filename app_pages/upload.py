"""Stage 1 — Data upload."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import streamlit as st

from agent import samples
from agent.profiling import profile
from agent.state import mark_done, reset_from
from agent.ui import flag_list, kpi_row, page_header, preview

page_header(
    "Data upload",
    "Bring a CSV, Excel or JSON file — or pick one of the eleven bundled datasets. "
    "Baba Jee reads it, infers the types and reports what arrived.",
    eyebrow="Stage 1 of 5",
)


@st.cache_data(show_spinner=False, ttl="2h", max_entries=8)
def read_file(payload: bytes, name: str, sheet: str | None, delimiter: str) -> pd.DataFrame:
    """Parse an uploaded file into a dataframe. Cached on the file's bytes."""
    suffix = Path(name).suffix.lower()
    buffer = io.BytesIO(payload)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(buffer, sheet_name=sheet or 0)
    if suffix == ".json":
        return pd.read_json(buffer)
    if suffix == ".parquet":
        return pd.read_parquet(buffer)
    return pd.read_csv(buffer, sep=None if delimiter == "auto" else delimiter, engine="python")


@st.cache_data(show_spinner=False)
def sheet_names(payload: bytes) -> list[str]:
    return pd.ExcelFile(io.BytesIO(payload)).sheet_names


def adopt(frame: pd.DataFrame, name: str) -> None:
    """Make this dataframe the session's dataset and reset everything downstream."""
    reset_from("upload")
    st.session_state.raw_df = frame
    st.session_state.source_name = name
    mark_done("upload")


own_tab, library_tab = st.tabs(["Upload your own file", "Sample library"])

uploaded = None
with own_tab:
    with st.container(border=True):
        uploaded = st.file_uploader(
            "Choose a data file",
            type=["csv", "txt", "tsv", "xlsx", "xls", "json", "parquet"],
            help="Up to 200 MB. Nothing is written to disk — the file stays in this session.",
        )
        delimiter = "auto"
        sheet = None
        if uploaded is not None:
            suffix = Path(uploaded.name).suffix.lower()
            if suffix in {".csv", ".txt", ".tsv"}:
                delimiter = st.selectbox(
                    "Delimiter",
                    ["auto", ",", ";", "\t", "|"],
                    format_func=lambda d: {"auto": "Detect automatically", "\t": "Tab"}.get(d, d),
                )
            elif suffix in {".xlsx", ".xls"}:
                try:
                    sheet = st.selectbox("Worksheet", sheet_names(uploaded.getvalue()))
                except Exception as exc:
                    st.error(f"Could not read the workbook: {exc}", icon=":material/error:")

with library_tab:
    catalogue = samples.available()
    if not catalogue:
        st.error(
            "No sample datasets found. Regenerate them with `python tools/make_samples.py`.",
            icon=":material/error:",
        )
    else:
        domain = st.segmented_control(
            "Filter by domain", samples.DOMAINS, default="All", label_visibility="collapsed"
        ) or "All"
        shown = [s for s in catalogue if domain == "All" or s.domain == domain]
        st.caption(f"{len(shown)} dataset(s) · every one is synthetic, and every one has deliberate flaws to clean.")

        columns = st.columns(2, gap="medium")
        for index, sample in enumerate(shown):
            rows, cols = samples.shape_of(sample.key)
            with columns[index % 2]:
                with st.container(border=True):
                    with st.container(horizontal=True, vertical_alignment="center"):
                        st.markdown(f"{sample.icon} **{sample.name}**")
                        st.badge(sample.domain, color="violet")
                    st.caption(sample.summary)
                    st.caption(f":material/lightbulb: Good for: {sample.good_for}")
                    with st.container(horizontal=True, vertical_alignment="center"):
                        st.markdown(f":gray[{rows:,} rows · {cols} columns]")
                        if st.button("Load", key=f"load_{sample.key}", icon=":material/download:", type="primary"):
                            adopt(samples.load(sample.key), sample.filename)
                            st.toast(f"Loaded {sample.name}", icon=":material/check_circle:")
                            st.rerun()

if uploaded is not None:
    try:
        df = read_file(uploaded.getvalue(), uploaded.name, sheet, delimiter)
    except Exception as exc:
        st.error(f"Baba Jee could not parse that file: {exc}", icon=":material/error:")
    else:
        if df.empty:
            st.error("That file parsed to zero rows. Check the delimiter or the worksheet.", icon=":material/error:")
        elif (
            st.session_state.source_name != uploaded.name
            or st.session_state.raw_df is None
            or not st.session_state.raw_df.equals(df)
        ):
            adopt(df, uploaded.name)
            st.toast(f"Loaded {len(df):,} rows from {uploaded.name}", icon=":material/check_circle:")
            st.rerun()

raw = st.session_state.raw_df
if raw is None:
    st.caption("Waiting for a dataset. Everything downstream unlocks once a file is loaded.")
    st.stop()

prof = profile(raw, st.session_state.source_name)

st.subheader(f"Loaded: `{st.session_state.source_name}`", anchor=False)

kpi_row([
    ("Rows", f"{prof['rows']:,}", None),
    ("Columns", str(prof["n_columns"]), None),
    ("Missing cells", f"{prof['missing_cells']:,}", f"{prof['missing_pct']}% of the grid"),
    ("Duplicate rows", f"{prof['duplicate_rows']:,}", "Exact row-level duplicates"),
    ("Size in memory", f"{prof['memory_kb']:,.0f} KB", None),
])

data_tab, schema_tab, quality_tab = st.tabs(["Preview", "Schema", "First impressions"])

with data_tab:
    preview(raw, key="raw_preview")

with schema_tab:
    schema = pd.DataFrame([
        {
            "Column": col["name"],
            "Detected type": col["kind"],
            "Dtype": col["dtype"],
            "Missing": col["missing"],
            "Missing %": col["missing_pct"],
            "Unique": col["unique"],
        }
        for col in prof["columns"]
    ])
    st.dataframe(
        schema,
        hide_index=True,
        height=380,
        column_config={
            "Missing %": st.column_config.ProgressColumn("Missing %", min_value=0, max_value=100, format="%.1f%%"),
        },
    )

with quality_tab:
    notes: list[dict[str, str]] = []
    if prof["duplicate_rows"]:
        notes.append({"level": "warning", "text": f"{prof['duplicate_rows']} duplicate row(s) — the preprocessing stage can drop these."})
    heavy = [c["name"] for c in prof["columns"] if c["missing_pct"] > 30]
    if heavy:
        notes.append({"level": "error", "text": f"Heavily incomplete column(s): {', '.join(heavy)}."})
    constant = [c["name"] for c in prof["columns"] if c["unique"] <= 1]
    if constant:
        notes.append({"level": "info", "text": f"Zero-variance column(s) carrying no information: {', '.join(constant)}."})
    date_like = [c["name"] for c in prof["columns"] if c["kind"] == "text" and any(t in c["name"].lower() for t in ("date", "time", "day"))]
    if date_like:
        notes.append({"level": "info", "text": f"These look like dates but arrived as text: {', '.join(date_like)}."})
    if not notes:
        notes.append({"level": "success", "text": "Nothing structurally alarming on arrival."})
    flag_list(notes)

with st.container(horizontal=True, horizontal_alignment="right"):
    if st.button("Continue to preprocessing", icon=":material/arrow_forward:", type="primary"):
        st.switch_page("app_pages/preprocess.py")

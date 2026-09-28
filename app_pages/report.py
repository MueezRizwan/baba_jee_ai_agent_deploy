"""Stage 5 — Final report."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from agent import AGENT_NAME, llm, report as report_builder
from agent.state import active_df, mark_done
from agent.ui import page_header, require

page_header(
    "Final report",
    "Everything the agent computed, cleaned, charted and concluded — assembled into one document.",
    eyebrow="Stage 5 of 5",
)

if not require("analysis", "The report is built from the analysis. Run that stage first.", "app_pages/analysis.py"):
    st.stop()

df = active_df()
result = st.session_state.analysis

with st.container(border=True):
    st.markdown("**Report contents**")
    summary_line = ", ".join(
        [
            f"{len(st.session_state.preprocess_log)} preprocessing step(s)",
            f"{len(result['corr_pairs'])} correlation finding(s)",
            f"{len(result['outliers'])} outlier column(s)",
            f"{len(st.session_state.charts)} chart(s)",
        ]
    )
    st.caption(summary_line)
    if not st.session_state.charts:
        st.caption(":orange[No charts selected — visit the visualization stage to add figures.]")
    generate = st.button("Generate report", icon=":material/auto_awesome:", type="primary")

if generate:
    with st.status(":shimmer[Assembling the report]", type="compact") as status:
        with st.status("Writing the executive summary", type="step"):
            st.write("Using the model." if llm.is_ready() else "Using the rule-based writer.")
        with st.status("Laying out sections and tables", type="step"):
            markdown = report_builder.build(
                result=result,
                insights=st.session_state.insights or "",
                steps=st.session_state.preprocess_log,
                charts=st.session_state.charts,
                chart_notes=st.session_state.chart_notes,
                source_name=st.session_state.source_name,
                agent_name=AGENT_NAME,
                model_used=st.session_state.model if llm.is_ready() else None,
            )
            st.write(f"{len(markdown.splitlines())} lines produced.")
        status.update(label="Report ready", state="complete")
    st.session_state.report_md = markdown
    mark_done("report")

markdown = st.session_state.report_md
if not markdown:
    st.caption("Press generate when you are ready. You can regenerate after changing any earlier stage.")
    st.stop()

stamp = datetime.now().strftime("%Y%m%d-%H%M")
base = (st.session_state.source_name or "dataset").rsplit(".", 1)[0]

with st.container(horizontal=True):
    try:
        from agent.export import markdown_to_docx

        st.download_button(
            "Download as MS Word (.docx)",
            data=markdown_to_docx(markdown, AGENT_NAME, st.session_state.source_name),
            file_name=f"{AGENT_NAME}-report-{base}-{stamp}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            icon=":material/description:",
            type="primary",
        )
    except ImportError:
        st.warning("Word export needs `python-docx`. Install it with: pip install python-docx", icon=":material/warning:")

    st.download_button(
        "Download as markdown (.md)",
        data=markdown,
        file_name=f"{AGENT_NAME}-report-{base}-{stamp}.md",
        mime="text/markdown",
        icon=":material/download:",
    )
    st.download_button(
        "Download cleaned data (.csv)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"{base}-cleaned-{stamp}.csv",
        mime="text/csv",
        icon=":material/table_view:",
    )

st.caption(
    "The Word file rebuilds the report with real headings, lists and tables — open it in "
    "Microsoft Word, Google Docs or LibreOffice and edit it like any other document."
)

rendered, source = st.tabs(["Rendered report", "Markdown source"])

with rendered:
    with st.container(border=True):
        st.markdown(markdown)
        st.caption(
            "Charts stay interactive in the app. To embed them in the document, hover a chart on the "
            "visualization page and use its camera icon to save a PNG."
        )

with source:
    st.code(markdown, language="markdown", height=520)

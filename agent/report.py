"""Stage 5: assemble everything the agent learned into one document.

The report is plain markdown so it downloads cleanly, pastes into any
wiki, and stays readable even when no model was available.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from agent import llm
from agent.profiling import as_prompt

EXEC_SUMMARY_PROMPT = """Write the executive summary of a data analysis report.

Dataset profile (JSON):
{profile}

Correlations found: {corr}
Outlier summary: {outliers}
Quality flags: {flags}
Preprocessing applied: {steps}
Charts produced: {charts}

Write 4-6 bullets a decision-maker can act on. Lead with the finding, not the method.
Use concrete numbers. Do not invent anything absent from the facts above. No heading, bullets only.
"""


def _table(df: pd.DataFrame, max_rows: int = 12) -> str:
    if df is None or df.empty:
        return "_No data._"
    subset = df.head(max_rows).round(4)
    return subset.to_markdown()


def executive_summary(result: dict[str, Any], steps: list[str], charts: list[dict]) -> tuple[str, bool]:
    """Returns ``(markdown_bullets, used_model)``."""
    if not llm.is_ready():
        prof = result["profile"]
        bullets = [
            f"- The dataset holds **{prof['rows']:,} records across {prof['n_columns']} fields**"
            f" ({prof['missing_pct']}% of cells missing, {prof['duplicate_rows']} duplicate rows).",
        ]
        if result["corr_pairs"]:
            top = result["corr_pairs"][0]
            bullets.append(
                f"- The strongest relationship is **{top['a']} vs {top['b']}** (r = {top['r']},"
                f" {top['strength']} {top['direction']}) - an association, not a proven cause."
            )
        if result["outliers"]:
            worst = result["outliers"][0]
            bullets.append(
                f"- **{worst['column']}** carries the heaviest tail: {worst['outliers']} values"
                f" ({worst['pct']}%) sit outside the 1.5x IQR fence."
            )
        if steps:
            bullets.append(f"- {len(steps)} preprocessing step(s) were applied before analysis; see the audit trail below.")
        bullets.append(f"- {len(charts)} chart(s) were generated to support the findings above.")
        bullets.append("- Treat this summary as descriptive: nothing here has been tested for statistical significance.")
        return "\n".join(bullets), False

    prompt = EXEC_SUMMARY_PROMPT.format(
        profile=as_prompt(result["profile"]),
        corr=result["corr_pairs"][:8] or "none",
        outliers=result["outliers"][:8] or "none",
        flags=[flag["text"] for flag in result["flags"]],
        steps=steps or "none",
        charts=[chart.get("title") for chart in charts] or "none",
    )
    try:
        return llm.complete(prompt), True
    except RuntimeError:
        return executive_summary(result, steps, [])[0], False


def build(
    *,
    result: dict[str, Any],
    insights: str,
    steps: list[str],
    charts: list[dict],
    chart_notes: dict[str, str],
    source_name: str | None,
    agent_name: str = "Baba_Jee",
    model_used: str | None = None,
) -> str:
    prof = result["profile"]
    summary, _ = executive_summary(result, steps, charts)
    stamp = datetime.now().strftime("%d %B %Y, %H:%M")

    groups = result["groups"]
    lines: list[str] = [
        f"# Data analysis report",
        f"**Prepared by {agent_name}** · {stamp}",
        "",
        f"| Field | Value |",
        f"| --- | --- |",
        f"| Source file | `{source_name or 'unknown'}` |",
        f"| Rows analysed | {prof['rows']:,} |",
        f"| Columns | {prof['n_columns']} |",
        f"| Missing cells | {prof['missing_cells']:,} ({prof['missing_pct']}%) |",
        f"| Duplicate rows | {prof['duplicate_rows']} |",
        f"| Reasoning engine | {model_used or 'rule-based (no model configured)'} |",
        "",
        "## 1. Executive summary",
        summary,
        "",
        "## 2. Data preparation",
    ]

    if steps:
        lines += [f"{i}. {step}" for i, step in enumerate(steps, start=1)]
    else:
        lines.append("_The data was analysed as uploaded; no preprocessing was applied._")

    lines += [
        "",
        "## 3. Dataset structure",
        f"- Numeric columns ({len(groups['numeric'])}): {', '.join(groups['numeric']) or 'none'}",
        f"- Categorical columns ({len(groups['categorical'])}): {', '.join(groups['categorical']) or 'none'}",
        f"- Datetime columns ({len(groups['datetime'])}): {', '.join(groups['datetime']) or 'none'}",
        f"- Text columns ({len(groups['text'])}): {', '.join(groups['text']) or 'none'}",
        "",
        "### Descriptive statistics",
        _table(result["describe"]),
        "",
        "## 4. Analysis",
        insights or "_No analysis was generated._",
        "",
        "## 5. Correlations",
    ]

    if result["corr_pairs"]:
        lines += ["| Column A | Column B | r | Reading |", "| --- | --- | --- | --- |"]
        lines += [
            f"| {p['a']} | {p['b']} | {p['r']} | {p['strength']} {p['direction']} |"
            for p in result["corr_pairs"][:15]
        ]
        lines.append("")
        lines.append("_Correlation measures association only. None of these pairs has been tested for causation._")
    else:
        lines.append("_No numeric pair cleared the correlation threshold._")

    lines += ["", "## 6. Outliers"]
    if result["outliers"]:
        lines += ["| Column | Outliers | Share | Lower fence | Upper fence |", "| --- | --- | --- | --- | --- |"]
        lines += [
            f"| {row['column']} | {row['outliers']} | {row['pct']}% | {row['lower_fence']} | {row['upper_fence']} |"
            for row in result["outliers"][:15]
        ]
    else:
        lines.append("_No column shows a meaningful outlier tail under the 1.5x IQR rule._")

    lines += ["", "## 7. Visualizations"]
    if charts:
        for i, chart in enumerate(charts, start=1):
            lines.append(f"**Figure {i} — {chart.get('title', 'Untitled')}**")
            lines.append("")
            lines.append(f"- Why this chart: {chart.get('why', 'n/a')}")
            note = chart_notes.get(chart.get("id", ""), "")
            if note:
                lines.append(f"- What it shows: {note}")
            lines.append("")
        lines.append("_Charts are interactive in the app; export them from the app to embed images here._")
    else:
        lines.append("_No charts were generated._")

    lines += ["", "## 8. Data quality flags"]
    lines += [f"- **{flag['level'].upper()}** — {flag['text']}" for flag in result["flags"]]

    lines += [
        "",
        "---",
        f"_Generated by {agent_name}. Figures are computed directly from the uploaded file; "
        "narrative sections are model-assisted and should be reviewed before circulation._",
    ]
    return "\n".join(lines)

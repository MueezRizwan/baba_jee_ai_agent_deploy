"""Stage 3: statistics first, language second.

``analyse`` computes the hard numbers. ``narrate`` asks the model to
explain them - and if no model is configured, ``fallback_narrative``
writes a competent rule-based version instead, so the app is never dead.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from agent import llm
from agent.profiling import profile, split_columns


def correlations(df: pd.DataFrame, threshold: float = 0.5) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    numeric = df.select_dtypes(include="number")
    numeric = numeric.loc[:, numeric.nunique() > 1]
    if numeric.shape[1] < 2:
        return pd.DataFrame(), []
    matrix = numeric.corr(numeric_only=True)
    pairs: list[dict[str, Any]] = []
    cols = list(matrix.columns)
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            value = matrix.loc[a, b]
            if pd.notna(value) and abs(value) >= threshold:
                pairs.append({
                    "a": a,
                    "b": b,
                    "r": round(float(value), 3),
                    "direction": "positive" if value > 0 else "negative",
                    "strength": "very strong" if abs(value) >= 0.8 else "strong" if abs(value) >= 0.6 else "moderate",
                })
    pairs.sort(key=lambda item: abs(item["r"]), reverse=True)
    return matrix, pairs


def outlier_summary(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for col in df.select_dtypes(include="number").columns:
        series = df[col].dropna()
        if len(series) < 5:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        count = int(((series < low) | (series > high)).sum())
        if count:
            rows.append({
                "column": str(col),
                "outliers": count,
                "pct": round(count / len(series) * 100, 2),
                "lower_fence": round(float(low), 4),
                "upper_fence": round(float(high), 4),
            })
    return sorted(rows, key=lambda item: item["pct"], reverse=True)


def quality_flags(df: pd.DataFrame, prof: dict[str, Any]) -> list[dict[str, str]]:
    flags: list[dict[str, str]] = []
    if prof["rows"] < 30:
        flags.append({"level": "warning", "text": f"Only {prof['rows']} rows — statistics here are indicative, not conclusive."})
    if prof["duplicate_rows"]:
        flags.append({"level": "warning", "text": f"{prof['duplicate_rows']} duplicate row(s) still present."})
    if prof["missing_pct"] > 5:
        flags.append({"level": "warning", "text": f"{prof['missing_pct']}% of all cells are missing."})
    for col in prof["columns"]:
        if col["missing_pct"] > 30:
            flags.append({"level": "error", "text": f"`{col['name']}` is {col['missing_pct']}% missing — treat it with suspicion."})
        if col["kind"] in {"categorical", "text"} and col["unique"] == prof["rows"] and prof["rows"] > 1:
            flags.append({"level": "info", "text": f"`{col['name']}` is unique per row — likely an identifier, not a feature."})
    if not flags:
        flags.append({"level": "success", "text": "No structural data-quality problems detected."})
    return flags


def analyse(df: pd.DataFrame, source_name: str | None = None, corr_threshold: float = 0.5) -> dict[str, Any]:
    prof = profile(df, source_name)
    matrix, pairs = correlations(df, corr_threshold)
    groups = split_columns(df)
    numeric = df.select_dtypes(include="number")
    return {
        "profile": prof,
        "groups": groups,
        "describe": numeric.describe().T if not numeric.empty else pd.DataFrame(),
        "corr_matrix": matrix,
        "corr_pairs": pairs,
        "outliers": outlier_summary(df),
        "flags": quality_flags(df, prof),
    }


def fallback_narrative(result: dict[str, Any]) -> str:
    """Rule-based commentary used when no model is configured."""
    prof = result["profile"]
    groups = result["groups"]
    lines = [
        "### Dataset overview",
        f"- **{prof['rows']:,} rows x {prof['n_columns']} columns**, about {prof['memory_kb']:.0f} KB in memory.",
        f"- Column mix: {len(groups['numeric'])} numeric, {len(groups['categorical'])} categorical, "
        f"{len(groups['datetime'])} datetime, {len(groups['text'])} free text.",
        f"- Missing cells: {prof['missing_cells']:,} ({prof['missing_pct']}% of the grid); duplicate rows: {prof['duplicate_rows']}.",
        "",
        "### Relationships",
    ]
    pairs = result["corr_pairs"]
    if pairs:
        for pair in pairs[:5]:
            lines.append(f"- `{pair['a']}` and `{pair['b']}`: {pair['strength']} {pair['direction']} correlation (r = {pair['r']}).")
        lines.append("- These are associations only — they do not establish cause.")
    else:
        lines.append("- No numeric pair cleared the correlation threshold, so the numeric columns move largely independently.")

    lines += ["", "### Spread and outliers"]
    if result["outliers"]:
        for row in result["outliers"][:5]:
            lines.append(f"- `{row['column']}`: {row['outliers']} value(s) outside the IQR fence ({row['pct']}% of non-null rows).")
    else:
        lines.append("- No numeric column shows a meaningful outlier tail under the 1.5x IQR rule.")

    lines += ["", "### What to check next"]
    lines += [f"- {flag['text']}" for flag in result["flags"]]
    return "\n".join(lines)


def build_prompt(result: dict[str, Any], question: str | None = None) -> str:
    from agent.profiling import as_prompt

    parts = [
        "Here is the statistical profile of a dataset, as JSON:",
        as_prompt(result["profile"]),
        "",
        f"Notable correlations (|r| above threshold): {result['corr_pairs'][:10] or 'none'}",
        f"Outlier summary (1.5x IQR): {result['outliers'][:10] or 'none'}",
        f"Automated quality flags: {[flag['text'] for flag in result['flags']]}",
        "",
    ]
    if question:
        parts.append(f"The user asks: {question}\nAnswer using only the facts above.")
    else:
        parts.append(
            "Write the analysis section of a report with these markdown headings:\n"
            "### What this dataset contains\n### Key findings\n### Data quality concerns\n### Recommended next steps\n"
            "Cite real figures from the profile. Keep it under 400 words."
        )
    return "\n".join(parts)


def narrate(result: dict[str, Any], question: str | None = None) -> tuple[str, bool]:
    """Returns ``(markdown, used_model)``."""
    if not llm.is_ready():
        return fallback_narrative(result), False
    try:
        return llm.complete(build_prompt(result, question)), True
    except RuntimeError:
        return fallback_narrative(result), False

"""A deterministic question-answering engine for the chat page.

Without an API key the chat would otherwise be dead weight. This module
routes a question to an intent, then answers it from the statistics the
app already computed - so Baba Jee replies with real figures whether or
not a language model is connected.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

SUGGESTION_TEXT = {
    "first": "Given this dataset, what are the three things I should investigate first, and why?",
    "correlations": "Explain the correlations found, in plain language, and say what they do and do not prove.",
    "risks": "What data-quality risks would undermine an analysis of this dataset?",
    "questions": "Suggest five specific analytical questions this dataset can actually answer.",
}


def _columns(result: dict[str, Any]) -> list[str]:
    return [column["name"] for column in result["profile"]["columns"]]


def _mentioned_column(question: str, result: dict[str, Any]) -> str | None:
    """Find the dataset column a question refers to, if any."""
    text = question.lower()
    best: tuple[int, str] | None = None
    for name in _columns(result):
        needle = str(name).lower()
        readable = needle.replace("_", " ")
        if needle in text or (len(readable) > 3 and readable in text):
            score = len(needle)
            if best is None or score > best[0]:
                best = (score, name)
    return best[1] if best else None


def _column_entry(result: dict[str, Any], name: str) -> dict[str, Any] | None:
    for column in result["profile"]["columns"]:
        if column["name"] == name:
            return column
    return None


# ------------------------------------------------------------------ answers


def _overview(result: dict[str, Any]) -> str:
    prof, groups = result["profile"], result["groups"]
    return (
        f"**{prof['rows']:,} rows and {prof['n_columns']} columns**, roughly {prof['memory_kb']:.0f} KB in memory.\n\n"
        f"- Numeric: {', '.join(groups['numeric']) or 'none'}\n"
        f"- Categorical: {', '.join(groups['categorical']) or 'none'}\n"
        f"- Datetime: {', '.join(groups['datetime']) or 'none'}\n"
        f"- Text: {', '.join(groups['text']) or 'none'}\n\n"
        f"Missing cells: {prof['missing_cells']:,} ({prof['missing_pct']}% of the grid). "
        f"Duplicate rows: {prof['duplicate_rows']}."
    )


def _first_look(result: dict[str, Any]) -> str:
    lines = ["Here is where I would start, in order:", ""]
    pairs, outliers = result["corr_pairs"], result["outliers"]
    step = 1
    if pairs:
        top = pairs[0]
        lines.append(
            f"**{step}. The {top['a']} / {top['b']} relationship.** They move together at r = {top['r']} "
            f"({top['strength']} {top['direction']}). That is the single loudest signal in the data — "
            f"but check whether one is derived from the other before you read anything into it."
        )
        step += 1
    heavy = [c for c in result["profile"]["columns"] if c["missing_pct"] > 10]
    if heavy:
        worst = max(heavy, key=lambda c: c["missing_pct"])
        lines.append(
            f"**{step}. Missing data in `{worst['name']}`** — {worst['missing_pct']}% absent. "
            f"Decide whether to impute it or exclude it before you trust any statistic that uses it."
        )
        step += 1
    if outliers:
        worst = outliers[0]
        lines.append(
            f"**{step}. The tail on `{worst['column']}`** — {worst['outliers']} values ({worst['pct']}%) "
            f"sit outside the fence of {worst['lower_fence']} to {worst['upper_fence']}. "
            f"Are those genuine extremes or data-entry errors?"
        )
        step += 1
    groups = result["groups"]
    if step <= 3 and groups["categorical"] and groups["numeric"]:
        lines.append(
            f"**{step}. How `{groups['numeric'][0]}` differs across `{groups['categorical'][0]}`.** "
            f"Group comparison is usually the fastest route to something actionable."
        )
    return "\n\n".join(lines)


def _correlations(result: dict[str, Any]) -> str:
    pairs = result["corr_pairs"]
    if not pairs:
        return (
            "No numeric pair cleared the reporting threshold, so the numeric columns in this dataset move "
            "largely independently. Lower the threshold on the analysis page if you want to see weaker "
            "associations, but be careful: weak correlations rarely survive contact with new data."
        )
    lines = ["These pairs cleared the threshold, strongest first:", ""]
    for pair in pairs[:6]:
        lines.append(
            f"- **{pair['a']} ↔ {pair['b']}** — r = {pair['r']}, a {pair['strength']} {pair['direction']} "
            f"relationship. As {pair['a']} rises, {pair['b']} tends to "
            f"{'rise' if pair['direction'] == 'positive' else 'fall'}."
        )
    lines += [
        "",
        "**What this does prove:** these columns carry overlapping information. If you are building a model, "
        "near-duplicate predictors will fight each other.",
        "",
        "**What this does not prove:** causation. A high r is equally consistent with one column being derived "
        "from the other, both being driven by a third factor, or pure coincidence in a small sample.",
    ]
    return "\n".join(lines)


def _risks(result: dict[str, Any]) -> str:
    lines = ["Here is what would undermine an analysis of this dataset:", ""]
    lines += [f"- {flag['text']}" for flag in result["flags"]]
    prof = result["profile"]
    if prof["rows"] < 200:
        lines.append(f"- Only {prof['rows']:,} rows — every statistic here is indicative rather than conclusive.")
    identifiers = [c["name"] for c in prof["columns"] if c["unique"] == prof["rows"] and prof["rows"] > 1]
    if identifiers:
        lines.append(f"- `{', '.join(identifiers)}` is unique per row — an identifier, never a feature.")
    lines += [
        "",
        "Nothing in this app runs a significance test. There are no p-values and no confidence intervals, "
        "so treat every figure as descriptive.",
    ]
    return "\n".join(lines)


def _questions(result: dict[str, Any]) -> str:
    groups = result["groups"]
    numeric, categorical, dates = groups["numeric"], groups["categorical"], groups["datetime"]
    asks: list[str] = []
    if categorical and numeric:
        asks.append(f"Which `{categorical[0]}` group has the highest average `{numeric[0]}`, and by how much?")
    if dates and numeric:
        asks.append(f"Is `{numeric[0]}` trending up or down over `{dates[0]}`, and is there a seasonal pattern?")
    if result["corr_pairs"]:
        pair = result["corr_pairs"][0]
        asks.append(f"Does the link between `{pair['a']}` and `{pair['b']}` hold within every subgroup, or only overall?")
    if len(numeric) >= 2:
        asks.append(f"What is the ratio of `{numeric[0]}` to `{numeric[1]}`, and which records break that ratio?")
    if result["outliers"]:
        asks.append(f"What do the {result['outliers'][0]['outliers']} extreme `{result['outliers'][0]['column']}` records have in common?")
    if len(categorical) >= 2:
        asks.append(f"How do `{categorical[0]}` and `{categorical[1]}` interact — is one concentrated inside the other?")
    asks.append("Which records are missing the most fields, and is that missingness random or systematic?")
    body = "\n".join(f"{i}. {ask}" for i, ask in enumerate(asks[:6], start=1))
    return f"Questions this dataset can genuinely answer:\n\n{body}"


def _missing(result: dict[str, Any]) -> str:
    columns = sorted(result["profile"]["columns"], key=lambda c: c["missing_pct"], reverse=True)
    incomplete = [c for c in columns if c["missing"] > 0]
    if not incomplete:
        return "No column has a single missing value — this dataset is complete."
    lines = [f"{len(incomplete)} column(s) have gaps, worst first:", ""]
    lines += [f"- `{c['name']}` — {c['missing']:,} missing ({c['missing_pct']}%)" for c in incomplete[:10]]
    lines += [
        "",
        "Fill them on the preprocessing page — median for numeric columns is the safe default, because "
        "unlike the mean it is not dragged around by outliers.",
    ]
    return "\n".join(lines)


def _outliers(result: dict[str, Any]) -> str:
    rows = result["outliers"]
    if not rows:
        return "No numeric column shows a meaningful outlier tail under the 1.5x IQR rule."
    lines = ["Columns with values outside the Tukey fence:", ""]
    lines += [
        f"- `{row['column']}` — {row['outliers']} value(s), {row['pct']}% of non-null rows, "
        f"outside {row['lower_fence']} to {row['upper_fence']}"
        for row in rows[:8]
    ]
    lines += [
        "",
        "I report outliers rather than deleting them. They are often the most interesting records in the "
        "dataset — remove them only once you know they are errors.",
    ]
    return "\n".join(lines)


def _about_column(result: dict[str, Any], name: str, df: pd.DataFrame | None) -> str:
    entry = _column_entry(result, name)
    if entry is None:
        return f"I cannot find a column called `{name}` in this dataset."
    lines = [
        f"**`{entry['name']}`** — detected as *{entry['kind']}* (`{entry['dtype']}`).",
        "",
        f"- Missing: {entry['missing']:,} ({entry['missing_pct']}%)",
        f"- Distinct values: {entry['unique']:,}",
    ]
    stats = entry.get("stats")
    if stats:
        lines += [
            f"- Range: {stats['min']:,} to {stats['max']:,}",
            f"- Mean {stats['mean']:,} · median {stats['median']:,} · std {stats['std']:,}",
            f"- Quartiles: Q1 {stats['q25']:,}, Q3 {stats['q75']:,}",
        ]
        if stats.get("skew") is not None:
            skew = stats["skew"]
            shape = "roughly symmetric" if abs(skew) < 0.5 else ("right-skewed" if skew > 0 else "left-skewed")
            lines.append(f"- Skew: {skew} — {shape}")
        if stats.get("zeros"):
            lines.append(f"- Zeros: {stats['zeros']:,}")
    top = entry.get("top_values")
    if top:
        lines.append("- Most frequent: " + ", ".join(f"`{k}` ({v:,})" for k, v in list(top.items())[:5]))
    related = [p for p in result["corr_pairs"] if name in (p["a"], p["b"])]
    if related:
        lines.append("")
        lines.append("Related columns:")
        lines += [
            f"- `{p['b'] if p['a'] == name else p['a']}` — r = {p['r']} ({p['strength']} {p['direction']})"
            for p in related[:4]
        ]
    return "\n".join(lines)


# ------------------------------------------------------------------- router

INTENTS: list[tuple[str, str]] = [
    ("first", r"\b(start|first|begin|where do i|look at first|priorit)"),
    ("correlations", r"\b(correlat|relationship|related|associat|linked|r value|pearson)"),
    ("risks", r"\b(risk|wrong|problem|concern|quality|trust|reliab|caveat|limitation|bias)"),
    ("questions", r"\b(suggest|what can i ask|which question|ideas|explore)"),
    ("missing", r"\b(missing|null|nan|empty|incomplete|gap)"),
    ("outliers", r"\b(outlier|extreme|anomal|unusual|spike)"),
    ("overview", r"\b(overview|summar|describe the data|what is this|how many rows|shape|size|columns)"),
]


def classify(question: str) -> str:
    text = question.lower()
    for intent, pattern in INTENTS:
        if re.search(pattern, text):
            return intent
    return "unknown"


def answer(question: str, result: dict[str, Any], df: pd.DataFrame | None = None) -> str:
    """Answer a question from the computed analysis, with no model involved."""
    intent = classify(question)
    column = _mentioned_column(question, result)

    # A named column beats a generic intent, unless the question is clearly generic.
    if column and intent in {"unknown", "overview", "missing", "outliers"}:
        return _about_column(result, column, df)

    handlers = {
        "first": _first_look,
        "correlations": _correlations,
        "risks": _risks,
        "questions": _questions,
        "missing": _missing,
        "outliers": _outliers,
        "overview": _overview,
    }
    if intent in handlers:
        return handlers[intent](result)

    return (
        "I answer from the statistics computed for this dataset, and I could not match that question to "
        "any of them.\n\n"
        + _overview(result)
        + "\n\nTry naming a column, or ask about **correlations**, **missing values**, **outliers**, "
        "**risks**, or **where to start**. Connect an OpenAI key in the sidebar for open-ended conversation."
    )

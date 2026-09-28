"""Stage 4: the agent picks charts that suit the columns, then draws them.

Recommendations are scored from the column types and the correlation
results, so the suggestions change with the data instead of being a fixed
template. Rendering uses Altair, which Streamlit draws natively and which
inherits the app theme.
"""

from __future__ import annotations

from typing import Any

import altair as alt
import pandas as pd

from agent.profiling import split_columns

MAX_POINTS = 5000
MAX_BARS = 15


def recommend(df: pd.DataFrame, corr_pairs: list[dict] | None = None, limit: int = 6) -> list[dict[str, Any]]:
    """Return chart specs ranked by how much they should reveal."""
    groups = split_columns(df)
    numeric, categorical, datetime_cols = groups["numeric"], groups["categorical"], groups["datetime"]
    specs: list[dict[str, Any]] = []

    # 1. Trend over time carries the most signal when a real date exists.
    if datetime_cols and numeric:
        specs.append({
            "id": f"line::{datetime_cols[0]}::{numeric[0]}",
            "type": "line",
            "x": datetime_cols[0],
            "y": numeric[0],
            "title": f"{numeric[0]} over {datetime_cols[0]}",
            "why": "A datetime column lets us read direction and seasonality, not just level.",
        })

    # 2. The strongest correlated pairs, as scatters.
    for pair in (corr_pairs or [])[:2]:
        specs.append({
            "id": f"scatter::{pair['a']}::{pair['b']}",
            "type": "scatter",
            "x": pair["a"],
            "y": pair["b"],
            "color": categorical[0] if categorical else None,
            "title": f"{pair['b']} vs {pair['a']} (r = {pair['r']})",
            "why": f"{pair['strength'].capitalize()} {pair['direction']} correlation - worth seeing the shape behind the number.",
        })

    # 3. Category comparison.
    if categorical and numeric:
        specs.append({
            "id": f"bar::{categorical[0]}::{numeric[0]}",
            "type": "bar",
            "x": categorical[0],
            "y": numeric[0],
            "agg": "mean",
            "title": f"Mean {numeric[0]} by {categorical[0]}",
            "why": "Compares the groups the data is actually organised around.",
        })

    # 4. Distribution of the most variable numeric column.
    if numeric:
        spread = {col: df[col].std(skipna=True) for col in numeric if df[col].notna().any()}
        widest = max(spread, key=lambda c: (spread[c] if pd.notna(spread[c]) else -1), default=numeric[0]) if spread else numeric[0]
        specs.append({
            "id": f"hist::{widest}",
            "type": "histogram",
            "x": widest,
            "title": f"Distribution of {widest}",
            "why": "The widest-spread numeric column - where skew and outliers hide.",
        })

    # 5. Category frequency.
    if categorical:
        specs.append({
            "id": f"count::{categorical[0]}",
            "type": "count",
            "x": categorical[0],
            "title": f"Record count by {categorical[0]}",
            "why": "Shows class balance before anyone models this column.",
        })

    # 6. Correlation heatmap when there is enough numeric surface.
    if len(numeric) >= 3:
        specs.append({
            "id": "heatmap::numeric",
            "type": "heatmap",
            "title": "Correlation heatmap",
            "why": "One picture for every numeric pair at once.",
        })

    # Deduplicate while preserving rank order.
    seen: set[str] = set()
    unique = [s for s in specs if not (s["id"] in seen or seen.add(s["id"]))]
    return unique[:limit]


def _sample(df: pd.DataFrame) -> pd.DataFrame:
    return df.sample(MAX_POINTS, random_state=7) if len(df) > MAX_POINTS else df


def build(spec: dict[str, Any], df: pd.DataFrame):
    """Turn a spec into an Altair chart, or None if the columns went missing."""
    kind = spec["type"]
    height = 320

    if kind == "heatmap":
        numeric = df.select_dtypes(include="number")
        numeric = numeric.loc[:, numeric.nunique() > 1]
        if numeric.shape[1] < 2:
            return None
        matrix = (
            numeric.corr(numeric_only=True)
            .reset_index(names="row")
            .melt(id_vars="row", var_name="column", value_name="r")
        )
        return (
            alt.Chart(matrix, height=height)
            .mark_rect()
            .encode(
                x=alt.X("row:N", title=None),
                y=alt.Y("column:N", title=None),
                color=alt.Color("r:Q", scale=alt.Scale(scheme="tealblues", domain=[-1, 1]), title="r"),
                tooltip=["row:N", "column:N", alt.Tooltip("r:Q", format=".3f")],
            )
        )

    used = [spec.get(axis) for axis in ("x", "y", "color") if spec.get(axis)]
    if any(col not in df.columns for col in used):
        return None
    data = _sample(df)

    if kind == "line":
        return (
            alt.Chart(data, height=height)
            .mark_line(strokeWidth=2)
            .encode(
                x=alt.X(f"{spec['x']}:T", title=spec["x"]),
                y=alt.Y(f"{spec['y']}:Q", title=spec["y"], scale=alt.Scale(zero=False)),
                tooltip=[spec["x"], spec["y"]],
            )
        )

    if kind == "scatter":
        encoding: dict[str, Any] = {
            "x": alt.X(f"{spec['x']}:Q", title=spec["x"], scale=alt.Scale(zero=False)),
            "y": alt.Y(f"{spec['y']}:Q", title=spec["y"], scale=alt.Scale(zero=False)),
            "tooltip": [spec["x"], spec["y"]],
        }
        color = spec.get("color")
        if color and data[color].nunique() <= 12:
            encoding["color"] = alt.Color(f"{color}:N", title=color)
        return alt.Chart(data, height=height).mark_circle(size=60, opacity=0.6).encode(**encoding)

    if kind == "bar":
        agg = spec.get("agg", "mean")
        top = data[spec["x"]].astype("string").value_counts().head(MAX_BARS).index
        subset = data[data[spec["x"]].astype("string").isin(top)]
        return (
            alt.Chart(subset, height=height)
            .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
            .encode(
                x=alt.X(f"{spec['x']}:N", title=spec["x"], sort="-y"),
                y=alt.Y(f"{spec['y']}:Q", aggregate=agg, title=f"{agg} {spec['y']}"),
                tooltip=[spec["x"], alt.Tooltip(f"{spec['y']}:Q", aggregate=agg, format=".2f")],
            )
        )

    if kind == "histogram":
        return (
            alt.Chart(data, height=height)
            .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
            .encode(
                x=alt.X(f"{spec['x']}:Q", bin=alt.Bin(maxbins=30), title=spec["x"]),
                y=alt.Y("count():Q", title="Records"),
                tooltip=[alt.Tooltip("count():Q", title="Records")],
            )
        )

    if kind == "count":
        top = data[spec["x"]].astype("string").value_counts().head(MAX_BARS).reset_index()
        top.columns = [spec["x"], "records"]
        return (
            alt.Chart(top, height=height)
            .mark_bar(cornerRadiusTopRight=3, cornerRadiusBottomRight=3)
            .encode(
                y=alt.Y(f"{spec['x']}:N", sort="-x", title=spec["x"]),
                x=alt.X("records:Q", title="Records"),
                tooltip=[spec["x"], "records"],
            )
        )

    return None


def describe(spec: dict[str, Any], df: pd.DataFrame) -> str:
    """A short factual caption the report can reuse without calling a model."""
    kind = spec["type"]
    if kind == "heatmap":
        return "Pairwise Pearson correlation across every numeric column."
    if kind in {"scatter", "line", "bar"} and spec.get("y") in df.columns:
        series = df[spec["y"]].dropna()
        if len(series):
            return f"{spec['y']} ranges from {series.min():,.2f} to {series.max():,.2f} (mean {series.mean():,.2f})."
    if kind == "histogram" and spec.get("x") in df.columns:
        series = df[spec["x"]].dropna()
        if len(series):
            return f"{spec['x']}: median {series.median():,.2f}, skew {series.skew():.2f} across {len(series):,} values."
    if kind == "count" and spec.get("x") in df.columns:
        return f"{df[spec['x']].nunique()} distinct value(s) in {spec['x']}."
    return str(spec.get("why", ""))

"""Turn a dataframe into a compact, token-cheap profile.

The LLM never sees the raw data - it sees this profile. That keeps costs
predictable, keeps row-level data out of the request, and makes the
agent's commentary reproducible.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

MAX_CATEGORIES = 8


def column_kind(series: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    non_null = series.dropna()
    if len(non_null) and non_null.nunique() / max(len(non_null), 1) < 0.5:
        return "categorical"
    return "text"


def split_columns(df: pd.DataFrame) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {"numeric": [], "categorical": [], "datetime": [], "boolean": [], "text": []}
    for col in df.columns:
        groups[column_kind(df[col])].append(str(col))
    return groups


def _clean(value: Any) -> Any:
    """Make numpy / pandas scalars JSON-safe."""
    if value is None or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return round(float(value), 4)
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return str(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def profile(df: pd.DataFrame, source_name: str | None = None) -> dict[str, Any]:
    """A structured summary of shape, quality and per-column statistics."""
    rows, cols = df.shape
    missing_total = int(df.isna().sum().sum())
    groups = split_columns(df)

    columns: list[dict[str, Any]] = []
    for col in df.columns:
        series = df[col]
        kind = column_kind(series)
        missing = int(series.isna().sum())
        entry: dict[str, Any] = {
            "name": str(col),
            "kind": kind,
            "dtype": str(series.dtype),
            "missing": missing,
            "missing_pct": round(missing / rows * 100, 2) if rows else 0.0,
            "unique": int(series.nunique(dropna=True)),
        }
        if kind == "numeric":
            described = series.describe()
            entry["stats"] = {
                "mean": _clean(described.get("mean")),
                "std": _clean(described.get("std")),
                "min": _clean(described.get("min")),
                "q25": _clean(described.get("25%")),
                "median": _clean(described.get("50%")),
                "q75": _clean(described.get("75%")),
                "max": _clean(described.get("max")),
                "skew": _clean(series.skew()) if series.notna().sum() > 2 else None,
                "zeros": int((series == 0).sum()),
            }
        elif kind in {"categorical", "boolean", "text"}:
            counts = series.astype("string").value_counts().head(MAX_CATEGORIES)
            entry["top_values"] = {str(k): int(v) for k, v in counts.items()}
        elif kind == "datetime":
            entry["range"] = {"start": _clean(series.min()), "end": _clean(series.max())}
        columns.append(entry)

    return {
        "source": source_name,
        "rows": rows,
        "n_columns": cols,
        "duplicate_rows": int(df.duplicated().sum()),
        "missing_cells": missing_total,
        "missing_pct": round(missing_total / (rows * cols) * 100, 2) if rows and cols else 0.0,
        "memory_kb": round(df.memory_usage(deep=True).sum() / 1024, 1),
        "column_groups": groups,
        "columns": columns,
    }


def as_prompt(profile_dict: dict[str, Any], limit_columns: int = 40) -> str:
    """Render a profile as compact JSON suitable for a prompt."""
    trimmed = dict(profile_dict)
    cols = trimmed.get("columns", [])
    if isinstance(cols, list) and len(cols) > limit_columns:
        trimmed["columns"] = cols[:limit_columns]
        trimmed["columns_truncated"] = f"showing {limit_columns} of {len(cols)} columns"
    return json.dumps(trimmed, indent=None, default=str)

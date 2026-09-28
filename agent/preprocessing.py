"""Stage 2 of the workflow: deterministic, logged cleaning operations.

Every operation returns ``(dataframe, log_line)`` so the UI can show the
user exactly what the agent did to their data. Nothing happens silently.
"""

from __future__ import annotations

import re

import pandas as pd

from agent.profiling import column_kind


def standardise_headers(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    def tidy(name: object) -> str:
        text = re.sub(r"[^0-9a-zA-Z]+", "_", str(name)).strip("_").lower()
        return text or "unnamed"

    original = list(df.columns)
    df = df.rename(columns={col: tidy(col) for col in df.columns})
    # Disambiguate any collisions produced by the rename.
    seen: dict[str, int] = {}
    fixed = []
    for col in df.columns:
        if col in seen:
            seen[col] += 1
            fixed.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            fixed.append(col)
    df.columns = fixed
    changed = sum(1 for a, b in zip(original, df.columns) if str(a) != b)
    return df, f"Standardised {changed} column name(s) to snake_case."


def drop_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    return df, f"Removed {before - len(df)} duplicate row(s)."


def trim_whitespace(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    touched = 0
    for col in df.columns:
        if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
            df[col] = df[col].astype("string").str.strip()
            touched += 1
    return df, f"Trimmed surrounding whitespace in {touched} text column(s)."


def coerce_dates(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Convert text columns that look like dates into real datetimes."""
    converted: list[str] = []
    for col in df.columns:
        series = df[col]
        if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)):
            continue
        if not re.search(r"date|time|day|month|year|_at$|_on$", str(col), re.IGNORECASE):
            continue
        parsed = pd.to_datetime(series, errors="coerce", format="mixed")
        if parsed.notna().mean() >= 0.8:
            df[col] = parsed
            converted.append(str(col))
    label = ", ".join(converted) if converted else "none"
    return df, f"Parsed date-like columns: {label}."


def drop_empty_columns(df: pd.DataFrame, threshold: float = 0.9) -> tuple[pd.DataFrame, str]:
    ratio = df.isna().mean()
    doomed = [col for col in df.columns if ratio[col] > threshold]
    df = df.drop(columns=doomed)
    label = ", ".join(map(str, doomed)) if doomed else "none"
    return df, f"Dropped columns above {threshold:.0%} missing: {label}."


def drop_constant_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    doomed = [col for col in df.columns if df[col].nunique(dropna=False) <= 1]
    df = df.drop(columns=doomed)
    label = ", ".join(map(str, doomed)) if doomed else "none"
    return df, f"Dropped zero-variance columns: {label}."


def impute_missing(df: pd.DataFrame, numeric_strategy: str, categorical_strategy: str) -> tuple[pd.DataFrame, str]:
    """numeric_strategy: median | mean | zero | none. categorical: mode | unknown | none."""
    filled_num, filled_cat = 0, 0
    for col in df.columns:
        series = df[col]
        if series.isna().sum() == 0:
            continue
        kind = column_kind(series)
        if kind == "numeric" and numeric_strategy != "none":
            value = {"median": series.median(), "mean": series.mean(), "zero": 0}[numeric_strategy]
            df[col] = series.fillna(value)
            filled_num += 1
        elif kind in {"categorical", "text", "boolean"} and categorical_strategy != "none":
            if categorical_strategy == "mode":
                mode = series.mode(dropna=True)
                value = mode.iloc[0] if len(mode) else "unknown"
            else:
                value = "unknown"
            df[col] = series.astype("object").fillna(value)
            filled_cat += 1
    return df, f"Imputed missing values in {filled_num} numeric and {filled_cat} categorical column(s)."


def remove_outliers(df: pd.DataFrame, factor: float = 1.5) -> tuple[pd.DataFrame, str]:
    """Drop rows outside the Tukey fence on any numeric column."""
    numeric = df.select_dtypes(include="number")
    if numeric.empty:
        return df, "Outlier removal skipped: no numeric columns."
    mask = pd.Series(True, index=df.index)
    for col in numeric.columns:
        q1, q3 = numeric[col].quantile(0.25), numeric[col].quantile(0.75)
        iqr = q3 - q1
        if iqr == 0 or pd.isna(iqr):
            continue
        mask &= numeric[col].between(q1 - factor * iqr, q3 + factor * iqr) | numeric[col].isna()
    removed = int((~mask).sum())
    return df[mask].reset_index(drop=True), f"Removed {removed} outlier row(s) beyond {factor}x IQR."


def run_pipeline(df: pd.DataFrame, options: dict) -> tuple[pd.DataFrame, list[str]]:
    """Apply the selected steps in a safe, fixed order."""
    out = df.copy()
    log: list[str] = []

    def apply(step):
        nonlocal out
        out, line = step(out)
        log.append(line)

    if options.get("standardise_headers"):
        apply(standardise_headers)
    if options.get("trim_whitespace"):
        apply(trim_whitespace)
    if options.get("coerce_dates"):
        apply(coerce_dates)
    if options.get("drop_duplicates"):
        apply(drop_duplicates)
    if options.get("drop_empty_columns"):
        apply(lambda d: drop_empty_columns(d, options.get("empty_threshold", 0.9)))
    if options.get("drop_constant_columns"):
        apply(drop_constant_columns)
    if options.get("numeric_strategy", "none") != "none" or options.get("categorical_strategy", "none") != "none":
        apply(lambda d: impute_missing(d, options.get("numeric_strategy", "none"), options.get("categorical_strategy", "none")))
    if options.get("remove_outliers"):
        apply(lambda d: remove_outliers(d, options.get("outlier_factor", 1.5)))

    return out, log

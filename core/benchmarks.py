"""Validated manual benchmarks. No national statistics are fabricated or fetched."""

import numpy as np
import pandas as pd


def blank_benchmarks(subjects: list[str], national: bool) -> pd.DataFrame:
    """An empty editable table: all benchmark values are percentage measures."""
    frame = pd.DataFrame({"Subject": ["Overall"] + subjects})
    for column in ["Previous mean", "Previous pass %", "Dzongkhag mean"] + (
        ["National mean"] if national else []
    ):
        frame[column] = np.nan
    return frame


def compare_benchmarks(
    current: pd.DataFrame, entries: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Validate inputs and return differences and a tidy comparison chart dataset."""
    errors = []
    for column in entries.columns[1:]:
        raw = entries[column]
        values = pd.to_numeric(raw, errors="coerce")
        invalid = (raw.notna() & values.isna()) | values.lt(0) | values.gt(100)
        if invalid.any():
            errors.append(
                f"{column}: benchmark percentages must be numeric and between 0 and 100."
            )
    if errors:
        return pd.DataFrame(), pd.DataFrame(), errors
    joined = current.merge(entries, on="Subject", how="left", validate="one_to_one")
    rows, chart_rows = [], []
    for _, row in joined.iterrows():
        chart_rows.append(
            {"Subject": row.Subject, "Source": "Our school", "Mean %": row.Mean}
        )
        for column in entries.columns[1:]:
            if pd.isna(row[column]):
                continue
            current_value = row["Pass %"] if column == "Previous pass %" else row.Mean
            difference = current_value - row[column]
            direction = (
                "Unavailable"
                if pd.isna(difference)
                else "↑ Up"
                if difference > 0
                else "↓ Down"
                if difference < 0
                else "→ Unchanged"
            )
            rows.append(
                {
                    "Subject": row.Subject,
                    "Benchmark": column,
                    "School": current_value,
                    "Reference": row[column],
                    "Difference (points)": difference,
                    "Trend": direction,
                }
            )
            if column != "Previous pass %":
                chart_rows.append(
                    {
                        "Subject": row.Subject,
                        "Source": column.replace(" mean", ""),
                        "Mean %": row[column],
                    }
                )
    return pd.DataFrame(rows), pd.DataFrame(chart_rows), errors


def try_fetch_national() -> tuple[None, str]:
    """Requested integration hook: fail safely until a vetted source is configured."""
    try:
        raise ConnectionError("No verified national data endpoint is configured.")
    except (ConnectionError, TimeoutError) as exc:
        return None, f"{exc} Please enter published figures manually."

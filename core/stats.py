"""Pure percentage-based statistical functions with explicit denominators."""

import numpy as np
import pandas as pd
from core.subjects_config import DIAGNOSIS, PASS_PERCENT, IDENTITY


def summary(values: pd.Series) -> dict:
    """Summarize numeric percentages; sample SD is undefined for fewer than two."""
    v = pd.to_numeric(values, errors="coerce").dropna()
    n = len(v)
    return {
        "n": n,
        "Mean": v.mean(),
        "Median": v.median(),
        "Mode": v.mode().iloc[0] if n and len(v.mode()) == 1 else np.nan,
        "Highest": v.max(),
        "Lowest": v.min(),
        "Range": v.max() - v.min(),
        "Std dev": v.std(ddof=1),
        "Pass count": int(v.ge(PASS_PERCENT).sum()),
        "Pass %": 100 * v.ge(PASS_PERCENT).mean() if n else np.nan,
        "Fail count": int(v.lt(PASS_PERCENT).sum()),
        "Excluded": len(values) - n,
    }


def outlier_mask(values: pd.Series) -> pd.Series:
    """Strict Tukey fences; values equal to the fence are not outliers."""
    q1, q3 = values.quantile([0.25, 0.75])
    return values.lt(q1 - 1.5 * (q3 - q1)) | values.gt(q3 + 1.5 * (q3 - q1))


def percentages(frame: pd.DataFrame, maxima: dict[str, float]) -> pd.DataFrame:
    """Normalize each subject separately without rounding before decisions."""
    return frame[list(maxima)].div(pd.Series(maxima)).mul(100)


def subject_stats(pct: pd.DataFrame) -> pd.DataFrame:
    """Return per-subject statistics and IQR outlier counts."""
    return pd.DataFrame(
        [
            {
                "Subject": s,
                **summary(pct[s]),
                "Outlier count": int(outlier_mask(pct[s]).sum()),
            }
            for s in pct
        ]
    )


def student_results(frame: pd.DataFrame, maxima: dict[str, float]) -> pd.DataFrame:
    """Available-subject averages; complete-only totals and competition ranks."""
    pct = percentages(frame, maxima)
    result = frame[IDENTITY].copy()
    complete = pct.notna().all(axis=1)
    result["Assessed subjects"] = pct.notna().sum(axis=1)
    result["Average %"] = pct.mean(axis=1)
    result["Total marks"] = frame[list(maxima)].sum(axis=1).where(complete)
    result["Failed subjects"] = pct.lt(PASS_PERCENT).sum(axis=1)
    result["Borderline subjects"] = (pct.ge(PASS_PERCENT) & pct.lt(50)).sum(axis=1)
    result["Excluded subjects"] = pct.isna().sum(axis=1)
    result["Complete"] = complete
    result["Passed all"] = pct.ge(PASS_PERCENT).all(axis=1) & complete
    result["Passed any"] = pct.ge(PASS_PERCENT).any(axis=1)
    result["Rank"] = (
        result["Average %"]
        .where(complete)
        .rank(ascending=False, method="min")
        .astype("Int64")
    )
    return result


def class_overview(students: pd.DataFrame) -> dict:
    """Overall means use available averages; all-pass denominator is complete n."""
    complete = students.Complete
    valid = students["Assessed subjects"].gt(0)
    result = summary(students["Average %"])
    result.update(
        {
            "Students": len(students),
            "Complete n": int(complete.sum()),
            "Assessed n": int(valid.sum()),
            "Passed all %": students.loc[complete, "Passed all"].mean() * 100,
            "Passed any %": students.loc[valid, "Passed any"].mean() * 100,
            "Average total marks": students["Total marks"].mean(),
            "Failing 1": int(students["Failed subjects"].eq(1).sum()),
            "Failing 2": int(students["Failed subjects"].eq(2).sum()),
            "Failing 3+": int(students["Failed subjects"].ge(3).sum()),
        }
    )
    return result


def comparisons(frame: pd.DataFrame, pct: pd.DataFrame, column: str) -> pd.DataFrame:
    """Include missing comparison groups explicitly with n=0 and undefined metrics."""
    groups = ["Male", "Female"] if column == "Gender" else ["Boarder", "Day Scholar"]
    rows = []
    for subject in pct:
        for group in groups:
            rows.append(
                {
                    "Subject": subject,
                    column: group,
                    **summary(pct.loc[frame[column].eq(group), subject]),
                }
            )
    return pd.DataFrame(rows)


def comparison_text(table: pd.DataFrame, column: str, subject: str) -> str:
    """Describe observed mean differences without claiming causality."""
    group = table[table.Subject.eq(subject)]
    if len(group) != 2 or group["Mean"].isna().any():
        return f"{subject}: both groups need valid marks for a comparison."
    a, b = group.iloc[0], group.iloc[1]
    gap = b["Mean"] - a["Mean"]
    if abs(gap) < 0.005:
        return f"{subject}: group means are equal to two decimal places."
    winner, loser = (b, a) if gap > 0 else (a, b)
    return (
        f"{subject}: {winner[column]} students averaged {abs(gap):.2f} percentage points "
        f"higher than {loser[column]} students (valid n={int(winner['n'])}/{int(loser['n'])})."
    )


def remarks(values: pd.Series, benchmark: float = DIAGNOSIS["pass_benchmark"]) -> str:
    """Plain-language descriptive interpretation with small-sample caveats."""
    s = summary(values)
    if not s["n"]:
        return (
            "No valid marks are available. Enter marks before interpreting performance."
        )
    spread = (
        "unavailable for n<2"
        if pd.isna(s["Std dev"])
        else f"{s['Std dev']:.2f} percentage points"
    )
    skew = values.skew() if s["n"] >= 3 and values.nunique() > 1 else np.nan
    shape = (
        "Skewness cannot be assessed."
        if pd.isna(skew)
        else f"Skewness is {skew:.2f}: "
        + (
            "approximately symmetric."
            if abs(skew) < 0.5
            else "a longer high-score tail."
            if skew > 0
            else "a longer low-score tail."
        )
    )
    return (
        f"Sample standard deviation is {spread}. {shape} Pass rate is {s['Pass %']:.2f}%, "
        f"{abs(s['Pass %'] - benchmark):.2f} points {'above' if s['Pass %'] >= benchmark else 'below'} "
        f"the {benchmark:g}% descriptive benchmark. "
        + ("Fewer than five valid marks: interpret cautiously." if s["n"] < 5 else "")
    )


def diagnosis(
    frame: pd.DataFrame, pct: pd.DataFrame, settings: dict = DIAGNOSIS
) -> pd.DataFrame:
    """Conservative exhaustive classification; thresholds reside in configuration."""
    table = subject_stats(pct)
    rows = []
    for _, row in table.iterrows():
        mean, rate, subject = row["Mean"], row["Pass %"], row.Subject
        if row["n"] == 0:
            status = "No data"
        elif rate < settings["urgent_pass"] or mean < settings["urgent_mean"]:
            status = "Needs Urgent Attention"
        elif rate < settings["improve_pass"] or mean < settings["improve_mean"]:
            status = "Needs Improvement"
        elif rate >= settings["well_pass"] and mean >= settings["well_mean"]:
            status = "Doing Well"
        else:
            status = "Satisfactory"
        notes = (
            [f"Mean {mean:.2f}%; pass {rate:.2f}%."]
            if row["n"]
            else ["No valid marks."]
        )
        if status == "Needs Urgent Attention":
            notes.append(
                f"Pass <{settings['urgent_pass']}% OR mean <{settings['urgent_mean']}%; prioritize remedial teaching."
            )
        elif status == "Needs Improvement":
            notes.append(
                f"Pass <{settings['improve_pass']}% OR mean <{settings['improve_mean']}%; revisit weak concepts."
            )
        elif status == "Doing Well":
            notes.append(
                f"Pass ≥{settings['well_pass']}% AND mean ≥{settings['well_mean']}%; extend learning."
            )
        elif status == "Satisfactory":
            notes.append(
                "Above improvement thresholds but not both Doing Well thresholds; consolidate learning."
            )
        if row["Std dev"] > settings["high_std"]:
            notes.append("High spread: use differentiated teaching.")
        gaps = {}
        for column in ["Gender", "Residence"]:
            comp = comparisons(frame, pct[[subject]], column)
            gap = abs(comp["Mean"].iloc[0] - comp["Mean"].iloc[1])
            gaps[column + " gap"] = gap
            if gap >= settings["group_gap"]:
                notes.append(
                    f"{column} gap {gap:.2f} points: investigate access and support needs."
                )
        if row["n"] < 5:
            notes.append("Small sample: interpret cautiously.")
        borderline = (
            pct[subject].between(PASS_PERCENT, 50, inclusive="left").sum()
            / row["n"]
            * 100
            if row["n"]
            else np.nan
        )
        if borderline > 0:
            notes.append(
                f"{borderline:.2f}% are borderline (40–<50%); provide targeted practice."
            )
        rows.append(
            {
                "Subject": subject,
                "Diagnosis": status,
                "Mean": mean,
                "Pass %": rate,
                "Below 40 %": 100 - rate,
                "Borderline %": borderline,
                **gaps,
                "Strength": 0.5 * mean + 0.5 * rate,
                "Reasons and recommendations": " ".join(notes),
            }
        )
    result = pd.DataFrame(rows).sort_values(
        "Strength", ascending=False, na_position="last"
    )
    result["Rank"] = result.Strength.rank(method="min", ascending=False).astype("Int64")
    return result


def section_comparison(
    frame: pd.DataFrame, maxima: dict
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute section composite and detailed per-subject comparisons."""
    rows, details = [], []
    for section, group in frame.groupby("Section", sort=False):
        overview = class_overview(student_results(group, maxima))
        sd = overview["Std dev"]
        composite = (
            (
                0.4 * overview["Passed all %"]
                + 0.3 * overview["Mean"]
                + 0.2 * overview["Median"]
                + 0.1 * max(0, 100 - sd)
            )
            if pd.notna(sd)
            else np.nan
        )
        rows.append(
            {
                "Section": section,
                "Students": len(group),
                "n": overview["n"],
                "Complete n": overview["Complete n"],
                "Excluded": overview["Excluded"],
                "Mean": overview["Mean"],
                "Median": overview["Median"],
                "Std dev": sd,
                "Pass %": overview["Passed all %"],
                "Composite": composite,
            }
        )
        sub = subject_stats(percentages(group, maxima))
        sub.insert(0, "Section", section)
        details.append(sub)
    result = pd.DataFrame(rows)
    result["Rank"] = result.Composite.rank(ascending=False, method="min").astype(
        "Int64"
    )
    return result.sort_values("Rank"), pd.concat(details, ignore_index=True)

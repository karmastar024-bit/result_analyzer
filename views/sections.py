"""Sequential section uploads, whole-grade analysis and manual benchmarks."""

import hashlib
import pandas as pd
import streamlit as st
from core.benchmarks import blank_benchmarks, compare_benchmarks, try_fetch_national
from core.charts import Chart
from core.pdf_report import Report
from core.stats import (
    section_comparison,
    percentages,
    subject_stats,
    class_overview,
    student_results,
)
from core.validators import check_section_compatibility
from views.common import selection, uploader, table, chart, text, report_download
from views.class_result import class_content


def section_label(index: int) -> str:
    """Spreadsheet-like section names: A...Z, AA...AZ."""
    label = ""
    index += 1
    while index:
        index, digit = divmod(index - 1, 26)
        label = chr(65 + digit) + label
    return label


def benchmark_controls(
    frame: pd.DataFrame, maxima: dict, grade: str, report: Report, signature: str
) -> None:
    """Manual optional benchmarks with no invented historical or national data."""
    current = subject_stats(percentages(frame, maxima))[["Subject", "Mean", "Pass %"]]
    overview = class_overview(student_results(frame, maxima))
    current = pd.concat(
        [
            pd.DataFrame(
                [
                    {
                        "Subject": "Overall",
                        "Mean": overview["Mean"],
                        "Pass %": overview["Passed all %"],
                    }
                ]
            ),
            current,
        ],
        ignore_index=True,
    )
    national = grade in ["VI", "VIII", "X", "XII"]
    st.caption(
        "Enter previous-year mean and pass %, and optional Dzongkhag/national means as percentages. "
        "Leave unavailable values blank. Overall previous pass % must use the passed-all definition."
    )
    year = st.text_input(
        "Previous academic year label", "Previous year", key="benchmark_year"
    )
    base = blank_benchmarks(list(maxima), national)
    key = "benchmarks_" + signature
    if key not in st.session_state:
        st.session_state[key] = base
    entries = st.data_editor(
        st.session_state[key],
        disabled=["Subject"],
        hide_index=True,
        width="stretch",
        key=key + "_editor",
        column_config={
            c: st.column_config.NumberColumn(
                c, min_value=0.0, max_value=100.0, format="%.2f"
            )
            for c in base.columns[1:]
        },
    )
    # Separate permanent state preserves benchmarks if the page is temporarily unmounted.
    st.session_state[key] = entries.copy()
    if national and st.button("Try fetch from online source"):
        _, message = try_fetch_national()
        st.info(message)
    differences, comparison, errors = compare_benchmarks(current, entries)
    for error in errors:
        st.error(error)
    if errors:
        return
    if differences.empty:
        text(report, "No benchmark figures supplied. Benchmark comparison is skipped.")
        return
    table(report, f"Benchmark differences ({year})", differences)
    table(report, "Benchmark inputs supplied by teacher", entries)
    chart(
        report,
        Chart(
            "School and external mean benchmarks",
            "bar",
            comparison,
            "Subject",
            "Mean %",
            "Source",
        ),
    )
    for _, row in differences.iterrows():
        delta = row["Difference (points)"]
        if pd.notna(delta):
            relation = "above" if delta > 0 else "below" if delta < 0 else "equal to"
            text(
                report,
                f"{row.Subject}: school result is {abs(delta):.2f} percentage points {relation} {row.Benchmark} ({year if row.Benchmark.startswith('Previous') else 'teacher supplied'}).",
            )
    previous = differences[differences.Benchmark.eq("Previous pass %")]
    if not previous.empty:
        tidy = (
            previous[["Subject", "School", "Reference"]]
            .rename(columns={"School": "Our school", "Reference": "Previous year"})
            .melt(id_vars="Subject", var_name="Year", value_name="Pass %")
        )
        chart(
            report,
            Chart(
                "Pass rate change from previous year",
                "bar",
                tidy,
                "Subject",
                "Pass %",
                "Year",
            ),
        )


def comparison_content(frame: pd.DataFrame, maxima: dict, report: Report) -> None:
    """Section composite, four metric panels, and explicit tie-aware winners."""
    overall, detail = section_comparison(frame, maxima)
    table(report, "Section comparison and overall ranks", overall, heat=True)
    best = overall[overall.Rank.eq(1)]
    if not best.empty:
        text(
            report, "Best performing section overall: " + ", ".join(best.Section) + "."
        )
    else:
        text(report, "No section has enough data to receive an overall composite rank.")
    text(
        report,
        "Section rank = 40% passed-all rate + 30% mean + 20% median + 10% consistency, "
        "where consistency=max(0,100−sample SD). Mean/median/SD use available student averages. "
        "A rank requires sample SD and a passed-all denominator. Ties share rank.",
    )
    if (overall["n"] < 5).any():
        st.warning("At least one section has fewer than 5 assessed students.")
    for metric in ["Mean", "Median", "Pass %", "Std dev"]:
        chart(
            report,
            Chart(
                f"{metric} by section and subject",
                "bar",
                detail,
                "Subject",
                metric,
                "Section",
            ),
        )
        matrix = detail.pivot(index="Section", columns="Subject", values=metric)
        chart(
            report,
            Chart(f"{metric}: section × subject heatmap", "heatmap", matrix, y=metric),
        )
    strengths = detail.assign(Strength=0.5 * detail.Mean + 0.5 * detail["Pass %"])
    best_rows = []
    for subject, group in strengths.groupby("Subject", sort=False):
        usable = group.dropna(subset=["Strength"])
        best_rows.append(
            {
                "Subject": subject,
                "Best section": ", ".join(
                    usable.loc[usable.Strength.eq(usable.Strength.max()), "Section"]
                )
                or "No data",
                "Best strength": usable.Strength.max(),
                "Weakest section": ", ".join(
                    usable.loc[usable.Strength.eq(usable.Strength.min()), "Section"]
                )
                or "No data",
                "Weakest strength": usable.Strength.min(),
            }
        )
    table(
        report,
        "Best and weakest section per subject",
        pd.DataFrame(best_rows),
        heat=True,
    )
    text(
        report,
        "Best/weakest section per subject uses 50% subject mean + 50% subject pass rate. All ties are listed.",
    )
    table(report, "Detailed section subject statistics", detail)


def render(metadata: dict) -> None:
    """Maintain an ordered section collection and expose one upload slot at a time."""
    st.header("Section Comparison")
    subjects, grade = selection("sections")
    if not subjects:
        return
    schema = hashlib.sha256(repr((subjects, grade)).encode()).hexdigest()[:12]
    if st.session_state.get("section_schema") != schema:
        st.session_state["section_schema"] = schema
        st.session_state["section_records"] = {}
        st.session_state["section_finished"] = False
        st.session_state["section_revision"] = 0
        st.session_state["section_edit"] = None
    records = st.session_state["section_records"]
    edit = st.session_state.get("section_edit")
    for index, (name, data) in enumerate(list(records.items())):
        a, b, c = st.columns([3, 1, 1])
        a.success(f"Section {name}: {len(data.frame)} validated students")
        if b.button("Re-upload", key="edit_" + name):
            st.session_state["section_edit"] = name
            st.session_state["section_revision"] += 1
            st.session_state["section_finished"] = False
            st.rerun()
        if c.button("Remove section", key="remove_" + name):
            del records[name]
            st.session_state["section_finished"] = False
            st.session_state["section_edit"] = None
            st.session_state["section_revision"] += 1
            st.rerun()
    label = edit or section_label(len(records))
    if not edit:
        while label in records:
            label += "1"
    st.subheader(
        f"Re-upload section {edit}" if edit else f"Add next section (Section {label})"
    )
    revision = st.session_state["section_revision"]
    slot = f"section_{schema}_{revision}_{len(records)}"
    name = st.text_input(
        "Section name", value=label, key=slot + "_name", disabled=bool(edit)
    ).strip()
    if not name or len(name) > 30:
        st.warning("Enter a section name of 1–30 characters.")
        return
    if any(
        name.casefold() == existing.casefold()
        for existing in records
        if existing != edit
    ):
        st.error("That section name is already uploaded. Use Re-upload to replace it.")
        return
    candidate = uploader(subjects, slot, section=name)
    if candidate is not None:
        errors = check_section_compatibility(
            candidate, {n: d for n, d in records.items() if n != edit}
        )
        for error in errors:
            st.error(error)
        if not errors and st.button("Save validated section", key=slot + "_save"):
            records[name] = candidate
            st.session_state["section_edit"] = None
            st.session_state["section_finished"] = False
            st.session_state["section_revision"] += 1
            st.rerun()
    if edit:
        if st.button("Cancel re-upload"):
            st.session_state["section_edit"] = None
            st.session_state["section_revision"] += 1
            st.rerun()
        return
    if st.button(
        "Finish uploading & Analyse", type="primary", disabled=len(records) < 2
    ):
        st.session_state["section_finished"] = True
    if len(records) < 2:
        st.info("Validate and save at least two sections to compare them.")
        return
    if not st.session_state["section_finished"]:
        return
    frame = pd.concat([d.frame for d in records.values()], ignore_index=True)
    maxima = next(iter(records.values())).maxima
    report = Report(f"Class {grade}: section comparison")
    tabs = st.tabs(["Section comparison", "Whole grade", "Benchmarks"])
    with tabs[0]:
        comparison_content(frame, maxima, report)
    with tabs[1]:
        class_content(frame, maxima, report, "grade", whole_grade=True)
    with tabs[2]:
        benchmark_controls(frame, maxima, grade, report, schema)
    report_download(
        report, {**metadata, "Class": grade, "Section": ", ".join(records)}, "sections"
    )

"""Individual subject analysis page."""

import numpy as np
import pandas as pd
import streamlit as st
from core.charts import Chart
from core.pdf_report import Report
from core.stats import summary, outlier_mask, comparisons, comparison_text, remarks
from core.subjects_config import IDENTITY
from views.common import uploader, metrics, table, chart, text, report_download


def render(metadata: dict) -> None:
    """Analyze a single subject, preserving original marks and normalized scores."""
    st.header("Individual Subject Analysis")
    with st.container(border=True, key="setup_panel"):
        st.subheader("Set up your subject")
        a, b = st.columns(2)
        subject = (
            a.text_input(
                "Subject name",
                None if "individual_subject" in st.session_state else "English",
                key="individual_subject",
            )
            or ""
        ).strip()
        maximum = b.number_input(
            "Maximum marks",
            min_value=1.0,
            value=None if "individual_maximum" in st.session_state else 100.0,
            key="individual_maximum",
        )
    if not subject or subject.casefold() in {s.casefold() for s in IDENTITY}:
        st.warning("Enter a subject name distinct from identity columns.")
        return
    if maximum is None:
        st.warning("Enter the maximum marks.")
        return
    data = uploader([subject], "individual", maximum=maximum, enforce_max=True)
    if data is None:
        return
    frame = data.frame
    score = frame[subject] / maximum * 100
    report = Report(f"{subject}: individual subject analysis")
    stats = summary(score)
    stats["Absent"] = int(data.absent[subject].sum())
    stats["Blank"] = stats["Excluded"] - stats["Absent"]
    tabs = st.tabs(
        ["Summary", "Distribution", "Outliers", "Group comparisons", "Student lists"]
    )
    with tabs[0]:
        metrics(stats)
        table(report, "Summary (%)", pd.DataFrame([stats]))
        text(report, remarks(score))
        st.caption(
            f"All measures are percentages of {maximum:g} marks. Student lists show raw marks too."
        )
    with tabs[1]:
        chart(
            report,
            Chart(
                f"{subject}: score distribution",
                "distribution",
                pd.DataFrame({"Score %": score}),
                "Score %",
            ),
        )
        labels = ["0–39", "40–49", "50–59", "60–69", "70–79", "80–100"]
        bands = pd.cut(
            score, [-0.001, 40, 50, 60, 70, 80, 100.001], right=False, labels=labels
        )
        counts = bands.value_counts(sort=False)
        band_table = pd.DataFrame(
            {
                "Score band": labels,
                "Count": counts.to_numpy(),
                "Percentage": counts.to_numpy() / stats["n"] * 100
                if stats["n"]
                else np.full(6, np.nan),
            }
        )
        chart(
            report,
            Chart(f"{subject}: score bands", "bar", band_table, "Score band", "Count"),
        )
        table(report, "Score band counts and percentages", band_table)
        st.caption(
            "Band labels use whole numbers; boundaries are 0≤x<40, 40≤x<50, …, 80≤x≤100."
        )
    with tabs[2]:
        plot = pd.DataFrame({"Subject": subject, "Score %": score})
        chart(
            report,
            Chart(f"{subject}: spread and outliers", "box", plot, "Subject", "Score %"),
        )
        mask = outlier_mask(score)
        outliers = frame.loc[mask, ["Student ID", "Student Name", subject]].copy()
        outliers["Score %"] = score[mask]
        outliers["Type"] = np.where(score[mask] < score.quantile(0.25), "Low", "High")
        table(report, "Outlier students", outliers)
        if not mask.any():
            text(report, "No IQR outliers were detected.")
        st.caption(
            "IQR method: below Q1 − 1.5×IQR or above Q3 + 1.5×IQR. Outliers are retained in statistics."
        )
    with tabs[3]:
        for group in ["Gender", "Residence"]:
            comp = comparisons(frame, pd.DataFrame({subject: score}), group)
            table(report, group + " comparison", comp)
            for metric in [
                "n",
                "Mean",
                "Median",
                "Pass %",
                "Std dev",
                "Highest",
                "Lowest",
            ]:
                chart(
                    report,
                    Chart(
                        f"{subject}: {metric} by {group.lower()}",
                        "bar",
                        comp,
                        "Subject",
                        metric,
                        group,
                    ),
                )
            text(report, comparison_text(comp, group, subject))
            if (comp["n"] < 5).any():
                st.warning(
                    "At least one comparison group has fewer than 5 valid marks; missing groups have no computed mean."
                )
    with tabs[4]:
        if st.toggle("Show top 10 and bottom 10 students"):
            listed = (
                frame[["Student ID", "Student Name", subject]]
                .assign(**{"Score %": score})
                .dropna(subset=["Score %"])
            )
            table(report, "Top 10 students", listed.nlargest(10, "Score %"))
            table(report, "Bottom 10 students", listed.nsmallest(10, "Score %"))
    report_download(
        report,
        {**metadata, "Class": "Individual subject", "Section": "As uploaded"},
        "individual",
    )

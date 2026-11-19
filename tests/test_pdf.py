"""PDF table/chart integration, including empty data and wide tables."""

from io import BytesIO
import pandas as pd
from pypdf import PdfReader
from core.pdf_report import Report, build_pdf
from core.charts import Chart


def test_pdf_all_chart_types_and_wide_tables():
    table = pd.DataFrame({f"Column {i}": [i, i + 1] for i in range(12)})
    report = Report(
        "Test class report", [("Wide table", table)], ["Interpretation text."]
    )
    report.charts = [
        Chart(
            "Distribution",
            "distribution",
            pd.DataFrame({"Score": [20, 40, 60, 80, 100]}),
            "Score",
        ),
        Chart(
            "Group means",
            "bar",
            pd.DataFrame(
                {
                    "Subject": ["English", "English"],
                    "Gender": ["Male", "Female"],
                    "Mean": [60, 65],
                }
            ),
            "Subject",
            "Mean",
            "Gender",
        ),
        Chart(
            "Spread",
            "box",
            pd.DataFrame({"Subject": ["English"] * 5, "Score": [20, 40, 60, 80, 100]}),
            "Subject",
            "Score",
        ),
        Chart(
            "Heatmap",
            "heatmap",
            pd.DataFrame(
                [[50, 60], [70, 80]], index=["A", "B"], columns=["English", "Math"]
            ),
            y="Mean",
        ),
    ]
    output = build_pdf(
        report,
        {
            "School": "Fictional school",
            "Teacher": "Test teacher",
            "Year": "2026",
            "Class": "VI",
            "Section": "A, B",
        },
    )
    reader = PdfReader(BytesIO(output))
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert text.startswith("Fictional school")
    assert "Column 11" in text
    assert "Interpretation text." in text
    assert all(
        f"Page {i + 1}" in page.extract_text() for i, page in enumerate(reader.pages)
    )
    assert sum(len(page.images) for page in reader.pages) == 4


def test_no_marks_pdf():
    report = Report(
        "No marks",
        charts=[
            Chart(
                "Empty scores",
                "distribution",
                pd.DataFrame({"Score": [float("nan")]}),
                "Score",
            )
        ],
    )
    assert build_pdf(report, {}).startswith(b"%PDF")

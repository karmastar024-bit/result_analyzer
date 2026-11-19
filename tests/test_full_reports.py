"""End-to-end report capture from each real UI, including the full chart set."""

from io import BytesIO
from unittest.mock import patch
from pathlib import Path
import pandas as pd
import pytest
from pypdf import PdfReader
from streamlit.testing.v1 import AppTest
from core.templates import template
from core.validators import read_marks
from core.subjects_config import STAGES
from core.pdf_report import build_pdf


@pytest.mark.parametrize("module", ["individual", "class", "sections"])
def test_complete_module_pdf(module, tmp_path):
    """Render precisely what the module passes to its PDF button."""
    names = {
        "individual": "Individual Subject Analysis",
        "class": "Class Result Analysis",
        "sections": "Section Comparison",
    }
    app = AppTest.from_file("app.py", default_timeout=60).run()
    app.sidebar.radio[0].set_value(names[module]).run()
    subjects = ["English"] if module == "individual" else STAGES["Key Stage 1"]["core"]
    if module == "sections":
        app.session_state["section_records"] = {
            s: read_marks(template(tuple(subjects), True, s), subjects, s)
            for s in ["A", "B"]
        }
        app.session_state["section_finished"] = True
    else:
        app.session_state[module + "_data"] = read_marks(
            template(tuple(subjects), True), subjects
        )
    app.run()
    captured = []

    def capture(report, metadata):
        captured.append((report, metadata))
        return b"%PDF-test"

    with patch("views.common.build_pdf", capture):
        next(b for b in app.button if b.label == "Prepare PDF Report").click().run()
    assert not app.exception
    assert captured
    report, metadata = captured[0]
    output = build_pdf(report, metadata)
    reader = PdfReader(BytesIO(output))
    assert sum(len(page.images) for page in reader.pages) == len(report.charts)
    assert len(report.charts) >= (
        17 if module == "individual" else 7 if module == "class" else 15
    )
    # QA outputs are fictional only and ignored by source control.
    folder = Path("tmp/pdfs")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{module}.pdf").write_bytes(output)
    for i, page in enumerate(reader.pages):
        assert f"Page {i + 1}" in page.extract_text()

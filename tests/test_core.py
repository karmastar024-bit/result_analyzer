"""Behavioral checks for denominators, boundaries, workbook validation and reports."""

from io import BytesIO
import numpy as np
import pandas as pd
import pytest
from openpyxl import load_workbook
from core.templates import template
from core.validators import read_marks, check_section_compatibility
from core.subjects_config import resolve_subjects, STAGES
from core.stats import (
    summary,
    outlier_mask,
    percentages,
    student_results,
    class_overview,
    diagnosis,
    section_comparison,
    comparisons,
)
from core.benchmarks import blank_benchmarks, compare_benchmarks


def edited(changes: dict[str, object], subjects=("English",)) -> bytes:
    """Alter a fictional workbook to exercise malformed inputs."""
    book = load_workbook(BytesIO(template(subjects, True, "A")))
    for address, value in changes.items():
        sheet, cell = address.split("!")
        book[sheet][cell] = value
    output = BytesIO()
    book.save(output)
    return output.getvalue()


def test_exact_pass_boundary_and_sample_sd():
    result = summary(pd.Series([0, 39.99, 40, 100, np.nan]))
    assert result["Pass count"] == 2
    assert result["Pass %"] == 50
    assert result["Excluded"] == 1
    assert result["Std dev"] == pytest.approx(np.std([0, 39.99, 40, 100], ddof=1))
    assert np.isnan(summary(pd.Series([40]))["Std dev"])
    assert np.isnan(summary(pd.Series([np.nan]))["Pass %"])


def test_iqr_keeps_outliers_in_summary():
    values = pd.Series([50] * 8 + [100])
    assert outlier_mask(values).sum() == 1
    assert summary(values)["Mean"] > 50


def test_per_subject_exclusions_and_class_denominators():
    data = read_marks(template(("English", "Math"), True, "A"), ["English", "Math"])
    frame = data.frame.iloc[:3].copy()
    frame["English"] = [20, np.nan, 0]
    frame["Math"] = [80, 70, np.nan]
    maxima = {"English": 50, "Math": 100}
    pct = percentages(frame, maxima)
    assert pct.English.iloc[0] == 40
    students = student_results(frame, maxima)
    assert students["Average %"].tolist() == [60, 70, 0]
    assert students.Rank.iloc[0] == 1 and students.Rank.iloc[1:].isna().all()
    result = class_overview(students)
    assert result["Passed all %"] == 100
    assert result["Passed any %"] == pytest.approx(200 / 3)
    assert result["Mean"] == pytest.approx(130 / 3)


@pytest.mark.parametrize("stage", list(STAGES))
def test_curriculum(stage):
    cfg = STAGES[stage]
    if "pathways" not in cfg:
        assert len(resolve_subjects(stage)) in [6, 7, 8]
    else:
        for name, path in cfg["pathways"].items():
            opts = path.get("options", [])[: path.get("min", 0)]
            assert len(resolve_subjects(stage, name, opts, "Electrical")) >= 5


def test_invalid_electives_and_duplicate_tvet():
    with pytest.raises(ValueError):
        resolve_subjects("Key Stage 5", "Science", [])
    with pytest.raises(ValueError):
        resolve_subjects("Key Stage 5", "Science", ["TVET"], "English")


def test_template_validation_and_protection():
    raw = template(("English",), True, "A")
    data = read_marks(raw, ["English"], "A")
    assert not data.errors
    assert data.absent.English.sum() == 1
    assert data.frame.English.isna().sum() == 2
    book = load_workbook(BytesIO(raw))
    assert book["Marks"]["A1"].protection.locked
    assert not book["Marks"]["A2"].protection.locked
    assert len(book["Marks"].data_validations.dataValidation) == 2
    assert book.sheetnames == ["Marks", "Settings", "Instructions"]


@pytest.mark.parametrize(
    "change, message",
    [
        ({"Marks!F14": 105}, "Row 14, column English: value 105 exceeds maximum 100"),
        ({"Marks!F2": -1}, "below 0"),
        ({"Marks!F2": "oops"}, "expected a numeric mark"),
        ({"Marks!F2": "=1+1"}, "formulas are not accepted"),
        ({"Marks!C2": "Other"}, "column Gender"),
        ({"Marks!D2": "Unknown"}, "column Residence"),
        ({"Marks!A3": "A-001"}, "duplicate ID"),
        ({"Marks!B2": ""}, "Student Name: value is required"),
        ({"Marks!A1": "Student Name"}, "columns must match"),
        ({"Marks!E2": "B"}, "column Section: expected A"),
        ({"Settings!B2": 0}, "positive number"),
    ],
)
def test_row_specific_errors(change, message):
    result = read_marks(edited(change), ["English"], "A")
    assert any(message in e for e in result.errors)


def test_normalized_categories_and_headers():
    data = read_marks(
        edited({"Marks!A1": " student id ", "Marks!C2": "F", "Marks!D2": "Hostel"}),
        ["English"],
    )
    assert not data.errors
    assert data.frame.Gender.iloc[0] == "Female"
    assert data.frame.Residence.iloc[0] == "Boarder"


def test_corrupt_empty_and_mismatched_file():
    assert read_marks(b"not xlsx", ["English"]).errors
    assert read_marks(template(("English",)), ["English"]).errors
    assert read_marks(template(("Math",), True), ["English"]).errors


def test_sections_duplicate_and_scale_validation():
    a = read_marks(template(("English",), True, "A"), ["English"], "A")
    b = read_marks(template(("English",), True, "B"), ["English"], "B")
    assert not check_section_compatibility(b, {"A": a})
    assert check_section_compatibility(a, {"A": a})
    b.maxima["English"] = 50
    assert check_section_compatibility(b, {"A": a})


def test_missing_groups_and_no_data_diagnosis():
    data = read_marks(template(("English",), True), ["English"])
    frame = data.frame.copy()
    frame["Gender"] = "Female"
    pct = percentages(frame, data.maxima)
    comp = comparisons(frame, pct, "Gender")
    assert comp.iloc[0]["n"] == 0
    assert pd.isna(comp.iloc[0]["Mean"])
    pct["English"] = np.nan
    assert diagnosis(frame, pct).Diagnosis.iloc[0] == "No data"


def test_section_ties():
    a = read_marks(template(("English",), True, "A"), ["English"])
    b = a.frame.copy()
    b.Section = "B"
    table, _ = section_comparison(pd.concat([a.frame, b]), a.maxima)
    assert table.Rank.tolist() == [1, 1]


def test_blank_benchmarks_and_zero_reference():
    entries = blank_benchmarks(["English"], False)
    assert "National mean" not in entries
    current = pd.DataFrame(
        {"Subject": ["Overall", "English"], "Mean": [60, 60], "Pass %": [80, 80]}
    )
    diff, _, errors = compare_benchmarks(current, entries)
    assert diff.empty and not errors
    entries.loc[1, "Previous mean"] = 0
    diff, _, errors = compare_benchmarks(current, entries)
    assert diff["Difference (points)"].iloc[0] == 60
    entries.loc[1, "Previous mean"] = 101
    assert compare_benchmarks(current, entries)[2]


def test_six_hundred_students():
    """Large class keeps denominators and calculations stable."""
    subjects = STAGES["Key Stage 3"]["core"]
    data = read_marks(template(tuple(subjects), True), subjects)
    frame = pd.concat([data.frame] * 19, ignore_index=True).iloc[:600].copy()
    frame["Student ID"] = [str(i) for i in range(600)]
    result = student_results(frame, data.maxima)
    assert len(result) == 600
    assert class_overview(result)["Students"] == 600
    assert len(diagnosis(frame, percentages(frame, data.maxima))) == 8


def test_numeric_name_rejected_and_ambiguous_mode_unavailable():
    assert any(
        "Student Name: expected text" in e
        for e in read_marks(edited({"Marks!B2": 123}), ["English"]).errors
    )
    assert pd.isna(summary(pd.Series([1, 2, 3]))["Mode"])

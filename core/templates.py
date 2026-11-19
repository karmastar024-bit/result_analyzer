"""Dynamic openpyxl templates with protected headers and editable input cells."""

from io import BytesIO
from pathlib import Path
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Protection
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter
from core.subjects_config import IDENTITY


def styled_sheet(
    ws, headers: list[str], rows: list[list], capacity: int = 1000
) -> None:
    """Lock header cells; unlock a bounded teacher-entry area."""
    ws.append(headers)
    for row in rows:
        ws.append(row)
    ws.freeze_panes = "F2" if len(headers) > 5 else "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{max(2, len(rows) + 1)}"
    ws.row_dimensions[1].height = 60
    for i, heading in enumerate(headers, 1):
        letter = get_column_letter(i)
        ws.column_dimensions[letter].width = 24 if len(heading) < 30 else 32
        cell = ws.cell(1, i)
        cell.font = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
        cell.fill = PatternFill("solid", fgColor="19384A")
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        cell.protection = Protection(locked=True)
        for r in range(2, capacity + 2):
            c = ws.cell(r, i)
            c.protection = Protection(locked=False)
            if r <= max(len(rows) + 1, 12):
                c.fill = PatternFill(
                    "solid", fgColor="EFF5FA" if r % 2 == 0 else "FFFFFF"
                )
            if isinstance(c.value, str):
                c.data_type = "s"
    ws.protection.sheet = True
    ws.protection.autoFilter = False
    ws.protection.selectUnlockedCells = False
    ws.print_title_rows = "1:1"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0


def template(
    subjects: tuple[str, ...],
    sample: bool = False,
    section: str = "",
    maximum: float = 100,
    seed: int = 19,
) -> bytes:
    """Build a Marks/Settings/Instructions workbook entirely in memory."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Marks"
    rng = np.random.default_rng(seed)
    names = ["Sonam", "Pema", "Karma", "Tshering", "Deki", "Tashi", "Kezang", "Choden"]
    rows = []
    if sample:
        for i in range(32):
            marks = np.clip(rng.normal(62, 20, len(subjects)), 0, 100) * maximum / 100
            row = [
                f"{section or 'S'}-{i + 1:03}",
                f"{names[i % len(names)]} Sample {i + 1}",
                "Male" if i % 2 else "Female",
                "Boarder" if i % 3 else "Day Scholar",
                section,
            ]
            row += [round(float(v), 2) for v in marks]
            if i == 2:
                row[5] = "AB"
            if i == 5:
                row[-1] = None
            rows.append(row)
    styled_sheet(ws, IDENTITY + list(subjects), rows)
    for column, options in [("C", "Male,Female"), ("D", "Boarder,Day Scholar")]:
        rule = DataValidation(type="list", formula1=f'"{options}"', allow_blank=False)
        rule.showErrorMessage = True
        rule.errorTitle = "Choose a listed value"
        rule.error = f"Allowed: {options}"
        rule.errorStyle = "stop"
        ws.add_data_validation(rule)
        rule.add(f"{column}2:{column}1001")
    settings = wb.create_sheet("Settings")
    styled_sheet(
        settings,
        ["Subject", "Max Marks"],
        [[s, maximum] for s in subjects],
        len(subjects),
    )
    for row in range(2, len(subjects) + 2):
        settings.cell(row, 1).protection = Protection(locked=True)
    rule = DataValidation(type="decimal", operator="greaterThan", formula1=0)
    rule.showErrorMessage = True
    settings.add_data_validation(rule)
    rule.add(f"B2:B{len(subjects) + 1}")
    instructions = wb.create_sheet("Instructions")
    lines = [
        "Bhutan Result Analysis Tool - "
        + ("FICTIONAL SAMPLE DATA" if sample else "EMPTY TEMPLATE"),
        "Keep every column name and its order. Fill one student per row on Marks.",
        "Student ID must be unique across the grade. Student Name, Gender and Residence are required.",
        "Gender: Male/Female (M/F accepted). Residence: Boarder/Day Scholar (Hostel/Day-scholar accepted).",
        "Section is required for section comparison and must match the upload slot name.",
        "Enter numeric marks, AB for absent, or leave a mark blank. AB/blank are excluded per subject.",
        "Edit Max Marks on Settings before entering marks. Default maximum is 100.",
        "Pass means at least 40% of maximum marks. No formulas or totals rows are accepted.",
        "Headers and subject labels are protected. Input rows 2–1001 are unlocked.",
        "For more than 1000 students, unprotect the worksheet in Excel; the app accepts up to 10000.",
        "Sheet protection prevents accidental edits; it is not encryption or access control.",
        "All dummy sample names and marks are fictional. Remove them before entering real data.",
    ]
    instructions.column_dimensions["A"].width = 110
    for line in lines:
        instructions.append([line])
        cell = instructions.cell(instructions.max_row, 1)
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        instructions.row_dimensions[instructions.max_row].height = 32
    instructions["A1"].font = Font(bold=True, color="19384A", size=14)
    output = BytesIO()
    wb.save(output)
    return output.getvalue()


if __name__ == "__main__":
    folder = Path("sample_data")
    folder.mkdir(exist_ok=True)
    from core.subjects_config import STAGES

    selected = tuple(STAGES["Key Stage 1"]["core"])
    for sec in ["A", "B"]:
        (folder / f"section_{sec}_sample.xlsx").write_bytes(
            template(selected, True, sec, seed=ord(sec))
        )
    (folder / "subject_sample.xlsx").write_bytes(template(("English",), True))

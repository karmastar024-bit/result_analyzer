"""In-memory ReportLab reports; tables split horizontally and repeat headers."""

from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
import os
from threading import RLock
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape
from zoneinfo import ZoneInfo
import pandas as pd
from core.subjects_config import METHODS


def escape(value: str) -> str:
    """Use portable mathematical text while preserving Unicode student names."""
    replacements = {
        "−": "-",
        "–": "-",
        "—": "-",
        "×": " x ",
        "≥": ">=",
        "≤": "<=",
        "↑": "",
        "↓": "",
        "→": "",
        "’": "'",
        "…": "...",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return xml_escape(value)


@dataclass
class Report:
    """The same tables, interpretations and chart definitions shown in the UI."""

    title: str
    tables: list[tuple[str, pd.DataFrame]] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    charts: list = field(default_factory=list)


def font_path() -> Path | None:
    """Optional TrueType font supporting Tibetan and Latin characters."""
    configured = os.environ.get("DZONGKHA_FONT_PATH", "")
    if configured and Path(configured).is_file():
        return Path(configured)
    for name in ["Jomolhari.ttf", "NotoSerifTibetan-Regular.ttf"]:
        candidate = Path(__file__).resolve().parent.parent / "assets" / name
        if candidate.is_file():
            return candidate
    return None


_PDF_LOCK = RLock()


def build_pdf(report: Report, metadata: dict[str, str]) -> bytes:
    """Serialize font registration and matplotlib rendering within this process."""
    with _PDF_LOCK:
        return _build_pdf(report, metadata)


def _build_pdf(report: Report, metadata: dict[str, str]) -> bytes:
    """Build a landscape A4 report with a cover and page-numbered content."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        PageBreak,
        LongTable,
        TableStyle,
        Image,
    )
    from core.charts import image_bytes

    output = BytesIO()
    font = "Helvetica"
    path = font_path()
    if path:
        font = "Dzongkha"
        if font not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(font, str(path)))
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = font
    styles["Heading2"].keepWithNext = True
    body = ParagraphStyle(
        "ReportBody", parent=styles["BodyText"], fontName=font, fontSize=10, leading=15
    )
    small = ParagraphStyle(
        "ReportCell", parent=body, fontSize=8, leading=11, wordWrap="CJK"
    )
    header_style = ParagraphStyle("ReportHeader", parent=small, textColor=colors.white)
    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=24 * mm,
        bottomMargin=18 * mm,
        title=report.title,
        author=metadata.get("Teacher", ""),
    )
    date = datetime.now(ZoneInfo("Asia/Thimphu")).strftime("%d %B %Y, %H:%M BTT")
    story = [
        Spacer(1, 20 * mm),
        Paragraph(escape(report.title), styles["Title"]),
        Spacer(1, 10 * mm),
    ]
    for key, value in metadata.items():
        story.append(Paragraph(escape(f"{key}: {value or 'Not supplied'}"), body))
    story += [
        Paragraph("Generated: " + date, body),
        Spacer(1, 10 * mm),
        Paragraph("Definitions and ranking methods", styles["Heading2"]),
        Paragraph(escape(METHODS), body),
    ]
    if not path:
        story.append(
            Paragraph(
                "Dzongkha PDF text needs a configured Tibetan-capable TTF font; see README.",
                body,
            )
        )
    story.append(PageBreak())
    for text in report.texts:
        story.extend([Paragraph(escape(text), body), Spacer(1, 3 * mm)])
    for title, frame in report.tables:
        if frame.empty:
            story.extend(
                [
                    Paragraph(escape(title), styles["Heading2"]),
                    Paragraph("No matching records.", body),
                ]
            )
            continue
        # Repeat every necessary row identifier when wide tables are split.
        cols = list(frame.columns)
        identifiers = [cols[0]]
        if cols[0] in ("Subject", "Section"):
            identifiers = [
                c for c in cols if c in ("Subject", "Section", "Gender", "Residence")
            ]
        remaining = [c for c in cols if c not in identifiers]
        capacity = max(1, 8 - len(identifiers))
        groups = (
            [cols]
            if len(cols) <= 8
            else [
                identifiers + remaining[i : i + capacity]
                for i in range(0, len(remaining), capacity)
            ]
        )
        for part, columns in enumerate(groups):
            heading = title + (
                f" ({part + 1}/{len(groups)})" if len(groups) > 1 else ""
            )
            data = [[Paragraph(escape(str(c)), header_style) for c in columns]]
            for row in frame[columns].itertuples(index=False, name=None):
                cells = []
                for value in row:
                    text = (
                        "N/A"
                        if pd.isna(value)
                        else f"{value:.2f}"
                        if isinstance(value, float)
                        else str(value)
                    )
                    cells.append(Paragraph(escape(text), small))
                data.append(cells)
            widths = [doc.width / len(columns)] * len(columns)
            if "Reasons and recommendations" in columns:
                idx = columns.index("Reasons and recommendations")
                widths = [doc.width * 0.6 / (len(columns) - 1)] * len(columns)
                widths[idx] = doc.width * 0.4
            table = LongTable(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#19384A")),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#EFF5FA")],
                        ),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#19384A")),
                    ]
                )
            )
            story += [
                Paragraph(escape(heading), styles["Heading2"]),
                table,
                Spacer(1, 5 * mm),
            ]
    for chart in report.charts:
        image = Image(
            BytesIO(image_bytes(chart)), width=doc.width, height=doc.width * 0.48
        )
        story.extend([image, Spacer(1, 4 * mm)])

    def page(canvas, document):
        canvas.saveState()
        canvas.setFont(font, 8)
        school = metadata.get("School", "") or "Bhutan Result Analysis Tool"
        header = f"{school} | {metadata.get('Year', '')} | Class {metadata.get('Class', '')} | Section {metadata.get('Section', '')} | {date}"
        header_paragraph = Paragraph(escape(header), small)
        _, header_height = header_paragraph.wrap(doc.width, 18 * mm)
        header_paragraph.drawOn(
            canvas, 15 * mm, landscape(A4)[1] - 8 * mm - header_height
        )
        canvas.drawString(15 * mm, 10 * mm, "Bhutan Result Analysis Tool")
        canvas.drawRightString(
            landscape(A4)[0] - 15 * mm, 10 * mm, f"Page {document.page}"
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=page, onLaterPages=page)
    return output.getvalue()

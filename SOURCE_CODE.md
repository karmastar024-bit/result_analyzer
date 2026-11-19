# Bhutan Result Analysis Tool — complete source delivery


## 1. Assumptions

- The curriculum dictionary implements the supplied specification; it is not independently certified as current MoESD/BCSEA policy. The general IX/X pathway includes both listed subjects. TVET IX/X requires a named vocational subject with optional Economics.
- `PASS_PERCENT = 40` is defined once in `core/subjects_config.py`. Marks exactly at 40% pass. Classification uses unrounded percentages.
- All statistics and comparison charts use percentage marks, including the individual-subject page. Individual student lists also show raw marks. Average total marks is a raw-mark metric.
- Excel `Settings` is the supported alternative to a Max Marks row. Every upload requires `Marks` and `Settings` worksheets. Identity and subject columns must match exactly in order, ignoring case and surrounding whitespace. Section cells may be blank outside Module 3, but the column is always present.
- Blank and AB marks are excluded independently per subject. Other subjects for the same student remain included. AB and blank counts are displayed separately; neither becomes zero.
- Overall mean, median and sample SD use student averages across available subjects, with equal subject weighting. Complete-only totals and rankings prevent an incomplete student from receiving a misleading overall rank. Averages for incomplete students may use different subject sets.
- Passed-all rate uses complete students as its denominator. Passed-at-least-one rate uses students with at least one valid mark. Both denominators appear on screen and in reports. Observed failure counts include partial records. Group overall pass rates refer to available averages ≥40%, not passed-all rates.
- Mode is shown only when a unique mode exists; tied modes are reported as N/A.
- Sample SD uses `ddof=1`; n<2 yields N/A. Small samples n<5 display warnings. No-data subjects remain N/A, not zero. Outliers remain in all statistics.
- Diagnosis categories apply urgent rules first, then improvement, then Doing Well. All other assessed combinations are Satisfactory, resolving gaps in the suggested ranges. Thresholds and the descriptive 75% pass-rate benchmark reside in `DIAGNOSIS`.
- Subject strength is `0.5 × mean + 0.5 × pass%`. Section composite is `0.4 × passed-all% + 0.3 × mean + 0.2 × median + 0.1 × max(0,100−sample SD)`. A section needs at least two assessed students and one complete student for a rank. Ties share competition ranks (1,1,3). Subject-section winners use subject strength and list ties.
- Support lists include students failing ≥2 subjects or with at least one score from 40% to below 50%. Missing assessments have a separate follow-up table.
- Score bands labelled 0–39, 40–49 etc. are continuous intervals [0,40), [40,50), ..., [80,100].
- Previous-year benchmarks use one teacher-labelled year per analysis. Dzongkhag/national inputs are optional means, in percentages. Overall prior-year pass rate must use the same passed-all definition. No benchmark numbers are preloaded. The requested online-fetch hook always falls back honestly to manual input until a verified endpoint is configured.

## 2. Project folder tree

```text
app.py
core/
  subjects_config.py   curriculum, thresholds, constants and methods
  validators.py        strict, row-specific Excel validation
  templates.py         dynamic openpyxl templates and fictional samples
  stats.py             pure analytical functions
  charts.py            Plotly charts and matplotlib PDF equivalents
  benchmarks.py        manual comparisons and safe national-source hook
  pdf_report.py        in-memory ReportLab reports
views/
  common.py            selection, uploads, tables, PDF controls
  individual.py        Module 1
  class_result.py      Module 2 and shared whole-grade views
  sections.py          Module 3 and benchmarks
assets/theme.css
static/classroom.jpg
static/valley.jpg
sample_data/            generated fictional examples
.streamlit/config.toml
requirements.txt
requirements-dev.txt
tests/
README.md
MANUAL_TESTS.md
SOURCE_CODE.md          full text-source listing in requested delivery order
```

## 3. Full source code

Each text source file is included in full. Binary artwork, the browser font, and fictional Excel samples are included in the ZIP. They are not source code and are not represented as code blocks. The template generator is in section 4; requirements and README follow in sections 5 and 6.

### app.py

````python
"""Bhutan Result Analysis Tool: Streamlit entry point and sidebar navigation."""

from base64 import b64encode
from functools import lru_cache
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import streamlit as st
from core.subjects_config import METHODS
from views import individual, class_result, sections

# Detach selection widget keys from Streamlit cleanup when pages are unmounted.
for saved_key in list(st.session_state):
    if saved_key.startswith(
        (
            "class_stage",
            "class_class",
            "class_path",
            "class_choices",
            "class_tvet",
            "sections_stage",
            "sections_class",
            "sections_path",
            "sections_choices",
            "sections_tvet",
            "individual_subject",
            "individual_maximum",
        )
    ):
        st.session_state[saved_key] = st.session_state[saved_key]

ROOT = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def tibetan_style() -> str:
    """Embed the reference app's licensed Tibetan font for browser display."""
    encoded = b64encode((ROOT / "assets/tibetan.woff2").read_bytes()).decode("ascii")
    return (
        "<style>@font-face{font-family:'Result Tibetan';font-display:swap;"
        "unicode-range:U+0F00-0FFF;src:url(data:font/woff2;base64,"
        + encoded
        + ") format('woff2')}"
        ".stApp{font-family:'Source Sans 3','Result Tibetan',sans-serif}</style>"
    )


st.set_page_config(
    page_title="Bhutan Result Analysis Tool",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto",
)
st.html(ROOT / "assets/theme.css")
st.html(tibetan_style())


def navigate(page_name: str) -> None:
    """Home cards use the same navigation state as the sidebar."""
    st.session_state["navigation"] = page_name


with st.sidebar:
    st.markdown(
        '<p class="sidebar-brand">Result analysis</p><p class="sidebar-kicker">For teachers in Bhutan</p>',
        unsafe_allow_html=True,
    )
    page = st.radio(
        "Navigation",
        [
            "Home",
            "Individual Subject Analysis",
            "Class Result Analysis",
            "Section Comparison",
            "Help/Instructions",
        ],
        key="navigation",
        label_visibility="collapsed",
    )
    st.divider()
    with st.expander("School & report details", expanded=True):
        school = st.text_input(
            "School Name", key="school_name", placeholder="Your school"
        )
        year = st.number_input(
            "Academic Year",
            2000,
            2100,
            datetime.now(ZoneInfo("Asia/Thimphu")).year,
            key="academic_year",
        )
        teacher = st.text_input(
            "Teacher Name", key="teacher_name", placeholder="Prepared by"
        )
    with st.expander("Session & privacy"):
        st.caption(
            "Files are processed in server memory. Hosted use sends files to the server. "
            "The app does not intentionally save student records to disk or a database."
        )
        if st.button("Clear session data", width="stretch"):
            for key in list(st.session_state):
                if key not in ["school_name", "academic_year", "teacher_name"]:
                    del st.session_state[key]
            st.rerun()
    st.caption("40% pass threshold · Excel uploads")

if page != "Home":
    st.html('<span class="workspace-compact"></span>')
with st.container(key="valley_art"):
    st.image(str(ROOT / "static/valley.jpg"), width="stretch")
with st.container(key="school_header"):
    with st.container(key="classroom_art"):
        st.image(str(ROOT / "static/classroom.jpg"), width="stretch")
    st.markdown(
        '<p class="ia-eyebrow">Assessment workspace</p>'
        '<p class="ia-title">Bhutan Result Analysis Tool</p>'
        '<p class="ia-sub">A clearer picture of learning.<br>From your mark sheet to the next lesson.</p>',
        unsafe_allow_html=True,
    )
metadata = {"School": school, "Year": str(year), "Teacher": teacher}
if page == "Home":
    st.header("What would you like to understand?")
    st.caption(
        "Choose an analysis to get started. Each workspace includes a matching Excel template and a fictional sample."
    )
    modules = [
        (
            "subject",
            "01",
            "Individual subject",
            "Look closely at one subject.",
            "Score distribution · Outliers · Group comparisons",
            "Analyse a subject",
            "Individual Subject Analysis",
        ),
        (
            "class",
            "02",
            "Class results",
            "See the whole class, subject by subject.",
            "Pass rates · Subject diagnosis · Student support",
            "Analyse a class",
            "Class Result Analysis",
        ),
        (
            "sections",
            "03",
            "Section comparison",
            "Bring the grade’s results together.",
            "Section rankings · Grade overview · Benchmarks",
            "Compare sections",
            "Section Comparison",
        ),
    ]
    for column, (key, number, title, description, detail, action, target) in zip(
        st.columns(3), modules
    ):
        with column:
            with st.container(border=True, key="module_" + key):
                st.markdown(
                    f'<span class="module-symbol">{number}</span>',
                    unsafe_allow_html=True,
                )
                st.subheader(title)
                st.write(description)
                st.markdown(
                    f'<p class="module-detail">{detail}</p>', unsafe_allow_html=True
                )
                st.button(
                    action,
                    key="open_" + key,
                    type="primary",
                    width="stretch",
                    on_click=navigate,
                    args=(target,),
                )
    st.markdown(
        '<div class="workflow-note"><span><strong>1</strong> Get your template</span>'
        "<span><strong>2</strong> Upload your marks</span><span><strong>3</strong> Review and export</span></div>",
        unsafe_allow_html=True,
    )
    st.info(
        "Pass mark: 40% of each subject’s maximum. Blank and AB marks are excluded per subject and counted separately."
    )
elif page == "Individual Subject Analysis":
    individual.render(metadata)
elif page == "Class Result Analysis":
    class_result.render(metadata)
elif page == "Section Comparison":
    sections.render(metadata)
else:
    st.header("Help / Instructions")
    st.subheader("Prepare and upload")
    st.write(
        "Select the stage, class and pathway first. Download that exact template. Keep identity and subject columns "
        "in order; fill the Marks sheet and edit maximum marks on Settings. Gender and Residence dropdowns are included. "
        "Section is mandatory for section comparison. Header protection prevents accidental edits; it is not security."
    )
    st.write(
        "Student ID must be unique across all uploaded sections. Use Male/Female (M/F accepted) and "
        "Boarder/Day Scholar (Hostel/Day-scholar accepted). Enter numeric marks, AB, or blank. "
        "Do not use formulas or summary rows. Up to 10,000 students and 10 MB per file are supported."
    )
    st.subheader("Statistics and rankings")
    st.write(METHODS)
    st.write(
        "Score-band labels 0–39, 40–49 and so on represent continuous intervals: 0≤x<40, "
        "40≤x<50, …, 80≤x≤100. Pass status uses unrounded percentages."
    )
    st.subheader("Diagnosis rules")
    st.write(
        "Urgent: pass<60% OR mean<45%. Improvement: pass<75% OR mean<55%, after urgent. "
        "Doing Well: pass≥90% AND mean≥65%. All other assessed combinations are Satisfactory. "
        "SD>20 points suggests differentiated teaching; group mean gaps≥10 points suggest investigation. "
        "Settings are editable in core/subjects_config.py. These are descriptive project rules."
    )
    st.subheader("Reports and Dzongkha")
    st.write(
        "Enter school, year and teacher in the sidebar. Prepare a PDF, then download it. "
        "Name visibility and optional student lists follow the on-screen toggles. "
        "To support Dzongkha, put Jomolhari.ttf or NotoSerifTibetan-Regular.ttf in assets, "
        "or set DZONGKHA_FONT_PATH to the font file. Verify stacked Tibetan glyphs in your deployment; "
        "font embedding alone may not provide full complex-script shaping."
    )
    st.subheader("Benchmarks and privacy")
    st.write(
        "Benchmarks are entered manually and remain optional. National input is shown only for VI, VIII, X and XII. "
        "The online-source hook intentionally falls back to manual entry because no verified endpoint is configured. "
        "No published benchmark figures are bundled. Uploaded data stays in the current session; "
        "refreshing or losing the server session may require uploading again."
    )
st.markdown(
    '<div class="result-footer"><span>Bhutan Result Analysis Tool</span><span>Made for educators in Bhutan</span></div>',
    unsafe_allow_html=True,
)
````


### core/__init__.py

````python
"""Pure analysis, validation, templates, and reporting services."""
````


### core/benchmarks.py

````python
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
````


### core/charts.py

````python
"""Shared chart specifications rendered interactively or into PDF images."""

from dataclasses import dataclass
from io import BytesIO
import textwrap
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import gaussian_kde
from core.subjects_config import COLORS, PASS_PERCENT


@dataclass
class Chart:
    """Portable chart definition: screen and PDF share exactly the same data."""

    title: str
    kind: str
    data: pd.DataFrame
    x: str = ""
    y: str = ""
    group: str | None = None
    pass_line: bool = False


def interactive(chart: Chart) -> go.Figure:
    """Plotly figures with readable labels and explicit numerical hover data."""
    d = chart.data
    if chart.kind == "distribution":
        values = d[chart.x].dropna()
        fig = go.Figure(
            go.Histogram(
                x=values,
                xbins=dict(start=0, end=100, size=10),
                name="Students",
                marker_color="#3288D1",
                hovertemplate="Score bin %{x}%<br>Students %{y}<extra></extra>",
            )
        )
        if len(values) >= 2 and values.nunique() > 1:
            grid = np.linspace(0, 100, 250)
            density = gaussian_kde(values)(grid) * len(values) * 10
            fig.add_trace(
                go.Scatter(
                    x=grid, y=density, name="KDE (count scale)", line_color="#D84B9B"
                )
            )
        for name, val, color in [
            ("Mean", values.mean(), "#2C9B73"),
            ("Median", values.median(), "#E88A32"),
        ]:
            if pd.notna(val):
                fig.add_vline(
                    x=val,
                    line_color=color,
                    annotation_text=f"{name} {val:.2f}",
                    annotation_position="top left"
                    if name == "Mean"
                    else "bottom right",
                )
        fig.add_vrect(
            x0=0, x1=PASS_PERCENT, fillcolor="red", opacity=0.08, line_width=0
        )
        fig.update_xaxes(title="Score (%)", range=[0, 100])
        fig.update_yaxes(title="Students (KDE scaled to bin counts)")
    elif chart.kind == "heatmap":
        fig = px.imshow(
            d,
            text_auto=".2f",
            aspect="auto",
            color_continuous_scale="Blues",
            labels={
                "x": d.columns.name or "Subject",
                "y": d.index.name or "Section",
                "color": chart.y,
            },
        )
    elif chart.kind == "box":
        fig = px.box(
            d,
            x=chart.x,
            y=chart.y,
            color=chart.group,
            points="outliers",
            color_discrete_map=COLORS,
            labels={chart.y: "Score (%)"},
        )
    else:
        fig = px.bar(
            d,
            x=chart.x,
            y=chart.y,
            color=chart.group,
            barmode="group",
            text_auto=".2f",
            color_discrete_map=COLORS,
            hover_data={c: ":.2f" for c in d.select_dtypes("number").columns},
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        title=dict(text=chart.title, font_size=18),
        template="plotly_dark",
        paper_bgcolor="#142c3d",
        plot_bgcolor="#142c3d",
        margin=dict(t=80, b=100),
        legend_title_text=chart.group or "",
        font=dict(size=13, color="#d5e3ea", family="Source Sans 3, sans-serif"),
        colorway=["#75b8c7", "#d9b477", "#a3e1d2", "#a89cdb"],
        height=470,
    )
    fig.update_xaxes(showgrid=False, automargin=True, title_standoff=18)
    fig.update_yaxes(
        gridcolor="#314958", zerolinecolor="#496170", automargin=True, title_standoff=18
    )
    if chart.pass_line:
        fig.add_hline(
            y=PASS_PERCENT,
            line_dash="dash",
            line_color="#C13B43",
            annotation_text="Pass threshold 40%",
        )
    return fig


def image_bytes(chart: Chart) -> bytes:
    """Render a static counterpart with matplotlib, without a browser dependency."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from core.pdf_report import font_path
    from matplotlib.font_manager import FontProperties

    font = FontProperties(fname=str(font_path())) if font_path() else None
    with plt.rc_context({"font.size": 10}):
        fig, ax = plt.subplots(figsize=(10, 4.8), layout="constrained")
        d = chart.data
        if chart.kind == "distribution":
            values = d[chart.x].dropna()
            ax.hist(
                values, bins=np.arange(0, 101, 10), color="#3288D1", edgecolor="white"
            )
            if len(values) >= 2 and values.nunique() > 1:
                grid = np.linspace(0, 100, 250)
                ax.plot(
                    grid,
                    gaussian_kde(values)(grid) * len(values) * 10,
                    color="#D84B9B",
                    label="KDE",
                )
            for name, value, color in [
                ("Mean", values.mean(), "#2C9B73"),
                ("Median", values.median(), "#E88A32"),
            ]:
                if pd.notna(value):
                    ax.axvline(value, color=color, label=f"{name} {value:.2f}")
            ax.axvspan(0, PASS_PERCENT, color="red", alpha=0.08)
            ax.set(xlabel="Score (%)", ylabel="Students", xlim=(0, 100))
            if len(values):
                ax.legend(fontsize=8)
        elif chart.kind == "heatmap":
            array = d.to_numpy(dtype=float)
            image = ax.imshow(np.ma.masked_invalid(array), aspect="auto", cmap="Blues")
            fig.colorbar(image, ax=ax, label=chart.y)
            ax.set_xticks(
                range(len(d.columns)),
                [textwrap.fill(str(c), 16) for c in d.columns],
                rotation=30,
                ha="right",
            )
            ax.set_yticks(range(len(d)), d.index)
            for r in range(len(d)):
                for c in range(len(d.columns)):
                    ax.text(
                        c,
                        r,
                        f"{array[r, c]:.2f}" if np.isfinite(array[r, c]) else "NA",
                        ha="center",
                        va="center",
                        fontsize=8,
                        color="white"
                        if np.isfinite(array[r, c]) and image.norm(array[r, c]) > 0.55
                        else "black",
                    )
            ax.set(xlabel="Subject", ylabel="Section")
        elif chart.kind == "box":
            labels = list(d[chart.x].unique())
            arrays = [
                d.loc[d[chart.x].eq(v), chart.y].dropna().to_numpy() for v in labels
            ]
            ax.boxplot(arrays, tick_labels=[textwrap.fill(str(x), 16) for x in labels])
            ax.set(xlabel=chart.x, ylabel="Score (%)")
        else:
            if chart.group:
                pivot = d.pivot(index=chart.x, columns=chart.group, values=chart.y)
            else:
                pivot = d.set_index(chart.x)[[chart.y]]
            x = np.arange(len(pivot))
            width = 0.8 / max(1, len(pivot.columns))
            for j, group in enumerate(pivot.columns):
                values = pivot[group].to_numpy(dtype=float)
                bars = ax.bar(
                    x - 0.4 + width / 2 + j * width,
                    values,
                    width,
                    label=str(group),
                    color=COLORS.get(group),
                )
                ax.bar_label(
                    bars,
                    labels=[f"{v:.2f}" if np.isfinite(v) else "" for v in values],
                    fontsize=7,
                    padding=2,
                )
            ax.set_xticks(
                x,
                [textwrap.fill(str(v), 16) for v in pivot.index],
                rotation=25,
                ha="right",
            )
            ax.set(xlabel=chart.x, ylabel=chart.y)
            if chart.group:
                ax.legend(fontsize=8)
            ax.margins(y=0.2)
        if chart.pass_line:
            ax.axhline(PASS_PERCENT, color="#C13B43", linestyle="--", label="40% pass")
        ax.set_title(textwrap.fill(chart.title, 85), fontsize=12, fontproperties=font)
        if font:
            for label in ax.get_xticklabels() + ax.get_yticklabels():
                label.set_fontproperties(font)
        output = BytesIO()
        fig.savefig(output, format="png", dpi=140)
        plt.close(fig)
        return output.getvalue()
````


### core/pdf_report.py

````python
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
````


### core/stats.py

````python
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
````


### core/subjects_config.py

````python
"""User-specified curriculum and analytical settings; not official policy advice."""

PASS_PERCENT = 40
IDENTITY = ["Student ID", "Student Name", "Gender", "Residence", "Section"]
STAGES = {
    "Key Stage 1": {
        "classes": ["PP", "I", "II", "III"],
        "core": [
            "Dzongkha",
            "English",
            "Mathematics",
            "Science & Technology",
            "Health & Physical Education",
            "Arts Education",
        ],
    },
    "Key Stage 2": {
        "classes": ["IV", "V", "VI"],
        "core": [
            "Dzongkha",
            "English",
            "Mathematics",
            "Science",
            "Social Studies (History & Geography)",
            "Health & Physical Education",
            "Arts Education & ICT",
        ],
    },
    "Key Stage 3": {
        "classes": ["VII", "VIII"],
        "core": [
            "Dzongkha",
            "English",
            "Mathematics",
            "Science",
            "History",
            "Geography",
            "Health & Physical Education",
            "Digital Technology / ICT",
        ],
    },
    "Key Stage 4": {
        "classes": ["IX", "X"],
        "core": [
            "Dzongkha",
            "English",
            "Mathematics",
            "Science (Physics, Chemistry, Biology)",
            "History & Geography",
        ],
        "pathways": {
            "General School Pathway": {
                "core": ["Economics", "Digital Technology & Innovation"]
            },
            "TVET School Pathway": {
                "core": ["TVET"],
                "options": ["Economics"],
                "min": 0,
                "max": 1,
            },
        },
    },
    "Key Stage 5": {
        "classes": ["XI", "XII"],
        "core": ["Dzongkha", "English"],
        "pathways": {
            "Science": {
                "core": ["Physics", "Chemistry"],
                "options": ["Biology", "Mathematics", "DTI", "Rigzhung", "TVET"],
                "min": 1,
                "max": 2,
            },
            "Commerce": {
                "core": ["Commerce", "Accountancy"],
                "options": [
                    "Economics",
                    "Business Mathematics / Math",
                    "DTI",
                    "Rigzhung",
                    "TVET",
                ],
                "min": 1,
                "max": 2,
            },
            "Arts/Humanities": {
                "core": [],
                "options": [
                    "Geography",
                    "History",
                    "Economics",
                    "Business Mathematics / Math",
                    "English Literature",
                    "Rigzhung",
                    "DTI",
                    "TVET",
                ],
                "min": 3,
                "max": 4,
            },
        },
    },
}
DIAGNOSIS = {
    "urgent_pass": 60,
    "urgent_mean": 45,
    "improve_pass": 75,
    "improve_mean": 55,
    "well_pass": 90,
    "well_mean": 65,
    "high_std": 20,
    "group_gap": 10,
    "pass_benchmark": 75,
}
COLORS = {
    "Male": "#3288D1",
    "Female": "#D84B9B",
    "Boarder": "#2C9B73",
    "Day Scholar": "#E88A32",
}
METHODS = (
    "Pass threshold: 40% (inclusive). All subject statistics use percentage marks. "
    "Blank/AB marks are excluded independently per subject, never converted to zero. "
    "Standard deviation uses ddof=1 and is unavailable for n<2. "
    "Student averages equally weight available subject percentages; total marks and "
    "rankings require complete records. Passed all subjects uses complete students; "
    "passed at least one uses students with at least one valid mark. "
    "Overall mean/median/std use available student averages. "
    "IQR outliers lie below Q1-1.5×IQR or above Q3+1.5×IQR. "
    "Subject strength = 0.5×mean + 0.5×pass%. "
    "Section composite = 0.4×all-subject pass% + 0.3×mean + 0.2×median "
    "+ 0.1×max(0,100-std). A section needs at least two assessed students and "
    "one complete student to receive a composite. Ties share competition rank. "
    "Diagnosis applies urgent and improvement rules first, then Doing Well; "
    "all remaining combinations are Satisfactory. Comparisons are descriptive, not causal."
)


def resolve_subjects(
    stage: str, pathway: str = "", choices: list[str] | None = None, tvet: str = ""
) -> list[str]:
    """Validate elective counts and resolve the school-specific TVET column."""
    config = STAGES[stage]
    result = list(config["core"])
    if "pathways" in config:
        path = config["pathways"][pathway]
        choices = choices or []
        if not path.get("min", 0) <= len(choices) <= path.get("max", 0):
            raise ValueError(
                f"Choose {path.get('min', 0)}–{path.get('max', 0)} optional subjects."
            )
        if any(c not in path.get("options", []) for c in choices):
            raise ValueError("An optional subject is not valid for this pathway.")
        result += path["core"] + choices
    if "TVET" in result:
        if not tvet.strip():
            raise ValueError("Enter the school-specific TVET subject name.")
        result = [tvet.strip() if s == "TVET" else s for s in result]
    keys = [s.strip().casefold() for s in result]
    if len(keys) != len(set(keys)) or set(keys) & {
        s.casefold() for s in IDENTITY + ["Overall", "Overall average"]
    }:
        raise ValueError(
            "Subject names must be unique and distinct from identity columns."
        )
    return result
````


### core/validators.py

````python
"""Strict workbook validation with original Excel row numbers."""

from dataclasses import dataclass, field
from io import BytesIO
import math
from zipfile import BadZipFile, ZipFile
import pandas as pd
from openpyxl import load_workbook
from core.subjects_config import IDENTITY


@dataclass
class ValidatedData:
    """Validated records and separate absence flags, retained only in session memory."""

    frame: pd.DataFrame
    maxima: dict[str, float]
    absent: pd.DataFrame
    errors: list[str] = field(default_factory=list)


def normalized(value: object) -> str:
    """Normalize headers and categorical values without changing student names."""
    return str(value or "").strip().casefold()


def read_marks(
    raw: bytes,
    subjects: list[str],
    required_section: str | None = None,
    expected_max: float | None = None,
) -> ValidatedData:
    """Reject reordered/extra columns, formulas, invalid identities and invalid marks."""
    errors: list[str] = []
    empty = ValidatedData(pd.DataFrame(), {}, pd.DataFrame(), errors)
    try:
        if len(raw) > 10 * 1024 * 1024:
            raise ValueError("File exceeds 10 MB.")
        with ZipFile(BytesIO(raw)) as archive:
            if sum(f.file_size for f in archive.infolist()) > 80 * 1024 * 1024:
                raise ValueError("Workbook expands beyond the 80 MB safety limit.")
        book = load_workbook(BytesIO(raw), read_only=True, data_only=False)
        if not {"Marks", "Settings"}.issubset(book.sheetnames):
            raise ValueError(
                "Required worksheets: Marks and Settings. Download a new template."
            )
        ws = book["Marks"]
        if ws.max_row > 10001 or ws.max_column > 50:
            raise ValueError("Maximum supported size: 10,000 students and 50 columns.")
        rows = list(ws.iter_rows(values_only=True))
        expected = IDENTITY + subjects
        if not rows or [normalized(v) for v in rows[0]] != [
            normalized(v) for v in expected
        ]:
            raise ValueError(
                "Marks row 1: columns must match this exact order: "
                + ", ".join(expected)
            )
        setting_rows = list(book["Settings"].iter_rows(values_only=True))
        if not setting_rows or [normalized(x) for x in setting_rows[0]] != [
            "subject",
            "max marks",
        ]:
            raise ValueError("Settings row 1 must contain Subject, Max Marks.")
        supplied = [r for r in setting_rows[1:] if any(x is not None for x in r)]
        if [normalized(r[0]) for r in supplied] != [normalized(s) for s in subjects]:
            raise ValueError(
                "Settings subjects must match the selected subjects in order."
            )
        maxima = {}
        for row_no, (subject, row) in enumerate(zip(subjects, supplied), 2):
            value = row[1]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value <= 0
            ):
                errors.append(
                    f"Settings row {row_no}, column Max Marks: enter a positive number."
                )
            else:
                maxima[subject] = float(value)
        if (
            expected_max is not None
            and maxima
            and any(v != expected_max for v in maxima.values())
        ):
            errors.append(
                f"Settings: maximum must match the selected maximum {expected_max:g}."
            )
        if errors:
            return empty
        data, row_numbers = [], []
        for row_no, row in enumerate(rows[1:], 2):
            if all(v is None or str(v).strip() == "" for v in row):
                continue
            data.append(list(row))
            row_numbers.append(row_no)
        if not data:
            raise ValueError("Marks contains no student records.")
        frame = pd.DataFrame(data, columns=expected)
        absent = pd.DataFrame(False, index=frame.index, columns=subjects)
        seen: set[str] = set()
        gender = {"male": "Male", "m": "Male", "female": "Female", "f": "Female"}
        residence = {
            "boarder": "Boarder",
            "hostel": "Boarder",
            "day scholar": "Day Scholar",
            "day-scholar": "Day Scholar",
            "dayscholar": "Day Scholar",
        }
        for i, row_no in enumerate(row_numbers):
            name_value = frame.at[i, "Student Name"]
            if pd.notna(name_value) and not isinstance(name_value, str):
                errors.append(f"Row {row_no}, column Student Name: expected text.")
            for column in expected:
                value = frame.at[i, column]
                if isinstance(value, str) and value.startswith("="):
                    errors.append(
                        f"Row {row_no}, column {column}: formulas are not accepted; paste values."
                    )
            for column in IDENTITY:
                v = frame.at[i, column]
                frame.at[i, column] = "" if pd.isna(v) else str(v).strip()
            for column in ["Student ID", "Student Name"]:
                if not frame.at[i, column]:
                    errors.append(f"Row {row_no}, column {column}: value is required.")
            sid = frame.at[i, "Student ID"].casefold()
            if sid in seen:
                errors.append(
                    f"Row {row_no}, column Student ID: duplicate ID {frame.at[i, 'Student ID']}."
                )
            seen.add(sid)
            for column, mapping in [("Gender", gender), ("Residence", residence)]:
                key = normalized(frame.at[i, column])
                if key not in mapping:
                    errors.append(
                        f"Row {row_no}, column {column}: allowed values are {', '.join(dict.fromkeys(mapping.values()))}."
                    )
                else:
                    frame.at[i, column] = mapping[key]
            if required_section is not None:
                if normalized(frame.at[i, "Section"]) != normalized(required_section):
                    errors.append(
                        f"Row {row_no}, column Section: expected {required_section}."
                    )
                else:
                    frame.at[i, "Section"] = required_section
            for subject in subjects:
                value = frame.at[i, subject]
                if pd.isna(value) or str(value).strip() == "":
                    frame.at[i, subject] = float("nan")
                elif normalized(value) == "ab":
                    absent.at[i, subject] = True
                    frame.at[i, subject] = float("nan")
                else:
                    try:
                        number = float(value)
                        if isinstance(value, bool) or not math.isfinite(number):
                            raise ValueError
                        if number < 0:
                            errors.append(
                                f"Row {row_no}, column {subject}: value {number:g} is below 0."
                            )
                        elif number > maxima[subject]:
                            errors.append(
                                f"Row {row_no}, column {subject}: value {number:g} exceeds maximum {maxima[subject]:g}."
                            )
                        frame.at[i, subject] = number
                    except (TypeError, ValueError):
                        errors.append(
                            f"Row {row_no}, column {subject}: expected a numeric mark, blank, or AB; found {value!r}."
                        )
        book.close()
        if errors:
            return empty
        frame[subjects] = frame[subjects].astype(float)
        return ValidatedData(frame, maxima, absent)
    except (ValueError, BadZipFile, KeyError, OSError, TypeError) as exc:
        errors.append(str(exc))
        return empty
    except Exception:
        errors.append(
            "Cannot read this workbook. Use an unencrypted .xlsx file created from the template."
        )
        return empty


def check_section_compatibility(
    candidate: ValidatedData, others: dict[str, ValidatedData]
) -> list[str]:
    """Reject conflicting scales or duplicate IDs across the grade."""
    errors = []
    for name, other in others.items():
        if candidate.maxima != other.maxima:
            errors.append(f"Subjects or maximum marks differ from section {name}.")
        duplicate = set(candidate.frame["Student ID"].str.casefold()) & set(
            other.frame["Student ID"].str.casefold()
        )
        if duplicate:
            errors.append(
                f"Student IDs already present in section {name}: {', '.join(sorted(duplicate))}."
            )
    return errors
````


### views/__init__.py

````python
"""Streamlit pages and reusable controls."""
````


### views/class_result.py

````python
"""Class and whole-grade analysis components."""

import pandas as pd
import streamlit as st
from core.stats import (
    percentages,
    subject_stats,
    student_results,
    class_overview,
    comparisons,
    comparison_text,
    diagnosis,
)
from core.charts import Chart
from core.pdf_report import Report
from views.common import (
    selection,
    uploader,
    metrics,
    table,
    chart,
    text,
    report_download,
)


def group_results(
    frame: pd.DataFrame, pct: pd.DataFrame, report: Report, overall: bool = False
) -> None:
    """Group means and pass rates, with per-subject exclusions and denominators."""
    for group in ["Gender", "Residence"]:
        data = pct.copy()
        if overall:
            data["Overall average"] = pct.mean(axis=1)
        comp = comparisons(frame, data, group)
        table(report, group + " statistics", comp)
        for metric in ["Mean", "Pass %"]:
            chart(
                report,
                Chart(
                    f"{group}: {metric} by subject",
                    "bar",
                    comp,
                    "Subject",
                    metric,
                    group,
                ),
            )
        for subject in data:
            text(report, comparison_text(comp, group, subject))
        if (comp["n"] < 5).any():
            st.warning(
                f"Some {group.lower()} comparison groups have fewer than 5 valid marks."
            )
        if overall:
            text(
                report,
                "Overall group pass % measures available student averages ≥40%; it is distinct from passing all subjects.",
            )


def class_content(
    frame: pd.DataFrame,
    maxima: dict,
    report: Report,
    key: str,
    whole_grade: bool = False,
) -> None:
    """Collect all class outputs for either the class or combined-grade report."""
    pct = percentages(frame, maxima)
    results = student_results(frame, maxima)
    overview = class_overview(results)
    overview_values = {
        k: overview[k]
        for k in [
            "Students",
            "Assessed n",
            "Complete n",
            "Mean",
            "Passed all %",
            "Passed any %",
            "Average total marks",
            "Failing 1",
            "Failing 2",
            "Failing 3+",
        ]
    }
    metrics(overview_values)
    text(
        report,
        f"Passed all denominator: {overview['Complete n']} complete records. "
        f"Passed any denominator: {overview['Assessed n']} students with at least one valid mark. "
        "Available subject averages contribute to class mean; totals and rankings require complete records. "
        "Failure counts count observed failures, including students with other missing marks.",
    )
    table(report, "Class overview", pd.DataFrame([overview_values]))
    stats = subject_stats(pct)
    tabs = st.tabs(
        [
            "Subject statistics",
            "Charts",
            "Group comparisons",
            "Diagnosis",
            "Student support",
        ]
    )
    with tabs[0]:
        table(report, "Per-subject statistics (%)", stats, heat=True)
        small = stats.loc[stats["n"] < 5, "Subject"].tolist()
        if small:
            st.warning("Small samples (n<5): " + ", ".join(small))
    with tabs[1]:
        chart(
            report,
            Chart(
                "Mean percentage by subject",
                "bar",
                stats,
                "Subject",
                "Mean",
                pass_line=True,
            ),
        )
        chart(
            report,
            Chart("Pass percentage by subject", "bar", stats, "Subject", "Pass %"),
        )
        long = pct.melt(var_name="Subject", value_name="Score %")
        chart(
            report, Chart("Score spread by subject", "box", long, "Subject", "Score %")
        )
    with tabs[2]:
        group_results(frame, pct, report, whole_grade)
    with tabs[3]:
        diagnosed = diagnosis(frame, pct)
        st.caption(
            "Subject strength = 50% mean + 50% pass rate. Thresholds are configurable in core/subjects_config.py."
        )
        colors = {
            "Needs Urgent Attention": "#8c2532",
            "Needs Improvement": "#86531e",
            "Satisfactory": "#236789",
            "Doing Well": "#247454",
            "No data": "#555555",
        }
        st.dataframe(
            diagnosed.style.format(precision=2, na_rep="N/A").map(
                lambda v: f"background-color: {colors[v]}; color: white",
                subset=["Diagnosis"],
            ),
            hide_index=True,
            width="stretch",
        )
        report.tables.append(("Subject diagnosis and strength ranking", diagnosed))
        for _, row in diagnosed.iterrows():
            text(
                report,
                f"{row.Subject}: {row['Diagnosis']}. {row['Reasons and recommendations']}",
            )
    with tabs[4]:
        hide = st.toggle("Hide student names", value=True, key=key + "_hide")
        display = results.drop(columns=["Student Name"]) if hide else results
        top = display[display.Rank.le(10)].sort_values(["Rank", "Student ID"])
        table(report, "Top 10 rank positions (ties included)", top)
        if st.toggle("Show students needing support", key=key + "_support"):
            mask = results["Failed subjects"].ge(2) | results["Borderline subjects"].gt(
                0
            )
            table(report, "Students needing support", display[mask])
        table(
            report,
            "Incomplete records for follow-up",
            display[display["Excluded subjects"].gt(0)],
        )


def render(metadata: dict) -> None:
    """Single class upload and complete report."""
    st.header("Class Result Analysis")
    subjects, grade = selection("class")
    if not subjects:
        return
    data = uploader(subjects, "class")
    if data is None:
        return
    report = Report(f"Class {grade}: result analysis")
    class_content(data.frame, data.maxima, report, "class")
    report_download(
        report, {**metadata, "Class": grade, "Section": "All uploaded"}, "class"
    )
````


### views/common.py

````python
"""Reusable Streamlit upload, curriculum, chart and report controls."""

import hashlib
import pickle
import pandas as pd
import streamlit as st
from core.subjects_config import STAGES, resolve_subjects, METHODS
from core.templates import template
from core.validators import read_marks, ValidatedData
from core.charts import Chart, interactive
from core.pdf_report import Report, build_pdf, font_path

WARNING = (
    "Please follow the exact column names and formats of the template. "
    "Do not rename, reorder or delete columns. Files that do not match will be rejected."
)


@st.cache_data(max_entries=24, show_spinner=False)
def cached_template(
    subjects: tuple, sample: bool, section: str, maximum: float
) -> bytes:
    """Cache public, synthetic templates only; student uploads stay session-local."""
    return template(
        subjects, sample, section, maximum, seed=sum(map(ord, section)) or 19
    )


def _selection(prefix: str) -> tuple[list[str], str]:
    """Stage → class → pathway → optional subjects, with enforced counts."""
    a, b = st.columns(2)
    stage = a.selectbox("Key Stage", list(STAGES), key=prefix + "_stage")
    config = STAGES[stage]
    grade = b.selectbox("Class", config["classes"], key=prefix + "_class")
    pathway, choices, tvet = "", [], ""
    if "pathways" in config:
        pathway = st.selectbox(
            "Pathway / Stream", list(config["pathways"]), key=prefix + "_path"
        )
        path = config["pathways"][pathway]
        if path.get("options"):
            choices = st.multiselect(
                f"Optional subjects (choose {path['min']}–{path['max']})",
                path["options"],
                key=prefix + "_choices_" + pathway,
            )
        if "TVET" in choices + path["core"]:
            tvet = st.text_input(
                "School-specific TVET subject name", key=prefix + "_tvet"
            )
    try:
        subjects = resolve_subjects(stage, pathway, choices, tvet)
    except ValueError as exc:
        st.warning(str(exc))
        return [], grade
    st.caption("Subjects: " + ", ".join(subjects))
    return subjects, grade


def _uploader(
    subjects: list[str],
    key: str,
    section: str | None = None,
    maximum: float = 100,
    enforce_max: bool = False,
) -> ValidatedData | None:
    """Persist validated bytes/data across navigation and prevent stale results."""
    signature = (tuple(subjects), section, maximum, enforce_max)
    if st.session_state.get(key + "_schema") != signature:
        st.session_state.pop(key + "_data", None)
        st.session_state.pop(key + "_digest", None)
        st.session_state[key + "_schema"] = signature
    a, b = st.columns(2)
    a.download_button(
        "Download Template",
        cached_template(tuple(subjects), False, section or "", maximum),
        f"{key}_template.xlsx",
        key=key + "_template",
        on_click="ignore",
    )
    b.download_button(
        "Download Sample File",
        cached_template(tuple(subjects), True, section or "", maximum),
        f"{key}_sample.xlsx",
        key=key + "_sample",
        on_click="ignore",
    )
    st.warning(WARNING)
    schema_hash = hashlib.sha256(repr(signature).encode()).hexdigest()[:10]
    upload = st.file_uploader(
        "Upload Excel (.xlsx)", type=["xlsx"], key=key + "_file_" + schema_hash
    )
    if upload is not None:
        raw = upload.getvalue()
        digest = hashlib.sha256(raw).hexdigest()
        if st.session_state.get(key + "_digest") != digest:
            st.session_state.pop(key + "_data", None)
            with st.spinner("Validating workbook…"):
                data = read_marks(
                    raw, subjects, section, maximum if enforce_max else None
                )
            st.session_state[key + "_digest"] = digest
            st.session_state[key + "_errors"] = data.errors
            if not data.errors:
                st.session_state[key + "_data"] = data
        for error in st.session_state.get(key + "_errors", []):
            st.error(error)
    data = st.session_state.get(key + "_data")
    if data is not None:
        st.success(
            f"Validated {len(data.frame)} students. Data retained for this session."
        )
        with st.expander("Data preview (first 10 rows)"):
            st.dataframe(data.frame.head(10), hide_index=True, width="stretch")
        excluded = data.frame[subjects].isna().sum()
        st.caption(
            "Excluded marks per subject: "
            + ", ".join(
                f"{s}: {excluded[s]} (AB: {data.absent[s].sum()})" for s in subjects
            )
        )
        small = [s for s in subjects if data.frame[s].notna().sum() < 5]
        if small:
            st.warning(
                "Fewer than 5 valid marks; interpret cautiously: " + ", ".join(small)
            )
    return data


def metrics(values: dict) -> None:
    """Responsive rows of four metric cards with consistent precision."""
    entries = list(values.items())
    for start in range(0, len(entries), 4):
        for column, (label, value) in zip(st.columns(4), entries[start : start + 4]):
            display = (
                "N/A"
                if pd.isna(value)
                else f"{value:.2f}"
                if isinstance(value, float)
                else str(value)
            )
            column.metric(label, display)


def table(report: Report, title: str, frame: pd.DataFrame, heat: bool = False) -> None:
    """Display and collect exactly the same table for export."""
    st.subheader(title)
    if frame.empty:
        st.info("No matching records.")
    else:
        styled = frame.style.format(precision=2, na_rep="N/A")
        if heat:
            columns = [
                c for c in frame.select_dtypes("number") if frame[c].notna().any()
            ]
            if columns:
                styled = styled.background_gradient(cmap="Blues", subset=columns)
        st.dataframe(styled, hide_index=True, width="stretch")
    report.tables.append((title, frame))


def chart(report: Report, spec: Chart) -> None:
    """Render a chart and retain its data for the PDF counterpart."""
    st.plotly_chart(interactive(spec), width="stretch", theme=None)
    report.charts.append(spec)


def text(report: Report, message: str) -> None:
    """Show an interpretation and include it in the report."""
    st.write(message)
    report.texts.append(message)


def _report_download(report: Report, metadata: dict, key: str) -> None:
    """Cache generated PDFs within this user's session, invalidated by content."""
    st.caption(
        "Sample standard deviation uses ddof=1. All displayed values are rounded to 2 decimals."
    )
    with st.expander("Definitions and ranking methods"):
        st.write(METHODS)
    if not font_path():
        st.caption(
            "For Dzongkha in PDFs, configure a Tibetan-capable TTF font as described in Help."
        )
    digest = hashlib.sha256(pickle.dumps((report, metadata))).hexdigest()
    state_key = key + "_pdf"
    cached = st.session_state.get(state_key)
    if cached and cached[0] != digest:
        st.session_state.pop(state_key)
        cached = None
    if st.button("Prepare PDF Report", key=key + "_prepare", type="primary"):
        try:
            with st.spinner("Rendering report tables and charts…"):
                content = build_pdf(report, metadata)
            st.session_state[state_key] = (digest, content)
            cached = (digest, content)
        except Exception as exc:
            st.error(
                f"The PDF could not be generated ({type(exc).__name__}). Check installed dependencies and configured font. Your results remain available."
            )
    if cached:
        st.download_button(
            "Download PDF Report",
            cached[1],
            key + ".pdf",
            "application/pdf",
            key=key + "_download",
            on_click="ignore",
        )
    else:
        st.download_button(
            "Download PDF Report",
            b"",
            key + ".pdf",
            disabled=True,
            key=key + "_disabled",
        )


def selection(prefix: str) -> tuple[list[str], str]:
    """Keep curriculum choices together on a readable setup panel."""
    with st.container(border=True, key="setup_panel"):
        st.subheader("Set up your class")
        st.caption("Your selections determine the subjects in the template.")
        return _selection(prefix)


def uploader(
    subjects: list[str],
    key: str,
    section: str | None = None,
    maximum: float = 100,
    enforce_max: bool = False,
) -> ValidatedData | None:
    """Present template downloads, file checks and upload status as one task."""
    with st.container(border=True, key="upload_panel"):
        st.subheader("Upload your mark sheet")
        st.caption(
            "Start with the matching template, or download the fictional sample to explore the analysis."
        )
        return _uploader(subjects, key, section, maximum, enforce_max)


def report_download(report: Report, metadata: dict, key: str) -> None:
    """Give report preparation a clear destination after the results."""
    with st.container(border=True, key="report_panel"):
        st.subheader("Take your analysis to the staff meeting")
        st.caption(
            "Prepare a PDF with the current tables, charts and selected student lists. School details come from the sidebar."
        )
        _report_download(report, metadata, key)
````


### views/individual.py

````python
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
````


### views/sections.py

````python
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
````


### tests/test_app.py

````python
"""Headless UI smoke tests with validated fictional uploads in session state."""

from streamlit.testing.v1 import AppTest
from core.templates import template
from core.validators import read_marks
from core.subjects_config import STAGES


def test_navigation_pages():
    app = AppTest.from_file("app.py", default_timeout=30).run()
    for page in [
        "Individual Subject Analysis",
        "Class Result Analysis",
        "Section Comparison",
        "Help/Instructions",
        "Home",
    ]:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception


def test_individual_and_class_results_persist():
    app = AppTest.from_file("app.py", default_timeout=30).run()
    app.sidebar.radio[0].set_value("Individual Subject Analysis").run()
    app.session_state["individual_data"] = read_marks(
        template(("English",), True), ["English"]
    )
    app.run()
    assert not app.exception
    assert any(m.label == "Pass %" for m in app.metric)
    app.sidebar.radio[0].set_value("Class Result Analysis").run()
    subjects = STAGES["Key Stage 1"]["core"]
    app.session_state["class_data"] = read_marks(
        template(tuple(subjects), True), subjects
    )
    app.run()
    assert not app.exception
    assert any(m.label == "Passed all %" for m in app.metric)
    app.sidebar.radio[0].set_value("Individual Subject Analysis").run()
    assert not app.exception
    assert any(m.label == "Pass %" for m in app.metric)


def test_sections_and_benchmarks():
    app = AppTest.from_file("app.py", default_timeout=40).run()
    app.sidebar.radio[0].set_value("Section Comparison").run()
    subjects = STAGES["Key Stage 1"]["core"]
    app.session_state["section_records"] = {
        s: read_marks(template(tuple(subjects), True, s), subjects, s)
        for s in ["A", "B"]
    }
    app.session_state["section_finished"] = True
    app.run()
    assert not app.exception
    assert any(m.label == "Passed all %" for m in app.metric)
    assert not any(b.label == "Try fetch from online source" for b in app.button)


def test_remove_reupload_and_national_visibility():
    app = AppTest.from_file("app.py", default_timeout=40).run()
    app.sidebar.radio[0].set_value("Section Comparison").run()
    next(s for s in app.selectbox if s.label == "Key Stage").set_value(
        "Key Stage 2"
    ).run()
    next(s for s in app.selectbox if s.label == "Class").set_value("VI").run()
    subjects = STAGES["Key Stage 2"]["core"]
    app.session_state["section_records"] = {
        s: read_marks(template(tuple(subjects), True, s), subjects, s)
        for s in ["A", "B"]
    }
    app.session_state["section_finished"] = True
    app.run()
    assert any(b.label == "Try fetch from online source" for b in app.button)
    next(b for b in app.button if b.label == "Re-upload").click().run()
    assert app.session_state["section_edit"] == "A"
    assert not app.session_state["section_finished"]
    next(b for b in app.button if b.label == "Cancel re-upload").click().run()
    next(b for b in app.button if b.key == "remove_B").click().run()
    assert len(app.session_state["section_records"]) == 1
    assert next(
        b for b in app.button if b.label == "Finish uploading & Analyse"
    ).disabled
    assert not app.exception


def test_subject_settings_survive_navigation():
    app = AppTest.from_file("app.py", default_timeout=30).run()
    app.sidebar.radio[0].set_value("Individual Subject Analysis").run()
    next(w for w in app.text_input if w.label == "Subject name").set_value(
        "Mathematics"
    ).run()
    next(w for w in app.number_input if w.label == "Maximum marks").set_value(50).run()
    app.sidebar.radio[0].set_value("Home").run()
    app.sidebar.radio[0].set_value("Individual Subject Analysis").run()
    assert (
        next(w for w in app.text_input if w.label == "Subject name").value
        == "Mathematics"
    )
    assert next(w for w in app.number_input if w.label == "Maximum marks").value == 50
````


### tests/test_core.py

````python
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
````


### tests/test_full_reports.py

````python
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
````


### tests/test_pdf.py

````python
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
````


### assets/theme.css

````css
/* Shared visual language with Item Analyzer: valley, deep blue, teal and brass. */
.stApp {
  --ink:#eef4f5; --muted:#b9cbd4; --edge:#36505f; --teal:#a3e1d2;
  --reading-font:"Source Sans 3","Result Tibetan","Segoe UI",sans-serif;
  color:var(--ink); background:#102230; font-family:var(--reading-font);
}
.stApp :is(p,label,button,input,select,td,th) {font-family:var(--reading-font);}
[data-testid="stHeader"] {background:#102230ed;border-bottom:1px solid #ffffff0b;}
.block-container {max-width:1240px;padding:3.8rem 2.5rem 2rem;}
[data-testid="stMainBlockContainer"] > div {isolation:isolate;}
.st-key-valley_art {position:fixed;inset:0;z-index:0;pointer-events:none;overflow:hidden;}
.st-key-valley_art div,.st-key-classroom_art div {position:static;}
.st-key-valley_art img,.st-key-classroom_art img {position:absolute;inset:0;width:100%;height:100%;object-fit:cover;}
.st-key-valley_art::after {content:"";position:absolute;inset:0;background:linear-gradient(#0c1d2de8,#102434c9 40%,#0b1b2bf5);}
.st-key-school_header {position:relative;isolation:isolate;overflow:hidden;min-height:15rem;padding:2.5rem!important;border:1px solid #62747780;border-radius:20px;justify-content:center;margin-bottom:1.2rem;background:#182d37;box-shadow:0 18px 45px #06121c40;}
.st-key-classroom_art {position:absolute;inset:0;z-index:-1;pointer-events:none;overflow:hidden;}
.st-key-classroom_art::after {content:"";position:absolute;inset:0;background:linear-gradient(90deg,#071b29ed,#122a35b8 52%,#122a3510);}
.ia-eyebrow {font-size:.75rem!important;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#b4e6da;margin:0 0 .9rem;}
.ia-title {font:500 clamp(2.1rem,3.5vw,3.4rem)/1.12 Georgia,"Result Tibetan",serif!important;letter-spacing:-.035em;color:#fff6e7;margin:0;max-width:19ch;text-shadow:0 2px 20px #061520;}
.ia-sub {color:#dae5e7;font-size:1rem;line-height:1.6;margin:.9rem 0 0;max-width:45ch;}
.stApp:has(.workspace-compact) .st-key-school_header {min-height:8rem;padding:1.35rem 2rem!important;margin-bottom:.5rem;}
.stApp:has(.workspace-compact) .ia-title {font-size:1.8rem!important;max-width:none;}
.stApp:has(.workspace-compact) .ia-eyebrow {margin-bottom:.45rem;}
.stApp:has(.workspace-compact) .ia-sub {display:none;}
.stApp h1,.stApp h2,.stApp h3 {color:#f7f3e9;letter-spacing:-.025em;}
.stApp h2 {font:500 clamp(1.55rem,2.3vw,2rem)/1.25 Georgia,"Result Tibetan",serif;}
.stApp h3 {font-size:1.12rem;font-weight:600;letter-spacing:-.01em;}
.stApp [data-testid="stCaptionContainer"] p {color:var(--muted);font-size:.88rem;line-height:1.55;}
[data-testid="stSidebar"] {background:#102330;border-right:1px solid #ffffff12;}
[data-testid="stSidebarUserContent"] {padding-top:1.4rem;}
.sidebar-brand {font:500 1.45rem/1.25 Georgia,serif;color:#fff3df;margin:0 0 .3rem;}
.sidebar-kicker {font-size:.73rem;letter-spacing:.12em;color:#9cb5c4;text-transform:uppercase;margin-bottom:1.6rem;}
[data-testid="stSidebar"] [role="radiogroup"] {gap:.4rem;}
[data-testid="stSidebar"] [role="radiogroup"] label {padding:.65rem .75rem;border-radius:10px;transition:background .15s;}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {background:#1b3646;}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {background:#244351;box-shadow:inset 3px 0 #a3e1d2;}
[data-testid="stSidebar"] [role="radiogroup"] label p {font-size:.94rem;}
[data-testid="stSidebar"] [data-testid="stExpander"] {background:#142c3a;border-color:#294451;}
[data-testid="stVerticalBlockBorderWrapper"] > div {border-radius:16px;}
.st-key-module_subject,.st-key-module_class,.st-key-module_sections {background:linear-gradient(145deg,#233e4e,#152d3d);border:1px solid #3a5564!important;border-radius:16px;padding:1.35rem!important;min-height:19rem;box-shadow:0 9px 25px #07141e30;}
.st-key-module_subject:hover,.st-key-module_class:hover,.st-key-module_sections:hover {border-color:#89bbaf!important;}
.module-symbol {display:inline-flex;align-items:center;justify-content:center;width:2.5rem;height:2.5rem;border:1px solid #6b9d9580;border-radius:10px;color:#b5eadb;background:#244b51;font:600 1rem/1 sans-serif;margin-bottom:.75rem;}
.module-detail {color:#a9c1cb;font-size:.85rem;line-height:1.6;margin-top:.6rem;}
.workflow-note {display:flex;flex-wrap:wrap;gap:.7rem 1.5rem;padding:1.15rem 1.4rem;border:1px solid #35505f;border-radius:12px;background:#172e3dcc;color:#c1d1d8;font-size:.9rem;}
.workflow-note strong {color:#e7d0a6;font-weight:600;margin-right:.35rem;}
.st-key-setup_panel,.st-key-upload_panel,.st-key-report_panel {background:#172e3def;border:1px solid #35505f!important;border-radius:16px;padding:1.4rem!important;}
.st-key-upload_panel {margin:.5rem 0 1.25rem;}
.st-key-report_panel {margin-top:1.5rem;border-top:2px solid #8bbcac!important;}
[data-testid="stFileUploaderDropzone"] {background:#102735;border:1px dashed #658394;border-radius:12px;min-height:8rem;}
[data-testid="stFileUploaderDropzone"]:hover {border-color:#a3e1d2;background:#173340;}
[data-testid="stMetric"] {background:linear-gradient(145deg,#203c4d,#152c3b);border:1px solid #365361;border-top:2px solid #89c3b5;border-radius:13px;padding:1rem 1.2rem;min-height:7rem;}
[data-testid="stMetricLabel"] p {color:#c0d2d9!important;font-size:.83rem;}
[data-testid="stMetricValue"] {color:#fff7e9;font-variant-numeric:tabular-nums;font-size:2rem;letter-spacing:-.03em;}
.stApp [role="tablist"] {gap:.35rem;border-bottom:1px solid #3a5261;padding:.4rem 0 .25rem;}
.stApp [role="tab"] {color:#baceD7;border-radius:8px 8px 0 0;padding:.55rem .85rem;font-size:.94rem;}
.stApp [role="tab"][aria-selected="true"] {color:#b8eadc;background:#26424f;}
[data-testid="stExpander"] {background:#142c3acc;border:1px solid #35505f;border-radius:11px;}
[data-testid="stDataFrame"] {border:1px solid #3c5564;border-radius:11px;overflow:hidden;}
[data-testid="stPlotlyChart"] {border:1px solid #344f60;border-radius:14px;overflow:hidden;background:#142c3d;}
[data-baseweb="input"],[data-baseweb="select"] > div {border-radius:9px;border-color:#3c5766;}
.stApp button {min-height:2.6rem;border-radius:9px!important;}
.stApp button[kind="primary"] {background:#a3e1d2;color:#102e32;border:1px solid #b9ecdf;font-weight:650;}
.stApp button[kind="primary"]:hover {background:#b6ecdf;border-color:#daf9f0;color:#0c2730;}
[data-testid="stDownloadButton"] button {color:#f0d29d;background:#263b49;border:1px solid #9a886a;}
[data-testid="stDownloadButton"] button:hover {border-color:#f0d29d;color:#ffe9c6;}
.stApp button:disabled {opacity:.45;}
.stApp :is(button,a,input):focus-visible {outline:3px solid #e7c486;outline-offset:3px;}
[data-testid="stAlert"] {border-radius:11px;}
.result-footer {display:flex;flex-wrap:wrap;justify-content:space-between;gap:.5rem;border-top:1px solid #36505f;padding-top:1rem;margin-top:1.5rem;color:#99b2c1;font-size:.8rem;}
@media(max-width:850px) {
 .block-container {padding:3.5rem 1.2rem 1.5rem;}
 .st-key-school_header {padding:1.6rem!important;min-height:13rem;}
 .st-key-module_subject,.st-key-module_class,.st-key-module_sections {padding:1rem!important;min-height:0;}
}
@media(max-width:640px) {
 .st-key-school_header {min-height:12rem;}
 .ia-title {font-size:2.1rem!important;}
 .stApp:has(.workspace-compact) .ia-title {font-size:1.45rem!important;}
 .st-key-setup_panel,.st-key-upload_panel,.st-key-report_panel {padding:1rem!important;}
 [data-testid="stMetricValue"] {font-size:1.6rem;}
 [data-testid="stMetric"] {padding:.8rem;min-height:6rem;}
 .stApp [role="tablist"] {overflow-x:auto;}
}
/* Keep fixed artwork behind every reading surface and interactive control. */
.block-container {isolation:isolate;}
.st-key-valley_art {z-index:-1;}
````


### .streamlit/config.toml

````toml
[theme]
base = "dark"
primaryColor = "#E8BD75"
backgroundColor = "#102230"
secondaryBackgroundColor = "#193444"
textColor = "#F6F3EB"
font = "sans serif"

[server]
maxUploadSize = 10

[browser]
gatherUsageStats = false
````


### .gitignore

````text
__pycache__/
.pytest_cache/
.venv/
.DS_Store
tmp/
.ruff_cache/
*.zip
````


### requirements-dev.txt

````text
-r requirements.txt
pytest>=8,<10
pypdf>=5,<7
pymupdf>=1.24,<2
ruff>=0.11,<1
````


### assets/NotoSerifTibetan-LICENSE.txt

````text
Copyright 2022 The Noto Project Authors (https://github.com/notofonts/tibetan)

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is copied below, and is also available with a FAQ at:
https://scripts.sil.org/OFL


-----------------------------------------------------------
SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007
-----------------------------------------------------------

PREAMBLE
The goals of the Open Font License (OFL) are to stimulate worldwide
development of collaborative font projects, to support the font creation
efforts of academic and linguistic communities, and to provide a free and
open framework in which fonts may be shared and improved in partnership
with others.

The OFL allows the licensed fonts to be used, studied, modified and
redistributed freely as long as they are not sold by themselves. The
fonts, including any derivative works, can be bundled, embedded, 
redistributed and/or sold with any software provided that any reserved
names are not used by derivative works. The fonts and derivatives,
however, cannot be released under any other type of license. The
requirement for fonts to remain under this license does not apply
to any document created using the fonts or their derivatives.

DEFINITIONS
"Font Software" refers to the set of files released by the Copyright
Holder(s) under this license and clearly marked as such. This may
include source files, build scripts and documentation.

"Reserved Font Name" refers to any names specified as such after the
copyright statement(s).

"Original Version" refers to the collection of Font Software components as
distributed by the Copyright Holder(s).

"Modified Version" refers to any derivative made by adding to, deleting,
or substituting -- in part or in whole -- any of the components of the
Original Version, by changing formats or by porting the Font Software to a
new environment.

"Author" refers to any designer, engineer, programmer, technical
writer or other person who contributed to the Font Software.

PERMISSION & CONDITIONS
Permission is hereby granted, free of charge, to any person obtaining
a copy of the Font Software, to use, study, copy, merge, embed, modify,
redistribute, and sell modified and unmodified copies of the Font
Software, subject to the following conditions:

1) Neither the Font Software nor any of its individual components,
in Original or Modified Versions, may be sold by itself.

2) Original or Modified Versions of the Font Software may be bundled,
redistributed and/or sold with any software, provided that each copy
contains the above copyright notice and this license. These can be
included either as stand-alone text files, human-readable headers or
in the appropriate machine-readable metadata fields within text or
binary files as long as those fields can be easily viewed by the user.

3) No Modified Version of the Font Software may use the Reserved Font
Name(s) unless explicit written permission is granted by the corresponding
Copyright Holder. This restriction only applies to the primary font name as
presented to the users.

4) The name(s) of the Copyright Holder(s) or the Author(s) of the Font
Software shall not be used to promote, endorse or advertise any
Modified Version, except to acknowledge the contribution(s) of the
Copyright Holder(s) and the Author(s) or with their explicit written
permission.

5) The Font Software, modified or unmodified, in part or in whole,
must be distributed entirely under this license, and must not be
distributed under any other license. The requirement for fonts to
remain under this license does not apply to any document created
using the Font Software.

TERMINATION
This license becomes null and void if any of the above conditions are
not met.

DISCLAIMER
THE FONT SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT
OF COPYRIGHT, PATENT, TRADEMARK, OR OTHER RIGHT. IN NO EVENT SHALL THE
COPYRIGHT HOLDER BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
INCLUDING ANY GENERAL, SPECIAL, INDIRECT, INCIDENTAL, OR CONSEQUENTIAL
DAMAGES, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF THE USE OR INABILITY TO USE THE FONT SOFTWARE OR FROM
OTHER DEALINGS IN THE FONT SOFTWARE.
````


## 4. Template and sample generator


### core/templates.py

````python
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
````


## 5. requirements.txt


### requirements.txt

````text
streamlit>=1.55,<2
pandas>=2.2,<4
numpy>=1.26,<3
scipy>=1.12,<2
plotly>=5.22,<7
openpyxl>=3.1,<4
matplotlib>=3.9,<4
reportlab>=4.2,<5
````


## 6. README with run and deployment instructions


### README.md

````markdown
# Bhutan Result Analysis Tool

A Python-only Streamlit application for individual subject, class, and same-grade section analysis. It reuses the Item Analyzer's valley artwork, classroom banner, dark panels, and typography, with the required sidebar navigation. No external chart service or JavaScript build is required.

## Assumptions and definitions

- The curriculum dictionary implements the supplied specification; it is not independently certified as current MoESD/BCSEA policy. The general IX/X pathway includes both listed subjects. TVET IX/X requires a named vocational subject with optional Economics.
- `PASS_PERCENT = 40` is defined once in `core/subjects_config.py`. Marks exactly at 40% pass. Classification uses unrounded percentages.
- All statistics and comparison charts use percentage marks, including the individual-subject page. Individual student lists also show raw marks. Average total marks is a raw-mark metric.
- Excel `Settings` is the supported alternative to a Max Marks row. Every upload requires `Marks` and `Settings` worksheets. Identity and subject columns must match exactly in order, ignoring case and surrounding whitespace. Section cells may be blank outside Module 3, but the column is always present.
- Blank and AB marks are excluded independently per subject. Other subjects for the same student remain included. AB and blank counts are displayed separately; neither becomes zero.
- Overall mean, median and sample SD use student averages across available subjects, with equal subject weighting. Complete-only totals and rankings prevent an incomplete student from receiving a misleading overall rank. Averages for incomplete students may use different subject sets.
- Passed-all rate uses complete students as its denominator. Passed-at-least-one rate uses students with at least one valid mark. Both denominators appear on screen and in reports. Observed failure counts include partial records. Group overall pass rates refer to available averages ≥40%, not passed-all rates.
- Mode is shown only when a unique mode exists; tied modes are reported as N/A.
- Sample SD uses `ddof=1`; n<2 yields N/A. Small samples n<5 display warnings. No-data subjects remain N/A, not zero. Outliers remain in all statistics.
- Diagnosis categories apply urgent rules first, then improvement, then Doing Well. All other assessed combinations are Satisfactory, resolving gaps in the suggested ranges. Thresholds and the descriptive 75% pass-rate benchmark reside in `DIAGNOSIS`.
- Subject strength is `0.5 × mean + 0.5 × pass%`. Section composite is `0.4 × passed-all% + 0.3 × mean + 0.2 × median + 0.1 × max(0,100−sample SD)`. A section needs at least two assessed students and one complete student for a rank. Ties share competition ranks (1,1,3). Subject-section winners use subject strength and list ties.
- Support lists include students failing ≥2 subjects or with at least one score from 40% to below 50%. Missing assessments have a separate follow-up table.
- Score bands labelled 0–39, 40–49 etc. are continuous intervals [0,40), [40,50), ..., [80,100].
- Previous-year benchmarks use one teacher-labelled year per analysis. Dzongkhag/national inputs are optional means, in percentages. Overall prior-year pass rate must use the same passed-all definition. No benchmark numbers are preloaded. The requested online-fetch hook always falls back honestly to manual input until a verified endpoint is configured.

## Run locally

Python 3.10+:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

On Windows, activate with `.venv\Scripts\activate` instead. The supplied `.streamlit/config.toml` sets the theme and 10 MB upload limit.

1. Choose a module in the sidebar and enter school, academic year, and teacher.
2. For class/section work, choose Key Stage, class, pathway and electives. Required counts are enforced.
3. Download that module's template or fictional sample file.
4. Fill the `Marks` sheet; use the `Settings` sheet for maximum marks. Headers are locked; Gender and Residence have dropdowns. The first 1,000 entry rows are unlocked. Unprotect the sheet to extend it, retaining the exact headers. Protection is an accidental-edit aid, not security.
5. Upload the `.xlsx` file. Correct row-specific errors and re-upload if necessary.
6. Section comparison: save Section A, then upload/save the next section. Custom names must match the Section column. Use Re-upload or Remove section as needed. At least two valid sections are required before Finish uploading & Analyse.
7. Review tabs. Prepare PDF Report, then Download PDF Report. Report data, optional lists and name visibility follow the current screen settings.

The maximum per upload is 10 MB, 10,000 students and 50 columns; expanded workbook XML is limited to 80 MB. Formula cells, duplicates, out-of-range marks and extra/reordered columns are rejected. Unique student IDs are required across all uploaded sections. `AB` is case-insensitive. `M/F`, `Hostel`, `Day-scholar`, and `Dayscholar` normalize to the specified categories.

## Project structure

```text
app.py
core/
  subjects_config.py   curriculum, thresholds, constants and methods
  validators.py        strict, row-specific Excel validation
  templates.py         dynamic openpyxl templates and fictional samples
  stats.py             pure analytical functions
  charts.py            Plotly charts and matplotlib PDF equivalents
  benchmarks.py        manual comparisons and safe national-source hook
  pdf_report.py        in-memory ReportLab reports
views/
  common.py            selection, uploads, tables, PDF controls
  individual.py        Module 1
  class_result.py      Module 2 and shared whole-grade views
  sections.py          Module 3 and benchmarks
assets/theme.css
static/classroom.jpg
static/valley.jpg
sample_data/            generated fictional examples
.streamlit/config.toml
requirements.txt
requirements-dev.txt
tests/
README.md
MANUAL_TESTS.md
SOURCE_CODE.md          full text-source listing in requested delivery order
```

## Templates and samples

The app generates a matching blank template and fictional sample for every supported subject combination. The code is in `core/templates.py` (openpyxl, no external service). Regenerate the three included examples with:

```sh
python -m core.templates
```

`Marks` contains Student ID, Student Name, Gender, Residence, Section, then the selected subjects. `Settings` contains Subject and Max Marks. `Instructions` explains formatting and exclusions. Sample names are deliberately labelled Sample and have no relationship to real students.

## PDF reports and Dzongkha

Reports are created entirely in memory using ReportLab, with the entered metadata, Bhutan-local generation date, cover, definitions, interpretations, tables, static equivalents of every displayed chart, and page-numbered footers. Wide tables split into column groups while repeating identifiers; long tables repeat headers. No browser, Kaleido or external rendering service is required.

For Dzongkha names/subjects, provide a licensed TrueType font containing Tibetan and Latin glyphs, e.g. Jomolhari or Noto Serif Tibetan:

```sh
export DZONGKHA_FONT_PATH="/absolute/path/Jomolhari.ttf"
streamlit run app.py
```

Alternatively put `Jomolhari.ttf` or `NotoSerifTibetan-Regular.ttf` in `assets/`. `font_path()` finds it; `build_pdf()` registers it with `pdfmetrics.registerFont(TTFont('Dzongkha', path))` and uses it in ReportLab paragraphs and tables. Matplotlib uses the same file for chart tick labels. No external font is required for English reports.

TrueType embedding supplies glyphs but does not guarantee correct Tibetan complex-script shaping. Visually verify stacked glyphs with your selected ReportLab/font combination before issuing Dzongkha reports. The UI and Excel preserve Unicode. The app displays a font setup reminder if no font is configured. See [ReportLab font documentation](https://docs.reportlab.com/reportlab/userguide/ch3_fonts/).

## Privacy and performance

Uploads are processed in server memory and held in `st.session_state`; they are not intentionally written to disk, database, logs or shared data cache. Only public blank templates and fictional samples use `st.cache_data`. PDF bytes are cached only in the user's session and invalidated when report content/metadata changes. Clear session data removes the app's session records. This is not a guaranteed secure-memory erasure service.

Hosted Streamlit sends uploads to its server. Local use processes them on your computer. A refreshed/lost session or server restart may require re-uploading. Downloaded reports contain student data. Name hiding is not anonymization: student IDs remain visible.

Pandas operations handle 500+ students. PDF preparation is explicit because large charts and tables take longer than screen summaries. Plotly remains interactive, while static PDFs use matplotlib. PDF rendering is serialized within a process for matplotlib thread safety.

## Deployment: Streamlit Community Cloud

1. Push this folder to a GitHub repository, including `assets/`, `static/`, `.streamlit/config.toml` and `requirements.txt`. Exclude `.venv/`, temporary QA output and actual student files.
2. Create an app in Streamlit Community Cloud, choose the repository/branch, and select `app.py` as the entry point.
3. Select a Python version compatible with the requirements (3.12 recommended for matching the development checks).
4. If using a Dzongkha font, include the licensed font in `assets/` or configure a valid font path for that deployment.
5. Test templates, all modules and PDF downloads in the deployed environment before sharing with teachers. Hosted processing requires connectivity; this is not a browser-only/offline hosted app.

No secrets or database are required. Hosting access, resource limits and availability are controlled by the provider. The server should be used only within your school's approved handling of student records.

## Tests

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Tests cover normalization, strict template contracts, missing marks, pass boundaries, sample SD, outliers, unavailable groups, section compatibility, ties, benchmark validation, page navigation and PDF output. See `MANUAL_TESTS.md` for the browser and deployment acceptance checklist.

## Verification record

Development checks on Python 3.12: 39 tests passed. Tested package versions: Streamlit 1.58.0, pandas 3.0.5, numpy 1.26.4, scipy 1.16.3, Plotly 5.22.0, openpyxl 3.1.5, matplotlib 3.10.0, ReportLab 4.5.1. The allowed dependency ranges also support Python 3.10-compatible package releases; that interpreter was not separately tested.

A browser check covered the reference styling, an actual fictional Excel upload, interactive distribution charts, and a downloaded PDF. Full PDFs for all three modules were generated and visually reviewed. A 600-student/eight-subject calculation and diagnosis check took approximately 0.08 seconds on the development machine (not an end-to-end upload, chart or PDF timing guarantee).

Remaining manual acceptance checks: mobile/narrow-width interactions, Excel's native dropdown behavior, simultaneous browser sessions, school deployment and Dzongkha complex-script PDF shaping with the chosen font. These are listed in MANUAL_TESTS.md. The app has not been publicly deployed.

## Interface revamp

The Item Analyzer artwork and dark blue/teal/brass palette are retained. Home now provides three direct module cards and a short workflow guide. Analysis pages have compact banners, grouped setup/upload/report panels, clearer tabs and metric cards, and matching dark interactive charts. The sidebar groups school details and session controls. Narrow layouts stack the cards and forms, with the sidebar initially collapsed where Streamlit chooses. Analytical rules and PDF content are unchanged.

Verification for this interface revision: five UI workflow tests passed; all three Home-card routes were exercised; the narrow browser layout and contrast were visually reviewed.
````


## 7. Manual test checklist


### MANUAL_TESTS.md

````markdown
# Manual acceptance checklist

- [ ] Home/sidebar readable at desktop and narrow mobile widths; keyboard navigation works.
- [ ] Select every stage/class; enforce elective minimum/maximum counts and require a distinct TVET name.
- [ ] Open a template in Excel: header protection, Gender/Residence dropdowns, editable marks/maxima, Instructions sheet.
- [ ] Upload each fictional sample; confirm first-ten-row preview, exclusions, and persistent results after navigating away/back.
- [ ] Reject renamed, reordered, missing and extra columns; reject invalid category, duplicate ID, formula, negative/over-maximum mark; inspect exact row numbers.
- [ ] Check 39.99%, exactly 40%, 100%, zero, AB and blank; repeat with a maximum of 50.
- [ ] Exercise n=0, n=1, n=4, all-equal values and a missing gender/residence group.
- [ ] Module 1: histogram/KDE, mean/median lines, fail shading, band counts, IQR outliers, all seven comparison metrics, optional top/bottom lists.
- [ ] Module 2: reconcile passed-all and passed-any denominators, observed failure counts, ranking ties and incomplete exclusions; verify name hiding in both screen and PDF.
- [ ] Confirm diagnosis categories, reasons, group gaps, borderline percentages and strongest/weakest order against hand calculations.
- [ ] Module 3: save A then B; custom names; reject subject/max mismatches and duplicate IDs across sections; re-upload A, cancel a re-upload, remove B, and ensure analysis requires two saved sections.
- [ ] Check section composite and per-subject winners, including ties; verify whole-grade group comparisons.
- [ ] Leave benchmarks blank (skip cleanly); enter zero and nonzero prior figures; check deltas, arrows, mean and pass-rate charts.
- [ ] National input/fetch control visible only in VI, VIII, X, XII; fetch falls back to manual entry without invented data.
- [ ] Generate a PDF from every module: school/year/class/section/date/teacher, summary, all selected tables and charts, interpretations, repeated table headings and page numbers.
- [ ] Verify Dzongkha glyphs in Excel, UI and PDF with the configured licensed font.
- [ ] Test 500+ students and two simultaneous teacher sessions; confirm data and downloads remain separate.
- [ ] Deploy to a staging Streamlit app; repeat upload/download and navigation checks before school rollout.
````

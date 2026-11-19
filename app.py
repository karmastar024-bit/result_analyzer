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

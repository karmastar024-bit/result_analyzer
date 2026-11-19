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

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

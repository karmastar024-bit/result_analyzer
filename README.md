# Result Analyzer
A local Streamlit companion to Item Analyzer, for teachers in Bhutan.

## Run
```sh
python -m pip install -r requirements.txt
python -m streamlit run app.py
```
Choose **Try fictional sample data**, or download the template and upload an Excel/CSV mark sheet. Select the worksheet and header row, map student details, choose subjects, and confirm assessment settings.

Initial layout: Student ID, Name, Gender, English, Dzongkha, Mathematics, Science, Social Studies. Subject names and maximum marks are configurable. The current version accepts subject totals, not separate CA/exam components.

Rules are illustrative, not verified official policy. Every required subject must pass; incomplete results are distinct from failures. Class averages equally weight subject percentages. Overall pass rates and ranks include complete records only. Subject metrics include numeric marks only. AB/Abs/Absent and blanks are recorded separately. Ties use competition ranks. Gender comparisons retain unspecified entries.

Excel reports include student results, subject summaries, detailed records and settings. Download the HTML report, open it in a browser, and use Print / Save as PDF for A4 landscape output.

Student uploads are processed in server memory, with no intentional application disk/database retention. Hosted Streamlit transmits uploads to its server. Local Streamlit runs on your computer. Downloaded reports contain student records.

The visual theme and artwork are reused from the user's Item Analyzer. Full Dzongkha translation, separate CA/exam rules, multi-term analysis and school presets are future work.

Tests: `python -m pytest -q`

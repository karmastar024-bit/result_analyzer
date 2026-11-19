from io import BytesIO
from pathlib import Path
import pandas as pd
import streamlit as st
from analyzer import analyze
from exports import workbook, print_report

ROOT = Path(__file__).parent
st.set_page_config(page_title='Result Analyzer', page_icon='📊', layout='wide', initial_sidebar_state='collapsed')
st.html(ROOT/'assets/theme.css')
with st.container(key='valley_art'):
    st.image(str(ROOT/'static/valley.jpg'), width='stretch')
with st.container(key='school_header'):
    with st.container(key='classroom_art'):
        st.image(str(ROOT/'static/classroom.jpg'), width='stretch')
    st.markdown('<p class="ia-title">Result Analyzer</p><p class="ia-sub">Made for educators in Bhutan</p>', unsafe_allow_html=True)
st.header('Understand your class results')
st.caption('Upload a mark sheet, confirm the rules, and prepare your class report.')
subjects = ['English', 'Dzongkha', 'Mathematics', 'Science', 'Social Studies']
sample = pd.DataFrame({'Student ID':[f'S{i:02}' for i in range(1,9)], 'Name':[f'Sample Student {i}' for i in range(1,9)], 'Gender':['Girl','Boy']*4, 'English':[82,65,39,40,77,55,'AB',90], 'Dzongkha':[76,60,45,42,80,52,65,88], 'Mathematics':[90,58,35,41,75,50,62,92], 'Science':[85,62,40,44,72,48,60,89], 'Social Studies':[80,64,38,43,78,'',63,91]})
with st.expander('How to prepare your mark sheet'):
    st.write('Use one row per student: Student ID, Name, Gender, and one column per subject. Enter total marks. Use AB for absent and leave missing marks blank. Remove class totals and summary rows. The first version supports subject totals; CA and exam components should be combined before uploading.')
    st.write('Example grade boundaries and pass marks are editable; confirm the rules applicable to your assessment. These are not verified MoESD or BCSEA presets.')
left, right = st.columns(2)
left.download_button('Download blank Excel template', workbook({'Marks':sample.iloc[:0]}), 'result_template.xlsx', width='stretch')
right.download_button('Download fictional sample', workbook({'Marks':sample}), 'sample_results.xlsx', width='stretch')
use_sample = st.toggle('Try fictional sample data')
upload = st.file_uploader('Upload Excel or CSV', type=['xlsx','csv'])
frame = None
if use_sample:
    frame = sample.astype(str)
elif upload:
    if upload.size > 10*1024*1024:
        st.error('Please upload a file smaller than 10 MB.'); st.stop()
    try:
        raw = upload.getvalue()
        header = st.number_input('Header row number', min_value=1, max_value=100, value=1)
        if upload.name.lower().endswith('.xlsx'):
            book = pd.ExcelFile(BytesIO(raw))
            sheet = st.selectbox('Worksheet', book.sheet_names)
            frame = pd.read_excel(book, sheet_name=sheet, header=header-1, dtype=str, keep_default_na=False)
        else:
            frame = pd.read_csv(BytesIO(raw), header=header-1, dtype=str, keep_default_na=False)
        frame = frame.replace(r'^\s*$', pd.NA, regex=True).dropna(how='all').reset_index(drop=True)
    except Exception:
        st.error('Unable to read this sheet. Check the file format and header row.'); st.stop()
if frame is not None:
    if frame.empty:
        st.info('Add student rows to your template before uploading.'); st.stop()
    st.subheader('Review your data')
    st.dataframe(frame.head(20), hide_index=True, width='stretch')
    columns = list(frame.columns)
    def choose(label, preferred, optional=False):
        opts = ['Not included']+columns if optional else columns
        return st.selectbox(label, opts, index=opts.index(preferred) if preferred in opts else 0)
    a,b,c = st.columns(3)
    with a: name = choose('Student name column','Name')
    with b: sid = choose('Student ID column','Student ID',True)
    with c: gender = choose('Gender column','Gender',True)
    identity = {'Name':name}
    if sid != 'Not included': identity['Student ID'] = sid
    if gender != 'Not included': identity['Gender'] = gender
    if len(set(identity.values())) != len(identity):
        st.error('Choose different columns for each student detail.'); st.stop()
    available = [c for c in columns if c not in identity.values()]
    selected = st.multiselect('Subject columns', available, default=[c for c in available if c in subjects])
    st.subheader('Confirm assessment rules')
    title = st.text_input('Report title', 'Class result analysis')
    a,b = st.columns(2)
    passing = a.number_input('Subject pass mark (%)', 0.0, 100.0, 40.0)
    borderline = b.number_input('Support band above pass mark (percentage points)', 0.0, 25.0, 5.0)
    st.caption('Overall pass requires passing every selected subject. Class averages use equally weighted subject percentages. Incomplete students are excluded from class means, overall pass-rate denominators, and rankings. Ties share the same rank.')
    maxima = {}
    if selected:
        grid = st.data_editor(pd.DataFrame({'Subject':selected,'Maximum mark':[100.0]*len(selected)}), disabled=['Subject'], hide_index=True, key='maxima')
        maxima = dict(zip(grid.Subject, grid['Maximum mark']))
    with st.expander('Grade boundaries (%)'):
        cols = st.columns(4)
        bands = tuple(col.number_input(f'{g} minimum',0.0,100.0,float(v)) for col,g,v in zip(cols,'ABCD',[80,65,50,40]))
        st.caption('E is below the D boundary. Grades and pass status are calculated separately.')
    if st.button('Run analysis', type='primary', disabled=not selected):
        try:
            students, summary, detail = analyze(frame, identity, selected, maxima, passing, borderline, bands)
        except ValueError as e:
            st.error(str(e)); st.stop()
        complete = students.Result.ne('Incomplete')
        assessed = int(complete.sum())
        metrics = st.columns(4)
        metrics[0].metric('Students',len(students))
        metrics[1].metric('Complete results',assessed)
        metrics[2].metric('Overall pass rate',f'{students.Result.eq("Pass").sum()/assessed*100:.1f}%' if assessed else '—')
        metrics[3].metric('Class mean',f'{students["Average %"].mean():.1f}%' if assessed else '—')
        st.caption(f'Overall pass rate denominator: {assessed} students with complete results. Subject rates use students with numeric marks in that subject; absence and missing marks remain separate.')
        overview, subject_tab, student_tab, support = st.tabs(['Overview','Subjects','Students','Support needed'])
        with overview:
            st.bar_chart(summary.set_index('Subject')[['Mean %']])
            if 'Gender' in students:
                grouped = students.assign(Gender=students.Gender.str.strip().str.lower().replace({'m':'Boy','male':'Boy','boy':'Boy','boys':'Boy','f':'Girl','female':'Girl','girl':'Girl','girls':'Girl','':'Unspecified'})).groupby('Gender',dropna=False)['Average %'].agg(['size','count','mean']).rename(columns={'size':'Students','count':'Complete results','mean':'Mean %'})
                st.dataframe(grouped, width='stretch')
        with subject_tab: st.dataframe(summary,hide_index=True,width='stretch')
        with student_tab:
            st.dataframe(students.sort_values('Rank'),hide_index=True,width='stretch')
            st.subheader('Top performers')
            st.caption('Includes all students tied within the first five rank positions, among complete records.')
            st.dataframe(students[students.Rank.le(5)].sort_values('Rank'),hide_index=True,width='stretch')
        with support:
            st.dataframe(students[(students.Result!='Pass') | students['Near threshold'].ne('')],hide_index=True,width='stretch')
        settings = f'Pass: {passing}%; all subjects required; equal subject weights; grade minima A/B/C/D: {bands}; support band: {borderline}; maxima: {maxima}. Incomplete records excluded from overall metrics and rankings. Subject pass rates use numeric marks only. Ties use competition ranking.'
        settings_frame = pd.DataFrame({'Settings':[settings]})
        st.download_button('Download Excel report',workbook({'Students':students,'Subjects':summary,'Subject details':detail,'Settings':settings_frame}),'result_report.xlsx', on_click='ignore')
        st.download_button('Download printable report',print_report(title,settings,students,summary),'result_report.html', on_click='ignore')
        st.caption('Open the printable report and select Print / Save as PDF.')
st.divider()
st.caption('Uploads are processed in server memory. This app does not intentionally save student records to disk or a database. Hosted use sends the file to the server; local use processes it on your computer.')

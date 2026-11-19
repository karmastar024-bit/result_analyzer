import pandas as pd
import pytest
from analyzer import analyze

def test_absence_zero_ties_and_normalization():
    df = pd.DataFrame({'Name':['A','B','C','D','E'], 'Math':[20,20,0,'AB',''], 'English':[80,80,50,90,70]})
    students, summary, detail = analyze(df, {'Name':'Name'}, ['Math','English'], {'Math':50,'English':100})
    assert students['Result'].tolist() == ['Pass','Pass','Fail','Incomplete','Incomplete']
    assert students['Rank'].iloc[:3].tolist() == [1,1,3]
    assert students['Average %'].iloc[0] == 60
    assert students['Average %'].iloc[3:].isna().all()
    assert summary.iloc[0]['Assessed'] == 3
    assert summary.iloc[0]['Absent'] == 1
    assert summary.iloc[0]['Missing'] == 1
    assert summary.iloc[0]['Pass %'] == pytest.approx(200/3)

@pytest.mark.parametrize('mark', [-1,101,'oops'])
def test_invalid_marks(mark):
    with pytest.raises(ValueError):
        analyze(pd.DataFrame({'Name':['A'],'Math':[mark]}),{'Name':'Name'},['Math'],{'Math':100})

def test_export_formula_text():
    from exports import workbook
    from openpyxl import load_workbook
    from io import BytesIO
    ws = load_workbook(BytesIO(workbook({'Results':pd.DataFrame({'Name':['=1+1']})}))).active
    assert ws['A2'].data_type == 's'

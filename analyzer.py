"""Result calculations independent of Streamlit. No student data is persisted."""
import math
import pandas as pd

ABSENT = {'ab', 'abs', 'absent'}

def analyze(frame, identity, subjects, maxima, pass_mark=40, borderline=5, bands=(80, 65, 50, 40)):
    if not subjects or len(set(identity.values()) & set(subjects)):
        raise ValueError('Select subjects separately from student detail columns.')
    if not 100 >= bands[0] > bands[1] > bands[2] > bands[3] >= 0:
        raise ValueError('Grade boundaries must decrease from A to D between 0 and 100.')
    df = frame.copy().reset_index(drop=True)
    names = df[identity['Name']].fillna('').astype(str).str.strip()
    if names.eq('').any():
        raise ValueError('Every student row needs a name. Remove empty or summary rows.')
    students = pd.DataFrame({'Name': names})
    for label, column in identity.items():
        students[label] = df[column].fillna('').astype(str).str.strip()
    if 'Student ID' in students:
        ids = students['Student ID']
        if ids.eq('').any() or ids.duplicated().any():
            raise ValueError('Student IDs must be filled and unique.')
    records = []
    percentages = pd.DataFrame(index=df.index)
    statuses = pd.DataFrame(index=df.index)
    for subject in subjects:
        try:
            maximum = float(maxima[subject])
        except (TypeError, ValueError):
            raise ValueError('Maximum marks must be positive numbers.')
        if not math.isfinite(maximum) or maximum <= 0:
            raise ValueError('Maximum marks must be positive.')
        raw = df[subject].fillna('').astype(str).str.strip()
        absent = raw.str.lower().isin(ABSENT)
        missing = raw.eq('')
        values = pd.to_numeric(raw.mask(absent | missing), errors='coerce')
        invalid = (~(absent | missing) & values.isna()) | (values < 0) | (values > maximum)
        if invalid.any():
            raise ValueError(f'{subject}: invalid marks at student row(s) ' + ', '.join(str(i+1) for i in df.index[invalid]))
        pct = values / maximum * 100
        percentages[subject] = pct
        status = pd.Series('Pass', index=df.index)
        status[pct < pass_mark] = 'Fail'
        status[absent] = 'Absent'
        status[missing] = 'Missing'
        statuses[subject] = status
        grade = pct.map(lambda v: '' if pd.isna(v) else next((g for g, b in zip('ABCD', bands) if v >= b), 'E'))
        part = students.copy()
        part['Subject'], part['Mark'], part['Maximum'] = subject, values, maximum
        part['Percentage'], part['Grade'], part['Status'] = pct, grade, status
        records.append(part)
    complete = percentages.notna().all(axis=1)
    students['Average %'] = percentages.mean(axis=1).where(complete)
    students['Failed subjects'] = statuses.apply(lambda row: ', '.join(row.index[row.eq('Fail')]), axis=1)
    students['Unassessed subjects'] = statuses.apply(lambda row: ', '.join(f'{s} ({row[s]})' for s in row.index if row[s] in ('Absent', 'Missing')), axis=1)
    students['Result'] = 'Pass'
    students.loc[students['Failed subjects'].ne(''), 'Result'] = 'Fail'
    students.loc[~complete, 'Result'] = 'Incomplete'
    students['Near threshold'] = percentages.apply(lambda row: ', '.join(row.index[(row >= pass_mark) & (row < pass_mark + borderline)]), axis=1)
    students['Rank'] = students['Average %'].rank(method='min', ascending=False).astype('Int64')
    detail = pd.concat(records, ignore_index=True)
    summary = []
    for subject, group in detail.groupby('Subject', sort=False):
        assessed = group['Percentage'].notna().sum()
        row = {'Subject': subject, 'Assessed': assessed, 'Absent': group.Status.eq('Absent').sum(), 'Missing': group.Status.eq('Missing').sum(), 'Mean %': group.Percentage.mean(), 'Highest %': group.Percentage.max(), 'Lowest %': group.Percentage.min(), 'Pass %': group.Status.eq('Pass').sum()/assessed*100 if assessed else float('nan')}
        row.update({g: group.Grade.eq(g).sum() for g in 'ABCDE'})
        summary.append(row)
    return students, pd.DataFrame(summary), detail

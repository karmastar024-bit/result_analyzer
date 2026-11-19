from io import BytesIO
from html import escape
import pandas as pd


def workbook(sheets):
    out = BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as writer:
        for title, frame in sheets.items():
            frame.to_excel(writer, sheet_name=title, index=False)
            ws = writer.sheets[title]
            ws.freeze_panes = 'A2'
            ws.auto_filter.ref = ws.dimensions
            from openpyxl.styles import Font, PatternFill
            for cell in ws[1]:
                cell.font = Font(color='FFFFFF', bold=True)
                cell.fill = PatternFill('solid', fgColor='19384A')
            for column in ws.columns:
                ws.column_dimensions[column[0].column_letter].width = min(45, max(14, max(len(str(c.value or '')) for c in column)+2))
                for cell in column[1:]:
                    if isinstance(cell.value, str):
                        cell.data_type = 's'
                    if isinstance(cell.value, float):
                        cell.number_format = '0.00'
    return out.getvalue()


def print_report(title, settings, students, subjects):
    html = '<!doctype html><html><head><meta charset="utf-8"><title>Result analysis</title><style>@page{size:A4 landscape;margin:12mm}body{font:12px Arial;color:#19384a}table{border-collapse:collapse;width:100%;margin:20px 0}th,td{border:1px solid #bbb;padding:6px;text-align:left}thead{display:table-header-group}tr{break-inside:avoid}button{padding:10px}@media print{button{display:none}}</style></head><body>'
    html += '<button onclick="window.print()">Print / Save as PDF</button><h1>'+escape(title)+'</h1>'
    html += '<p>'+escape(settings)+'</p><h2>Subject summary</h2>'+subjects.to_html(index=False, float_format=lambda x:f'{x:.2f}', na_rep='—')
    html += '<h2>Student results</h2>'+students.to_html(index=False, float_format=lambda x:f'{x:.2f}', na_rep='—')
    return (html+'</body></html>').encode('utf-8')

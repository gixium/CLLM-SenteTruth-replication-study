import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import LineChart, BarChart, Reference
from openpyxl.utils import get_column_letter

# --- CONFIGURAZIONE PERCORSI ---
FILE_NAMES = {
    'Temp 0':    'temp-0_Research-project_GPT4o-mini.xlsx',
    'Temp 1':    'temp-default_Research-project_GPT4o-mini.xlsx',
    'Temp 1.5':  'temp-1.5_Research-project_GPT4o-mini.xlsx',
    'Seed 4321': 'seed-4321_Research-project_GPT4o-mini.xlsx'
}

TEMPS = ['Temp 0', 'Temp 1', 'Temp 1.5', 'Seed 4321']

if os.path.exists('results'):
    BASE_DIR = 'results'
else:
    BASE_DIR = '.'

LOCAL = {tk: os.path.join(BASE_DIR, name) for tk, name in FILE_NAMES.items()}

# --- CONFIGURAZIONE SHEETS ---
SINGLE_SHEETS = [
    'gpt4omini_single_100',
    'gpt4omini_single_60',
    'gpt4omini_single_100_2',
    'gpt4omini_single_60_2',
]
SHUF_SHEET = {s: s.replace('single', 'shuffle') for s in SINGLE_SHEETS}

COND_LABEL = {
    'gpt4omini_single_100':   '60/40 · MIX · 100 nodes',
    'gpt4omini_single_60':    '60/40 · PRO · 60 nodes',
    'gpt4omini_single_100_2': '70/30 · MIX · 100 nodes',
    'gpt4omini_single_60_2':  '70/30 · PRO · 60 nodes',
}
COND_SHORT = {k: v.replace(' · ', ' ') for k, v in COND_LABEL.items()}

# --- LETTURA METADATI ---
print("Analisi file sorgente in corso...")
LAST_ROWS = {}
SHUF_RUNS = {}

for sh in SINGLE_SHEETS:
    try:
        df_single = pd.read_excel(LOCAL['Temp 1'], sheet_name=sh, header=None)
        LAST_ROWS[sh] = len(df_single)
        
        SHUF_RUNS[sh] = {}
        shuf_name = SHUF_SHEET[sh]
        for tk in TEMPS:
            df_shuf = pd.read_excel(LOCAL[tk], sheet_name=shuf_name, header=None)
            acc = []
            for row_idx in [1, 3]: 
                vals = df_shuf.iloc[row_idx, 14:].dropna().values
                acc.extend([float(v) for v in vals if isinstance(v, (int, float))])
            SHUF_RUNS[sh][tk] = acc[:30]
    except Exception as e:
        print(f"Nota: Impossibile leggere metadati per {sh}: {e}")
        LAST_ROWS[sh] = 20

# --- BUILDER FORMULE ESTERNE ---
def ext(tk, sheet_name, cell):
    filename = FILE_NAMES[tk]
    return f"='[{filename}]{sheet_name}'!{cell}"

# --- HELPERS STILE ---
def apply_style(cell, bold=False, bg=None, fmt=None, align='center'):
    cell.font = Font(name='Calibri', bold=bold, size=10)
    if bg: cell.fill = PatternFill('solid', fgColor=bg)
    cell.alignment = Alignment(horizontal=align, vertical='center', wrap_text=True)
    side = Side(style='thin', color='BFBFBF')
    cell.border = Border(left=side, right=side, top=side, bottom=side)
    if fmt: cell.number_format = fmt

# --- CREAZIONE WORKBOOK ---
wb = Workbook()
wb.remove(wb.active)

# --- FOGLIO 1: SUMMARY ---
ws1 = wb.create_sheet("Summary")
ws1.sheet_view.showGridLines = False

col_widths = [25, 12, 12, 12, 12, 12, 12, 12]
for i, w in enumerate(col_widths, 1):
    ws1.column_dimensions[get_column_letter(i)].width = w

ws1['A1'] = "Blockchain LLM Oracle — Comprehensive Temperature & Seed Comparison"
ws1['A1'].font = Font(bold=True, size=14)

headers = ['Condition', 'Config', 'Sys. Acc', 'Mal. Wins', 'Final Delta', 'Avg Shuf', 'Max Shuf', 'Min Shuf']
for i, h in enumerate(headers, 1):
    apply_style(ws1.cell(4, i, h), bold=True, bg='D9D9D9')

curr_row = 5
chart_map = {}
for sh in SINGLE_SHEETS:
    chart_map[sh] = []
    for tk in TEMPS:
        bg = 'F2F2F2' if curr_row % 2 == 0 else 'FFFFFF'
        apply_style(ws1.cell(curr_row, 1, COND_LABEL[sh]), align='left', bg=bg)
        apply_style(ws1.cell(curr_row, 2, tk), bg=bg)
        apply_style(ws1.cell(curr_row, 3, ext(tk, sh, 'O5')), fmt='0.0%', bg=bg)
        apply_style(ws1.cell(curr_row, 4, ext(tk, sh, 'O4')), bg=bg)
        apply_style(ws1.cell(curr_row, 5, ext(tk, sh, 'O6')), fmt='+0.000', bold=True, bg=bg)
        shuf = SHUF_SHEET[sh]
        apply_style(ws1.cell(curr_row, 6, ext(tk, shuf, 'AA4')), fmt='0.0%', bg=bg)
        apply_style(ws1.cell(curr_row, 7, ext(tk, shuf, 'AA2')), fmt='0.0%', bg=bg)
        apply_style(ws1.cell(curr_row, 8, ext(tk, shuf, 'AA3')), fmt='0.0%', bg=bg)
        chart_map[sh].append(curr_row)
        curr_row += 1

# --- STAGING AREA PER GRAFICI ---
L_COL = 12

# FIX: Aggiunte le intestazioni della riga 4 (essenziali per evitare l'errore file corrotto)
ws1.cell(4, L_COL, "Condition")
for ti, tk in enumerate(TEMPS):
    ws1.cell(4, L_COL + ti + 1, tk)

for i, sh in enumerate(SINGLE_SHEETS):
    r = 5 + i
    ws1.cell(r, L_COL, COND_SHORT[sh])
    for ti, tk in enumerate(TEMPS):
        source_row = chart_map[sh][ti]
        ws1.cell(r, L_COL + ti + 1, f"=E{source_row}") 

# Grafico a Barre
bar = BarChart()
bar.title = "Final Delta Comparison (Negative is better)"
bar.y_axis.title = "Delta Value"
bar.height, bar.width = 12, 22
data = Reference(ws1, min_col=L_COL+1, max_col=L_COL+len(TEMPS), min_row=4, max_row=8)
cats = Reference(ws1, min_col=L_COL, min_row=5, max_row=8)
bar.add_data(data, titles_from_data=True)
bar.set_categories(cats)
ws1.add_chart(bar, "A22")

# --- FOGLIO 2: DELTA TRENDS ---
ws2 = wb.create_sheet("Delta Trends")
for i, sh in enumerate(SINGLE_SHEETS):
    col_off = 1 + (i * 6)
    ws2.cell(1, col_off, COND_LABEL[sh]).font = Font(bold=True)
    ws2.cell(2, col_off, "Round")
    
    # FIX: Il calcolo della riga massima ora è esatto, senza prendere righe vuote
    max_data_row = 2 + LAST_ROWS[sh] 
    
    for ti, tk in enumerate(TEMPS):
        ws2.cell(2, col_off + ti + 1, tk)
        for r in range(LAST_ROWS[sh]):
            ws2.cell(3 + r, col_off, r)
            ws2.cell(3 + r, col_off + ti + 1, ext(tk, sh, f"L{r+2}"))
    
    chart = LineChart()
    chart.title = f"Delta Trend: {COND_SHORT[sh]}"
    chart.height, chart.width = 10, 18
    
    d = Reference(ws2, min_col=col_off+1, max_col=col_off+len(TEMPS), min_row=2, max_row=max_data_row)
    chart.add_data(d, titles_from_data=True)
    ws2.add_chart(chart, get_column_letter(col_off) + str(max_data_row + 2))

# --- SALVATAGGIO ---
output_file = "Dashboard_Oracle_Final.xlsx"
output_path = os.path.join(BASE_DIR, output_file)
wb.save(output_path)
print(f"\nDashboard generata correttamente in: {output_path}")
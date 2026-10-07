"""
Step 5 - EXCEL WORKBOOK
Builds excel/AI_Layoffs_2026_Analysis.xlsx:
  Cover          project summary + navigation
  Dashboard      interactive: pick an industry, every KPI/table/chart recalculates
                 (SUMIFS / COUNTIFS / AVERAGEIFS on named ranges, data validation,
                 conditional formatting, native Excel charts)
  Data           475 clean events as an Excel Table (tblLayoffs)
  Data_Quality   every issue found in cleaning and how it was handled
  Dictionary     column definitions
A PivotTable + slicers sheet is added afterwards by excel/add_pivot_and_recalc.ps1
(runs Excel itself, recalculates, and checks for formula errors).

Run:  python python/05_build_excel.py
"""
from pathlib import Path
import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.formatting.rule import DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parents[1]
PROC, XL = ROOT / "data" / "processed", ROOT / "excel"
XL.mkdir(exist_ok=True)
OUT = XL / "AI_Layoffs_2026_Analysis.xlsx"

df = pd.read_csv(PROC / "layoffs_clean.csv", parse_dates=["event_date", "month_start"])
dq = pd.read_csv(PROC / "data_quality_log.csv")

FONT = "Arial"
ACCENT, INK, INK2, GREY, LIGHT = "EB6834", "0B0B0B", "52514E", "C9C8C2", "F4F3EF"
F = lambda **kw: Font(name=FONT, **{"color": INK, **kw})
fill = lambda c: PatternFill("solid", start_color=c, end_color=c)
thin = Side(style="thin", color="E6E5E0")
BOX = Border(bottom=thin)

wb = Workbook()

# =================================================================== Data sheet
ws = wb.active
ws.title = "Data"
cols = list(df.columns)
ws.append(cols)
for row in df.itertuples(index=False):
    ws.append([None if pd.isna(v) else (v.to_pydatetime() if isinstance(v, pd.Timestamp) else v) for v in row])
n = len(df) + 1
tbl = Table(displayName="tblLayoffs", ref=f"A1:{get_column_letter(len(cols))}{n}")
tbl.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=True)
ws.add_table(tbl)
ws.freeze_panes = "C2"
fmt = {"people_cut": "#,##0", "total_workforce": "#,##0", "workforce_pct": "0.0%",
       "event_date": "yyyy-mm-dd", "month_start": "mmm yyyy"}
for i, c in enumerate(cols, 1):
    L = get_column_letter(i)
    ws.column_dimensions[L].width = min(max(len(c) + 2, df[c].astype(str).str.len().quantile(0.9) + 2), 45)
    for cell in ws[L][1:]:
        cell.font = F(size=10)
        if c in fmt:
            cell.number_format = fmt[c]
    ws[f"{L}1"].font = F(bold=True, size=10)

# named ranges on plain absolute refs (robust in every Excel version)
for name in ["industry", "category_label", "people_cut", "is_ai_driven", "month_start",
             "workforce_pct", "is_shutdown", "company_size_band", "sector_group"]:
    L = get_column_letter(cols.index(name) + 1)
    wb.defined_names[f"d_{name}"] = DefinedName(f"d_{name}", attr_text=f"Data!${L}$2:${L}${n}")

# =================================================================== Dashboard
ds = wb.create_sheet("Dashboard", 0)
ds.sheet_view.showGridLines = False
for L, w in zip("ABCDEFGHIJKLMN", [2, 26, 14, 14, 14, 14, 3, 30, 13, 13, 13, 12, 3, 3]):
    ds.column_dimensions[L].width = w

ds["B2"] = "AI Layoffs 2026 - Interactive Excel Dashboard"
ds["B2"].font = F(bold=True, size=18)
ds["B3"] = "Pick an industry in the orange cell - every number and chart on this sheet recalculates."
ds["B3"].font = F(size=10, color=INK2)

ds["B5"] = "Industry filter  >"
ds["B5"].font = F(bold=True)
ds["C5"] = "All"
ds.merge_cells("C5:E5")
ds["C5"].fill = fill("FFE3D6")
ds["C5"].font = F(bold=True, color="0000FF")  # blue = input
ds["C5"].alignment = Alignment(horizontal="center")
industries = sorted(df["industry"].unique())
# list for validation lives on the Dictionary-adjacent helper area (hidden column N)
ds["N1"] = "All"
for i, ind in enumerate(industries, 2):
    ds[f"N{i}"] = ind
ds.column_dimensions["N"].hidden = True
dv = DataValidation(type="list", formula1=f"=$N$1:$N${len(industries) + 1}", allow_blank=False)
ds.add_data_validation(dv)
dv.add("C5")
ds["F5"] = '=IF(C5="All","*",C5)'          # wildcard criterion used by every formula below
ds["F5"].font = F(size=8, color="FFFFFF")  # helper, kept invisible on the dashboard
SEL = "$F$5"

# ---- KPI tiles
kpis = [
    ("Layoff events", f'=COUNTIFS(d_industry,{SEL})', "#,##0"),
    ("Jobs cut", f'=SUMIFS(d_people_cut,d_industry,{SEL})', "#,##0"),
    ("AI-driven jobs", f'=SUMIFS(d_people_cut,d_industry,{SEL},d_is_ai_driven,1)', "#,##0"),
    ("AI share of jobs", "=IFERROR(E8/D8,0)", "0.0%"),
    ("Avg jobs / event", "=IFERROR(D8/C8,0)", "#,##0"),
]
for j, (label, formula, nf) in enumerate(kpis):
    col = get_column_letter(3 + j) if j < 4 else "H"
    ds[f"{col}7"] = label
    ds[f"{col}7"].font = F(size=9, color=INK2)
    ds[f"{col}8"] = formula
    ds[f"{col}8"].number_format = nf
    ds[f"{col}8"].font = F(bold=True, size=16, color=ACCENT if "AI" in label else INK)
    for r in (7, 8):
        ds[f"{col}{r}"].fill = fill(LIGHT)
ds["B7"], ds["B8"] = "Headline", "=C5"
ds["B7"].font, ds["B8"].font = F(size=9, color=INK2), F(bold=True, size=12)
ds["B7"].fill = ds["B8"].fill = fill(LIGHT)  # tiles: C=events D=jobs E=AI jobs F=AI share H=avg

def header(row, start_col, labels):
    for k, lab in enumerate(labels):
        c = ds.cell(row=row, column=start_col + k, value=lab)
        c.font = F(bold=True, size=10, color="FFFFFF")
        c.fill = fill(INK)
        c.alignment = Alignment(horizontal="center" if k else "left", wrap_text=True)

# ---- Table 1: by stated reason (B11:F16)
ds["B10"] = "1. Why companies cut - by stated reason"
ds["B10"].font = F(bold=True, size=12)
header(11, 2, ["Reason", "Events", "Jobs cut", "Share of jobs", "Avg jobs/event"])
reasons = ["AI-Driven", "Restructure", "Weak Demand", "Cost Cut", "Merger"]
for i, r in enumerate(reasons, 12):
    ds[f"B{i}"] = r
    ds[f"C{i}"] = f"=COUNTIFS(d_industry,{SEL},d_category_label,B{i})"
    ds[f"D{i}"] = f"=SUMIFS(d_people_cut,d_industry,{SEL},d_category_label,B{i})"
    ds[f"E{i}"] = f"=IFERROR(D{i}/$D$17,0)"
    ds[f"F{i}"] = f"=IFERROR(D{i}/C{i},0)"
ds["B17"], ds["C17"], ds["D17"], ds["E17"], ds["F17"] = "Total", "=SUM(C12:C16)", "=SUM(D12:D16)", "=SUM(E12:E16)", "=IFERROR(D17/C17,0)"
ds["B18"] = "Check: total equals KPI tile"
ds["D18"] = '=IF(D17=D8,"OK","MISMATCH")'
ds["B18"].font = ds["D18"].font = F(size=8, color=INK2, italic=True)

# ---- Table 2: monthly trend (H11:L21)
ds["H10"] = "2. Monthly trend (dated events)"
ds["H10"].font = F(bold=True, size=12)
header(11, 8, ["Month", "Jobs cut", "AI-driven", "Other", "AI share"])
months = pd.date_range("2026-01-01", "2026-10-01", freq="MS")
for i, m in enumerate(months, 12):
    ds[f"H{i}"] = m.to_pydatetime()
    ds[f"H{i}"].number_format = "mmm yyyy"
    ds[f"I{i}"] = f"=SUMIFS(d_people_cut,d_industry,{SEL},d_month_start,H{i})"
    ds[f"J{i}"] = f"=SUMIFS(d_people_cut,d_industry,{SEL},d_month_start,H{i},d_is_ai_driven,1)"
    ds[f"K{i}"] = f"=I{i}-J{i}"
    ds[f"L{i}"] = f"=IFERROR(J{i}/I{i},0)"
last_m = 11 + len(months)
ds[f"H{last_m + 1}"] = "Undated (year / multi-year)"
ds[f"I{last_m + 1}"] = f"=D8-SUM(I12:I{last_m})"
ds[f"H{last_m + 1}"].font = ds[f"I{last_m + 1}"].font = F(size=9, italic=True, color=INK2)

# ---- Table 3: by industry (B24:F37) - not filtered; shows all industries
ds["B23"] = "3. AI share of job cuts by industry (all industries)"
ds["B23"].font = F(bold=True, size=12)
header(24, 2, ["Industry", "Events", "Jobs cut", "AI-driven jobs", "AI share"])
for i, ind in enumerate(industries, 25):
    ds[f"B{i}"] = ind
    ds[f"C{i}"] = f"=COUNTIFS(d_industry,B{i})"
    ds[f"D{i}"] = f"=SUMIFS(d_people_cut,d_industry,B{i})"
    ds[f"E{i}"] = f"=SUMIFS(d_people_cut,d_industry,B{i},d_is_ai_driven,1)"
    ds[f"F{i}"] = f"=IFERROR(E{i}/D{i},0)"
last_i = 24 + len(industries)
ds.conditional_formatting.add(f"F25:F{last_i}", DataBarRule(start_type="num", start_value=0, end_type="num",
                                                            end_value=1, color=ACCENT))

# number formats + fonts for all tables
for row in ds.iter_rows(min_row=12, max_row=last_i, min_col=2, max_col=12):
    for c in row:
        if c.row not in (23, 24) and c.value is not None and not c.font.italic:
            c.font = F(size=10)
            c.border = BOX
for r in range(12, 18):
    ds[f"C{r}"].number_format = ds[f"D{r}"].number_format = ds[f"F{r}"].number_format = "#,##0"
    ds[f"E{r}"].number_format = "0.0%"
for r in range(12, last_m + 2):
    for L in "IJK":
        ds[f"{L}{r}"].number_format = "#,##0"
    ds[f"L{r}"].number_format = "0.0%"
for r in range(25, last_i + 1):
    ds[f"C{r}"].number_format = ds[f"D{r}"].number_format = ds[f"E{r}"].number_format = "#,##0"
    ds[f"F{r}"].number_format = "0.0%"
ds["B17"].font = ds["C17"].font = ds["D17"].font = ds["E17"].font = ds["F17"].font = F(bold=True, size=10)
ds["E17"].number_format = "0.0%"
ds["C17"].number_format = ds["D17"].number_format = ds["F17"].number_format = "#,##0"
for L in "BCDEFHIJKL":
    ds[f"{L}8"].alignment = Alignment(horizontal="left")

# ---- Charts
c1 = BarChart(); c1.type = "bar"; c1.style = 2
c1.title = "Jobs cut by stated reason"
c1.add_data(Reference(ds, min_col=4, min_row=11, max_row=16), titles_from_data=True)
c1.set_categories(Reference(ds, min_col=2, min_row=12, max_row=16))
c1.legend = None; c1.y_axis.majorGridlines = None
c1.series[0].graphicalProperties.solidFill = ACCENT
c1.y_axis.numFmt = "#,##0"; c1.x_axis.scaling.orientation = "maxMin"
c1.dataLabels = DataLabelList(); c1.dataLabels.showVal = True
for flag in ("showSerName", "showCatName", "showLegendKey", "showPercent"):
    setattr(c1.dataLabels, flag, False)
c1.height, c1.width = 7.5, 15
ds.add_chart(c1, "H39")

c2 = BarChart(); c2.type = "col"; c2.grouping = "stacked"; c2.overlap = 100
c2.title = "Monthly jobs cut: AI-driven vs other"
c2.add_data(Reference(ds, min_col=10, max_col=11, min_row=11, max_row=last_m), titles_from_data=True)
c2.set_categories(Reference(ds, min_col=8, min_row=12, max_row=last_m))
c2.series[0].graphicalProperties.solidFill = ACCENT
c2.series[1].graphicalProperties.solidFill = GREY
c2.x_axis.number_format = "mmm"; c2.y_axis.numFmt = "#,##0"
c2.height, c2.width = 7.5, 15
ds.add_chart(c2, "H23")

c3 = BarChart(); c3.type = "bar"
c3.title = "AI share of job cuts by industry"
c3.add_data(Reference(ds, min_col=6, min_row=24, max_row=last_i), titles_from_data=True)
c3.set_categories(Reference(ds, min_col=2, min_row=25, max_row=last_i))
c3.legend = None; c3.series[0].graphicalProperties.solidFill = ACCENT
c3.y_axis.numFmt = "0%"; c3.y_axis.scaling.min = 0; c3.y_axis.scaling.max = 1
c3.x_axis.scaling.orientation = "maxMin"
c3.height, c3.width = 9, 15
ds.add_chart(c3, "B40")

for ch in (c1, c2, c3):  # openpyxl hides axes by default in recent Excel builds
    ch.x_axis.delete = False
    ch.y_axis.delete = False
c3.y_axis.majorGridlines = None
# horizontal bars carry value labels, so drop the value axis (it collides with the title)
c1.y_axis.delete = True
c3.y_axis.delete = True
c3.dataLabels = DataLabelList(); c3.dataLabels.showVal = True
for flag in ("showSerName", "showCatName", "showLegendKey", "showPercent"):
    setattr(c3.dataLabels, flag, False)
ds["B39"] = "Charts update with the filter (except the industry chart, which always shows all industries)."
ds["B39"].font = F(size=9, italic=True, color=INK2)
ds.freeze_panes = "A10"

# =================================================================== Data quality + dictionary
q = wb.create_sheet("Data_Quality")
q.append(["Check", "Rows affected", "Action taken"])
for r in dq.itertuples(index=False):
    q.append(list(r))
for c, w in zip("ABC", [55, 14, 80]):
    q.column_dimensions[c].width = w
for row in q.iter_rows():
    for c in row:
        c.font = F(size=10, bold=c.row == 1)
        c.alignment = Alignment(wrap_text=True, vertical="top")

d = wb.create_sheet("Dictionary")
desc = {
    "event_id": "Surrogate key, one row per layoff announcement",
    "company": "Company name as reported",
    "industry": "Industry (13 groups, from source)",
    "sector_group": "Tech & Digital (Tech, Crypto & Fintech, Telecom) vs Non-Tech - derived",
    "category_label": "Stated reason: AI-Driven, Restructure, Cost Cut, Weak Demand, Merger",
    "is_ai_driven": "1 if the company cited AI/automation as the reason",
    "people_cut": "Jobs cut in this announcement",
    "total_workforce": "Company headcount at time of announcement",
    "workforce_pct": "people_cut / total_workforce (decimal)",
    "event_date": "Announcement date (blank when source gave only a year or multi-year plan)",
    "month_start": "First day of the announcement month - used for monthly trends",
    "date_precision": "Day / Month / Year / Multi-year plan - how precise the source date was",
    "period_label": "Readable period, e.g. 'Mar 2026' or '2025-30 program'",
    "date_raw": "Date exactly as published in the source",
    "company_size_band": "Workforce band: <1K, 1K-10K, 10K-50K, 50K-100K, 100K+",
    "severity_band": "Share of workforce cut: <5%, 5-10%, 10-25%, 25-99%, Shutdown",
    "layoff_size_band": "Jobs cut band: <100, 100-499, 500-999, 1K-4.9K, 5K+",
    "is_shutdown": "1 if 100% of workforce cut (closure)",
    "company_event_no": "Nth layoff by this company in 2026 (chronological)",
    "company_event_count": "Total 2026 layoff events by this company",
    "is_repeat_layoffer": "1 if the company announced more than one layoff in 2026",
    "source_type": "News media / Government WARN filing / Company (SEC) filing - from URL domain",
    "source_domain": "Domain of the source article",
    "source_url": "Link to the original report",
}
d.append(["Column", "Description"])
for c in cols:
    d.append([c, desc.get(c, "")])
d.append([])
d.append(["Source", "layoffhedge. (2026). 2026 Layoff Dataset. Retrieved 2026-10-06, from https://layoffhedge.com/data/ (free to use with attribution)"])
d.append(["Macro source", "U.S. BLS JOLTS (JTSLDL, JTU510099LDL, JTSJOL) and CPS (UNRATE) via FRED, Federal Reserve Bank of St. Louis"])
d.column_dimensions["A"].width, d.column_dimensions["B"].width = 24, 110
for row in d.iter_rows():
    for c in row:
        c.font = F(size=10, bold=c.row == 1 or c.column == 1)

# =================================================================== Cover
cv = wb.create_sheet("Cover", 0)
cv.sheet_view.showGridLines = False
cv.column_dimensions["A"].width, cv.column_dimensions["B"].width = 3, 110
lines = [
    ("Did AI really take the jobs?  |  2026 Layoffs Analysis", F(bold=True, size=20)),
    ("Excel workbook - part of an end-to-end Python > SQL > Excel > Power BI portfolio project", F(size=11, color=INK2)),
    ("", None),
    ("Sheets", F(bold=True, size=12)),
    ("Dashboard     Interactive KPIs, tables and charts - choose an industry in the orange cell", F(size=11)),
    ("Pivot         PivotTable with slicers (reason x industry), built in Excel", F(size=11)),
    ("Data          475 cleaned layoff events (Excel Table: tblLayoffs)", F(size=11)),
    ("Data_Quality  Every data issue found during cleaning and how it was handled", F(size=11)),
    ("Dictionary    Column definitions and sources", F(size=11)),
    ("", None),
    ("Colour key: blue text in an orange cell = input you can change. Black = formula.", F(size=10, italic=True, color=INK2)),
    ("", None),
    ("Data: layoffhedge.com 2026 Layoff Dataset (as of 6 Oct 2026, free with attribution); BLS JOLTS via FRED.", F(size=9, color=INK2)),
]
for i, (t, f) in enumerate(lines, 2):
    cv[f"B{i}"] = t
    if f:
        cv[f"B{i}"].font = f

wb.active = 1  # open on Dashboard
wb.save(OUT)
print("Workbook ->", OUT)

"""
Step 6 - POWER BI PROJECT (.pbip)
Generates a ready-to-open Power BI Project in powerbi/:
  AI_Layoffs_2026.pbip                    <- double-click this
  AI_Layoffs_2026.SemanticModel/          star-schema model in TMDL (tables, relationships, 35 measures)
  AI_Layoffs_2026.Report/                 report in PBIR format (3 pages, theme)

Open it in Power BI Desktop, click Refresh if prompted, then File > Save as > .pbix if you want a single file.
The model reads the CSVs in data/processed/ through the ProjectFolder parameter
(Transform data > Edit parameters to point it somewhere else).

Run:  python python/06_build_pbip.py
"""
from pathlib import Path
import json
import shutil
import uuid

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
PBI = ROOT / "powerbi"
NAME = "AI_Layoffs_2026"
SM = PBI / f"{NAME}.SemanticModel"
RP = PBI / f"{NAME}.Report"
DATA_FOLDER = str(PROC) + "\\"

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric"
V_VISUAL, V_PAGE, V_REPORT = "2.7.0", "2.1.0", "3.2.0"


def tag(*parts):
    """Deterministic lineage tag so regenerating doesn't churn the files."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "ai-layoffs-2026/" + "/".join(parts)))


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_json(path: Path, obj):
    write(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def q(name):  # TMDL object name quoting
    return f"'{name}'" if any(c in name for c in " %#.-=:'()") else name


# ============================================================ semantic model
TABLES = {
    "fact_layoff_events": {
        "event_id": "int64", "company_id": "int64", "industry_id": "int64", "category_id": "int64",
        "date_key": "int64", "date_precision": "string", "period_label": "string", "people_cut": "int64",
        "total_workforce": "int64", "workforce_pct": "double", "is_ai_driven": "int64", "is_shutdown": "int64",
        "severity_band": "string", "layoff_size_band": "string", "company_event_no": "int64",
        "source_type": "string", "source_url": "string"},
    "dim_company": {
        "company_id": "int64", "company": "string", "industry": "string", "total_workforce": "int64",
        "company_size_band": "string", "is_repeat_layoffer": "int64"},
    "dim_industry": {"industry_id": "int64", "industry": "string", "sector_group": "string"},
    "dim_category": {"category_id": "int64", "category_label": "string", "description": "string", "sort_order": "int64"},
    "dim_date": {
        "date_key": "int64", "date": "dateTime", "year": "int64", "quarter": "string", "month_no": "int64",
        "month_name": "string", "month_start": "dateTime", "week_of_year": "int64", "day_name": "string",
        "is_weekend": "int64"},
    "macro_monthly": {
        "month_start": "dateTime", "us_layoffs_discharges_k": "double", "info_sector_layoffs_k": "double",
        "us_job_openings_k": "double", "unemployment_rate_pct": "double", "year": "int64",
        "openings_per_layoff": "double"},
}
# sanity: columns must match the CSVs exactly
for t, cols in TABLES.items():
    assert list(pd.read_csv(PROC / f"{t}.csv", nrows=0).columns) == list(cols), t

M_TYPE = {"int64": "Int64.Type", "string": "type text", "double": "type number", "dateTime": "type date"}
HIDDEN = {"event_id", "company_id", "industry_id", "category_id", "date_key"}
FORMATS = {"workforce_pct": "0.0%", "people_cut": "#,0", "total_workforce": "#,0",
           "date": "dd mmm yyyy", "month_start": "mmm yyyy"}
SORT_BY = {("dim_date", "month_name"): "month_no", ("dim_category", "category_label"): "sort_order"}
SUMMARIZE = {"people_cut": "sum", "total_workforce": "sum", "us_layoffs_discharges_k": "average",
             "info_sector_layoffs_k": "average", "us_job_openings_k": "average",
             "unemployment_rate_pct": "average", "openings_per_layoff": "average"}

MEASURES = [  # (folder, name, dax, format)
    ("Core", "Jobs Cut", "SUM ( fact_layoff_events[people_cut] )", "#,0"),
    ("Core", "Layoff Events", "COUNTROWS ( fact_layoff_events )", "#,0"),
    ("Core", "Companies", "DISTINCTCOUNT ( fact_layoff_events[company_id] )", "#,0"),
    ("Core", "Avg Jobs per Event", "DIVIDE ( [Jobs Cut], [Layoff Events] )", "#,0"),
    ("Core", "Median Jobs per Event", "MEDIAN ( fact_layoff_events[people_cut] )", "#,0"),
    ("Core", "Avg Workforce % Cut", "AVERAGE ( fact_layoff_events[workforce_pct] )", "0.0%"),
    ("Core", "Shutdowns", "CALCULATE ( [Layoff Events], fact_layoff_events[is_shutdown] = 1 )", "#,0"),
    ("AI", "AI Jobs Cut", "CALCULATE ( [Jobs Cut], fact_layoff_events[is_ai_driven] = 1 )", "#,0"),
    ("AI", "AI Events", "CALCULATE ( [Layoff Events], fact_layoff_events[is_ai_driven] = 1 )", "#,0"),
    ("AI", "AI Share of Jobs", "DIVIDE ( [AI Jobs Cut], [Jobs Cut] )", "0.0%"),
    ("AI", "AI Share of Events", "DIVIDE ( [AI Events], [Layoff Events] )", "0.0%"),
    ("AI", "Non-AI Jobs Cut", "[Jobs Cut] - [AI Jobs Cut]", "#,0"),
    ("AI", "Avg Jobs per AI Event", "DIVIDE ( [AI Jobs Cut], [AI Events] )", "#,0"),
    ("AI", "Avg Jobs per Non-AI Event", "DIVIDE ( [Non-AI Jobs Cut], [Layoff Events] - [AI Events] )", "#,0"),
    ("AI", "AI Size Multiplier", "DIVIDE ( [Avg Jobs per AI Event], [Avg Jobs per Non-AI Event] )", '0.0"x"'),
    ("AI", "AI Share H1",
     "CALCULATE ( [AI Share of Jobs], DATESBETWEEN ( dim_date[date], DATE ( 2026, 1, 1 ), DATE ( 2026, 6, 30 ) ) )", "0%"),
    ("AI", "AI Share Q3",
     "CALCULATE ( [AI Share of Jobs], DATESBETWEEN ( dim_date[date], DATE ( 2026, 7, 1 ), DATE ( 2026, 9, 30 ) ) )", "0%"),
    ("Time", "Jobs Cut Running Total",
     "VAR _maxDate = MAX ( dim_date[date] )\nRETURN\n    IF (\n        NOT ISBLANK ( [Jobs Cut] ),\n"
     "        CALCULATE ( [Jobs Cut], dim_date[date] <= _maxDate, ALL ( dim_date ),\n"
     "            NOT ISBLANK ( fact_layoff_events[date_key] ) )\n    )", "#,0"),
    ("Time", "Jobs Cut Prev Month", "CALCULATE ( [Jobs Cut], DATEADD ( dim_date[date], -1, MONTH ) )", "#,0"),
    ("Time", "Jobs Cut MoM %", "IF ( NOT ISBLANK ( [Jobs Cut] ), DIVIDE ( [Jobs Cut] - [Jobs Cut Prev Month], [Jobs Cut Prev Month] ) )", "+0%;-0%;0%"),
    ("Time", "Undated Jobs Cut", "CALCULATE ( [Jobs Cut], ISBLANK ( fact_layoff_events[date_key] ) )", "#,0"),
    ("Ranking", "Share of Total Jobs", "DIVIDE ( [Jobs Cut], CALCULATE ( [Jobs Cut], ALLSELECTED () ) )", "0.0%"),
    ("Ranking", "Industry Rank", "RANKX ( ALLSELECTED ( dim_industry[industry] ), [Jobs Cut], , DESC, DENSE )", "0"),
    ("Ranking", "Company Rank", "RANKX ( ALLSELECTED ( dim_company[company] ), [Jobs Cut], , DESC, DENSE )", "0"),
    ("Ranking", "Repeat Layoffers", "CALCULATE ( [Companies], dim_company[is_repeat_layoffer] = 1 )", "#,0"),
    ("Macro", "US Avg Monthly Layoffs 2026",
     "CALCULATE ( AVERAGE ( macro_monthly[us_layoffs_discharges_k] ) * 1000, macro_monthly[year] = 2026 )", "#,0"),
    ("Macro", "US Monthly Layoffs", "AVERAGE ( macro_monthly[us_layoffs_discharges_k] ) * 1000", "#,0"),
    ("Macro", "AI Jobs vs One US Month",
     "DIVIDE ( CALCULATE ( [AI Jobs Cut], REMOVEFILTERS () ), [US Avg Monthly Layoffs 2026] )", "0%"),
    ("Formatting", "Bar Colour AI",
     'IF (\n    SELECTEDVALUE ( dim_category[category_label] ) = "AI-Driven",\n    "#EB6834",\n    "#C9C8C2"\n)', None),
    ("Formatting", "Bar Colour Industry AI Share", 'IF ( [AI Share of Jobs] >= 0.5, "#EB6834", "#C9C8C2" )', None),
    ("Formatting", "Title Overview",
     'VAR _scope =\n    IF (\n        ISFILTERED ( dim_industry[industry] ),\n'
     '        CONCATENATEX ( VALUES ( dim_industry[industry] ), dim_industry[industry], ", " ),\n'
     '        "all industries"\n    )\nRETURN\n'
     '    "AI was blamed for " & FORMAT ( [AI Share of Jobs], "0%" ) & " of 2026 job cuts  |  " & _scope', None),
    ("Formatting", "Subtitle Overview",
     '"AI was named in " & FORMAT ( [AI Share of Events], "0%" ) & " of layoff events, but AI-driven layoffs were "\n'
     '    & FORMAT ( [AI Size Multiplier], "0.0" ) & "x bigger on average (" & FORMAT ( [Avg Jobs per AI Event], "#,0" )\n'
     '    & " vs " & FORMAT ( [Avg Jobs per Non-AI Event], "#,0" ) & " jobs)."', None),
    ("Formatting", "Data As Of", '"Data as of 6 Oct 2026  |  layoffhedge.com 2026 Layoff Dataset, BLS JOLTS via FRED"', None),
]


def m_partition(t, cols):
    types = ", ".join(f'{{"{c}", {M_TYPE[d]}}}' for c, d in cols.items())
    return [
        "let",
        f'    Source = Csv.Document(File.Contents(ProjectFolder & "{t}.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
        "    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),",
        f'    Typed = Table.TransformColumnTypes(Promoted, {{{types}}}, "en-US")',
        "in",
        "    Typed",
    ]


def table_tmdl(t, cols):
    out = [f"table {t}", f"\tlineageTag: {tag(t)}"]
    if t == "dim_date":
        out.append("\tdataCategory: Time")
    out.append("")
    for c, dt in cols.items():
        out.append(f"\tcolumn {q(c)}")
        out.append(f"\t\tdataType: {dt}")
        if t == "dim_date" and c == "date":
            out.append("\t\tisKey")
        if c in FORMATS:
            out.append(f"\t\tformatString: {FORMATS[c]}")
        elif dt == "int64":
            out.append("\t\tformatString: 0")
        if c in HIDDEN or (t != "fact_layoff_events" and c.endswith("_id")):
            out.append("\t\tisHidden")
        out.append(f"\t\tlineageTag: {tag(t, c)}")
        out.append(f"\t\tsummarizeBy: {SUMMARIZE.get(c, 'none')}")
        out.append(f"\t\tsourceColumn: {c}")
        if (t, c) in SORT_BY:
            out.append(f"\t\tsortByColumn: {SORT_BY[(t, c)]}")
        if c == "source_url":
            out.append("\t\tdataCategory: WebUrl")
        out.append("")
        out.append("\t\tannotation SummarizationSetBy = User")
        if dt == "dateTime":
            out.append("")
            out.append("\t\tannotation UnderlyingDateTimeDataType = Date")
        out.append("")
    out.append(f"\tpartition {t} = m")
    out.append("\t\tmode: import")
    out.append("\t\tsource =")
    out += ["\t\t\t\t" + line for line in m_partition(t, cols)]
    out.append("")
    out.append("\tannotation PBI_ResultType = Table")
    return "\n".join(out) + "\n"


def measures_tmdl():
    out = ["table _Measures", f"\tlineageTag: {tag('_Measures')}", ""]
    for folder, name, dax, fmt in MEASURES:
        if "\n" in dax:
            out.append(f"\tmeasure {q(name)} =")
            out += ["\t\t\t" + line for line in dax.split("\n")]
        else:
            out.append(f"\tmeasure {q(name)} = {dax}")
        if fmt:
            out.append(f"\t\tformatString: {fmt}")
        out.append(f"\t\tdisplayFolder: {folder}")
        out.append(f"\t\tlineageTag: {tag('_Measures', name)}")
        out.append("")
    out += ["\tcolumn Value", "\t\tdataType: int64", "\t\tisHidden", "\t\tformatString: 0",
            f"\t\tlineageTag: {tag('_Measures', 'Value')}", "\t\tsummarizeBy: none", "\t\tisNameInferred",
            "\t\tsourceColumn: [Value]", "", "\t\tannotation SummarizationSetBy = Automatic", "",
            "\tpartition _Measures = calculated", "\t\tmode: import", '\t\tsource = ROW ( "Value", 0 )', "",
            "\tannotation PBI_Id = " + tag("pbi", "_Measures").replace("-", "")]
    return "\n".join(out) + "\n"


RELATIONSHIPS = [("company_id", "dim_company"), ("industry_id", "dim_industry"),
                 ("category_id", "dim_category"), ("date_key", "dim_date")]

all_tables = ["_Measures"] + list(TABLES)
model_tmdl = "\n".join([
    "model Model",
    "\tculture: en-US",
    "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
    "\tdiscourageImplicitMeasures",
    "\tsourceQueryCulture: en-US",
    "\tdataAccessOptions",
    "\t\tlegacyRedirects",
    "\t\treturnErrorValuesAsNull",
    "",
    "annotation __PBI_TimeIntelligenceEnabled = 0",
    "",
    "annotation PBI_QueryOrder = " + json.dumps(["ProjectFolder"] + list(TABLES)),
    "",
    "annotation PBIDesktopVersion = 2.158.1177.0",
    "",
    *[f"ref table {q(t)}" for t in all_tables],
]) + "\n"

expressions_tmdl = "\n".join([
    f'expression ProjectFolder = "{DATA_FOLDER}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]',
    f"\tlineageTag: {tag('ProjectFolder')}",
    "",
    "\tannotation PBI_ResultType = Text",
]) + "\n"

relationships_tmdl = "\n".join(
    "\n".join([f"relationship {tag('rel', key)}",
               f"\tfromColumn: fact_layoff_events.{key}",
               f"\ttoColumn: {dim}.{key}", ""])
    for key, dim in RELATIONSHIPS)

# ============================================================ report helpers
def measure(name, entity="_Measures"):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": name}}


def column(entity, prop):
    return {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def proj(field, active=None, display=None):
    kind = "Measure" if "Measure" in field else "Column"
    ent = field[kind]["Expression"]["SourceRef"]["Entity"]
    prop = field[kind]["Property"]
    p = {"field": field, "queryRef": f"{ent}.{prop}", "nativeQueryRef": prop}
    if active is not None:
        p["active"] = active
    if display:
        p["displayName"] = display
    return p


def lit(v):
    if isinstance(v, bool):
        return {"expr": {"Literal": {"Value": "true" if v else "false"}}}
    if isinstance(v, (int, float)):
        return {"expr": {"Literal": {"Value": f"{v}D"}}}
    return {"expr": {"Literal": {"Value": f"'{v}'"}}}


def color(hex_):
    return {"solid": {"color": lit(hex_)}}


def title_obj(text, size=12):
    return {"title": [{"properties": {"show": lit(True), "text": lit(text), "fontSize": lit(size)}}]}


def padding(px):
    return {"padding": [{"properties": {k: lit(px) for k in ("top", "bottom", "left", "right")}}]}


def no_title():
    return {"title": [{"properties": {"show": lit(False)}}]}


def container(name, x, y, w, h, visual, z=0, filters=None):
    c = {"$schema": f"{SCHEMA}/item/report/definition/visualContainer/{V_VISUAL}/schema.json",
         "name": name, "position": {"x": x, "y": y, "z": z, "width": w, "height": h, "tabOrder": z},
         "visual": visual}
    if filters:
        c["filterConfig"] = {"filters": filters}
    return c


def card(name, x, y, w, h, m, label, accent=False, size=24, units=None, precision=None):
    label_props = {"fontSize": lit(size), "color": color("#EB6834" if accent else "#0B0B0B"),
                   "fontFamily": lit("Segoe UI Semibold")}
    if units is not None:
        label_props["labelDisplayUnits"] = lit(units)
    if precision is not None:
        label_props["labelPrecision"] = lit(precision)
    return container(name, x, y, w, h, {
        "visualType": "card",
        "query": {"queryState": {"Values": {"projections": [proj(measure(m))]}}},
        "objects": {
            "labels": [{"properties": label_props}],
            "categoryLabels": [{"properties": {"show": lit(False)}}],  # the title already names the number
        },
        "visualContainerObjects": {**title_obj(label, 10), **padding(8)},
        "drillFilterOtherVisuals": True,
    })


def text_card(name, x, y, w, h, m, size, bold=False, fg="#0B0B0B", bg=None):
    vco = {**no_title(), **padding(0),
           "background": [{"properties": {"show": lit(bg is not None), **({"color": color(bg)} if bg else {})}}],
           "border": [{"properties": {"show": lit(False)}}]}
    return container(name, x, y, w, h, {
        "visualType": "card",
        "query": {"queryState": {"Values": {"projections": [proj(measure(m))]}}},
        "objects": {
            "labels": [{"properties": {"fontSize": lit(size), "color": color(fg), "bold": lit(bold),
                                       "fontFamily": lit("Segoe UI Semibold" if bold else "Segoe UI")}}],
            "categoryLabels": [{"properties": {"show": lit(False)}}],
            "wordWrap": [{"properties": {"show": lit(True)}}],
        },
        "visualContainerObjects": vco,
    })


def textbox(name, x, y, w, h, runs):
    """runs: list of paragraphs; each paragraph = list of (text, size_pt, bold, colour)."""
    paragraphs = [{"textRuns": [{"value": t, "textStyle": {"fontSize": f"{s}pt", "color": c,
                                                           **({"fontWeight": "bold"} if b else {})}}
                                for t, s, b, c in para]} for para in runs]
    return container(name, x, y, w, h, {
        "visualType": "textbox",
        "objects": {"general": [{"properties": {"paragraphs": paragraphs}}]},
        "visualContainerObjects": {"background": [{"properties": {"show": lit(False)}}],
                                   "border": [{"properties": {"show": lit(False)}}], **padding(2)},
    })


def slicer(name, x, y, w, h, entity, prop, label, mode="Dropdown"):
    return container(name, x, y, w, h, {
        "visualType": "slicer",
        "query": {"queryState": {"Values": {"projections": [proj(column(entity, prop), active=True)]}}},
        "objects": {"data": [{"properties": {"mode": lit(mode)}}],
                    "header": [{"properties": {"show": lit(True), "text": lit(label)}}]},
        "visualContainerObjects": {**no_title()},
    })


def colour_by_measure(m):
    return [{"properties": {"fill": {"solid": {"color": {"expr": measure(m)}}}},
             "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}}]


def bar(name, x, y, w, h, cat, val, title, colour_measure=None, sort_desc=True, pct=False):
    vis = {
        "visualType": "clusteredBarChart",
        "query": {"queryState": {"Category": {"projections": [proj(cat, active=True)]},
                                 "Y": {"projections": [proj(val)]}}},
        "objects": {
            "labels": [{"properties": {"show": lit(True), "fontSize": lit(10), "labelDisplayUnits": lit(1)}}],
            "valueAxis": [{"properties": {"show": lit(False), "gridlineShow": lit(False)}}],
            "categoryAxis": [{"properties": {"fontSize": lit(10), "showAxisTitle": lit(False),
                                             "maxMarginFactor": lit(45)}}],  # room for long industry names
        },
        "visualContainerObjects": {**title_obj(title)},
        "drillFilterOtherVisuals": True,
    }
    if colour_measure:
        vis["objects"]["dataPoint"] = colour_by_measure(colour_measure)
    else:
        vis["objects"]["dataPoint"] = [{"properties": {"fill": color("#EB6834")}}]
    if sort_desc:
        vis["query"]["sortDefinition"] = {"sort": [{"field": val, "direction": "Descending"}], "isDefaultSort": True}
    return container(name, x, y, w, h, vis)


def not_blank_filter(fname, entity, prop):
    return {"name": fname, "field": column(entity, prop), "type": "Categorical",
            "filter": {"Version": 2, "From": [{"Name": "d", "Entity": entity, "Type": 0}],
                       "Where": [{"Condition": {"Not": {"Expression": {"In": {
                           "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": prop}}],
                           "Values": [[{"Literal": {"Value": "null"}}]]}}}}}]},
            "howCreated": "User"}


def page(name, display, visuals):
    return {"name": name, "displayName": display, "visuals": visuals}


# ============================================================ report pages (1280 x 720)
W, H, M = 1280, 720, 16
footer = lambda n: text_card(f"{n}Footer", M, 692, 760, 24, "Data As Of", 8, fg="#8A8984")

p1 = [
    text_card("ovTitle", M, 8, 870, 46, "Title Overview", 18, bold=True),
    text_card("ovSubtitle", M, 54, 870, 30, "Subtitle Overview", 11, fg="#52514E"),
    slicer("ovSlicerIndustry", 900, 12, 180, 66, "dim_industry", "industry", "Industry"),
    slicer("ovSlicerSector", 1090, 12, 174, 66, "dim_industry", "sector_group", "Sector"),
    card("ovKpiJobs", M, 92, 240, 96, "Jobs Cut", "Jobs cut (announced, 2026)"),
    card("ovKpiEvents", 268, 92, 240, 96, "Layoff Events", "Layoff events"),
    card("ovKpiAiJobs", 520, 92, 240, 96, "AI Jobs Cut", "AI-driven jobs cut", accent=True),
    card("ovKpiAiShare", 772, 92, 240, 96, "AI Share of Jobs", "AI share of jobs cut", accent=True),
    card("ovKpiMult", 1024, 92, 240, 96, "AI Size Multiplier", "AI layoffs vs others (avg size)", accent=True),
    bar("ovReasonBar", M, 200, 470, 300, column("dim_category", "category_label"), measure("Jobs Cut"),
        "Jobs cut by stated reason", colour_measure="Bar Colour AI"),
    container("ovMonthly", 498, 200, 766, 300, {
        "visualType": "columnChart",
        "query": {"queryState": {
            "Category": {"projections": [proj(column("dim_date", "month_name"), active=True)]},
            "Y": {"projections": [proj(measure("AI Jobs Cut")), proj(measure("Non-AI Jobs Cut"))]}},
            "sortDefinition": {"sort": [{"field": column("dim_date", "month_name"), "direction": "Ascending"}],
                               "isDefaultSort": True}},
        "objects": {
            "dataPoint": [
                {"properties": {"fill": color("#EB6834")}, "selector": {"metadata": "_Measures.AI Jobs Cut"}},
                {"properties": {"fill": color("#C9C8C2")}, "selector": {"metadata": "_Measures.Non-AI Jobs Cut"}}],
            "legend": [{"properties": {"show": lit(True), "position": lit("Top")}}],
            "categoryAxis": [{"properties": {"showAxisTitle": lit(False)}}],
            "valueAxis": [{"properties": {"showAxisTitle": lit(False)}}],
        },
        "visualContainerObjects": {**title_obj("Monthly jobs cut: AI-driven vs other reasons (dated announcements)")},
        "drillFilterOtherVisuals": True,
    }, filters=[not_blank_filter("fMonthNotBlank", "dim_date", "month_name")]),
    card("ovEventsShare", M, 512, 300, 110, "AI Share of Events", "Share of layoff EVENTS citing AI", accent=True, size=28),
    card("ovJobsShare", 328, 512, 300, 110, "AI Share of Jobs", "Share of JOBS cut citing AI", accent=True, size=28),
    card("ovH1", 640, 512, 300, 110, "AI Share H1", "AI share of jobs cut, Jan-Jun", size=28),
    card("ovQ3", 952, 512, 312, 110, "AI Share Q3", "AI share of jobs cut, Jul-Sep", size=28),
    textbox("ovNote", M, 628, W - 2 * M, 60, [[
        ("Reading it: ", 10, True, "#0B0B0B"),
        ("few announcements, huge numbers. AI was cited in about 1 in 5 layoffs, but those took about 2 in 5 jobs. "
         "The AI share fell sharply after Q1's mega-announcements (Oracle 30K, HSBC 20K, Meta 16K).", 10, False, "#52514E")]]),
    footer("ov"),
]

p2 = [
    textbox("inTitle", M, 10, 900, 44, [[("Industries & companies: who blames AI?", 18, True, "#0B0B0B")]]),
    slicer("inSlicerSize", 940, 12, 324, 66, "dim_company", "company_size_band", "Company size"),
    bar("inAiShare", M, 70, 440, 330, column("dim_industry", "industry"), measure("AI Share of Jobs"),
        "AI share of each industry's job cuts", colour_measure="Bar Colour Industry AI Share"),
    container("inMatrix", 468, 70, 796, 330, {
        "visualType": "pivotTable",
        "query": {"queryState": {
            "Rows": {"projections": [proj(column("dim_industry", "industry"), active=True, display="Industry")]},
            "Columns": {"projections": [proj(column("dim_category", "category_label"), active=True, display="Stated reason")]},
            "Values": {"projections": [proj(measure("Jobs Cut"))]}}},
        "objects": {"values": [{"properties": {"backColor": {"solid": {"color": {"expr": {
            "FillRule": {"Input": measure("Jobs Cut"),
                         "FillRule": {"linearGradient2": {
                             "min": {"color": {"Literal": {"Value": "'#FFFFFF'"}}},
                             "max": {"color": {"Literal": {"Value": "'#EB6834'"}}},
                             "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'asZero'"}}}}}}}}}}},
            "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": "_Measures.Jobs Cut"}}]},
        "visualContainerObjects": {**title_obj("Jobs cut: industry x stated reason (heatmap)")},
        "drillFilterOtherVisuals": True,
    }),
    container("inDecomp", M, 412, 760, 272, {
        "visualType": "decompositionTreeVisual",
        "query": {"queryState": {
            "Analyze": {"projections": [proj(measure("Jobs Cut"))]},
            "ExplainBy": {"projections": [proj(column("dim_industry", "sector_group"), active=True),
                                          proj(column("dim_category", "category_label"), active=True),
                                          proj(column("dim_industry", "industry"), active=True),
                                          proj(column("dim_company", "company"), active=True)]}}},
        "visualContainerObjects": {**title_obj("Decomposition tree: click + to drill sector > reason > industry > company")},
        "drillFilterOtherVisuals": True,
    }),
    container("inTopCompanies", 788, 412, 476, 272, {
        "visualType": "tableEx",
        "query": {"queryState": {"Values": {"projections": [
            proj(column("dim_company", "company"), display="Company"), proj(measure("Jobs Cut")),
            proj(measure("AI Share of Jobs"), display="AI share"), proj(measure("Layoff Events"), display="Events")]}},
            "sortDefinition": {"sort": [{"field": measure("Jobs Cut"), "direction": "Descending"}], "isDefaultSort": True}},
        "visualContainerObjects": {**title_obj("Companies ranked by jobs cut")},
        "drillFilterOtherVisuals": True,
    }),
    footer("in"),
]

p3 = [
    textbox("rcTitle", M, 10, W - 2 * M, 80, [
        [("Reality check: US layoffs are flat, not spiking", 18, True, "#0B0B0B")],
        [("Official BLS data puts the 'AI layoff' headlines in context.", 11, False, "#52514E")]]),
    container("rcLine", M, 96, 860, 520, {
        "visualType": "lineChart",
        "query": {"queryState": {
            "Category": {"projections": [proj(column("macro_monthly", "month_start"), active=True)]},
            "Y": {"projections": [proj(measure("US Monthly Layoffs"))]}}},
        "objects": {
            "dataPoint": [{"properties": {"fill": color("#2A78D6")},
                           "selector": {"metadata": "_Measures.US Monthly Layoffs"}}],
            "legend": [{"properties": {"show": lit(False)}}],
            "valueAxis": [{"properties": {"start": lit(0), "end": lit(3500000), "showAxisTitle": lit(False)}}],
            "categoryAxis": [{"properties": {"showAxisTitle": lit(False)}}],
            "lineStyles": [{"properties": {"strokeWidth": lit(2)}}],
        },
        "visualContainerObjects": {**title_obj("US layoffs & discharges per month, 2019-2026 (BLS JOLTS, seasonally adjusted)")},
        "drillFilterOtherVisuals": True,
    }),
    card("rcUsMonth", 892, 96, 372, 120, "US Avg Monthly Layoffs 2026", "US layoffs in an average 2026 month",
         units=1000000, precision=2),
    card("rcAiJobs", 892, 228, 372, 120, "AI Jobs Cut", "All AI-driven cuts announced in 2026", accent=True),
    card("rcRatio", 892, 360, 372, 120, "AI Jobs vs One US Month", "...equal to this share of ONE US month", accent=True),
    textbox("rcNote", 892, 492, 372, 124, [
        [("Caveats", 10, True, "#0B0B0B")],
        [("COVID peak (13.0M, Mar 2020) is cut off at 3.5M so the recent trend is readable. "
          "The layoff dataset is global; BLS is US-only, so this compares scale, not like-for-like. "
          "'AI-Driven' is the reason companies gave, not proven causation.", 9, False, "#52514E")]]),
    footer("rc"),
]

PAGES = [page("overview", "Overview", p1), page("industries", "Industries & Companies", p2),
         page("realitycheck", "Reality Check", p3)]


# ============================================================ write everything
def build():
    for d in (SM, RP):
        if d.exists():
            shutil.rmtree(d)

    # semantic model
    write_json(SM / "definition.pbism", {"$schema": f"{SCHEMA}/item/semanticModel/definitionProperties/1.0.0/schema.json",
                                         "version": "4.2", "settings": {}})
    defn = SM / "definition"
    write(defn / "database.tmdl", "database\n\tcompatibilityLevel: 1600\n")
    write(defn / "model.tmdl", model_tmdl)
    write(defn / "expressions.tmdl", expressions_tmdl)
    write(defn / "relationships.tmdl", relationships_tmdl)
    write(defn / "tables" / "_Measures.tmdl", measures_tmdl())
    for t, cols in TABLES.items():
        write(defn / "tables" / f"{t}.tmdl", table_tmdl(t, cols))

    # report
    write_json(RP / "definition.pbir", {"$schema": f"{SCHEMA}/item/report/definitionProperties/2.0.0/schema.json",
                                        "version": "4.0",
                                        "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}})
    rdef = RP / "definition"
    write_json(rdef / "version.json", {"$schema": f"{SCHEMA}/item/report/definition/versionMetadata/1.0.0/schema.json",
                                       "version": "2.0.0"})
    theme_name = "AI_Layoffs_Theme.json"
    res = RP / "StaticResources" / "RegisteredResources"
    res.mkdir(parents=True, exist_ok=True)
    shutil.copy(PBI / theme_name, res / theme_name)
    write_json(rdef / "report.json", {
        "$schema": f"{SCHEMA}/item/report/definition/report/{V_REPORT}/schema.json",
        "themeCollection": {"customTheme": {
            "name": theme_name,
            "reportVersionAtImport": {"visual": V_VISUAL, "page": V_PAGE, "report": V_REPORT},
            "type": "RegisteredResources"}},
        "resourcePackages": [{"name": "RegisteredResources", "type": "RegisteredResources",
                              "items": [{"name": theme_name, "path": theme_name, "type": "CustomTheme"}]}],
        "settings": {"useStylableVisualContainerHeader": True, "defaultDrillFilterOtherVisuals": True},
    })
    write_json(rdef / "pages" / "pages.json", {
        "$schema": f"{SCHEMA}/item/report/definition/pagesMetadata/1.1.0/schema.json",
        "pageOrder": [p["name"] for p in PAGES], "activePageName": PAGES[0]["name"]})
    for p in PAGES:
        pdir = rdef / "pages" / p["name"]
        write_json(pdir / "page.json", {"$schema": f"{SCHEMA}/item/report/definition/page/{V_PAGE}/schema.json",
                                        "name": p["name"], "displayName": p["displayName"],
                                        "displayOption": "FitToPage", "height": H, "width": W})
        for v in p["visuals"]:
            write_json(pdir / "visuals" / v["name"] / "visual.json", v)

    # project file
    write_json(PBI / f"{NAME}.pbip", {"$schema": f"{SCHEMA}/pbip/pbipProperties/1.0.0/schema.json",
                                      "version": "1.0",
                                      "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
                                      "settings": {"enableAutoRecovery": True}})
    write(PBI / ".gitignore", "**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")
    n_vis = sum(len(p["visuals"]) for p in PAGES)
    print(f"Power BI project -> {PBI / (NAME + '.pbip')}")
    print(f"  {len(TABLES) + 1} tables, {len(RELATIONSHIPS)} relationships, {len(MEASURES)} measures, "
          f"{len(PAGES)} pages, {n_vis} visuals")


if __name__ == "__main__":
    build()

"""
Step 2 - CLEAN & TRANSFORM
Turns the raw layoffhedge + FRED files into:
  data/processed/layoffs_clean.csv        flat, analysis-ready table (Excel / quick EDA)
  data/processed/fact_layoff_events.csv   star schema fact (Power BI / SQL)
  data/processed/dim_company.csv
  data/processed/dim_industry.csv
  data/processed/dim_category.csv
  data/processed/dim_date.csv
  data/processed/macro_monthly.csv        BLS JOLTS + unemployment (2019-2026)
  data/processed/data_quality_log.csv     every issue found and how it was handled

Run:  python python/02_clean_transform.py
"""
from pathlib import Path
import re
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)
YEAR = 2026
AS_OF = pd.Timestamp("2026-10-06")  # layoffhedge "Generated" stamp

dq = []  # data-quality log rows


def log(check, rows, action):
    dq.append({"check": check, "rows_affected": int(rows), "action_taken": action})
    print(f"  [DQ] {check:55s} {rows:>4}  -> {action}")


# ---------------------------------------------------------------- load
# The CSV starts with 3 '# comment' lines (source / license / generated) before the header.
df = pd.read_csv(RAW / "layoffs-2026.csv", skiprows=3, encoding="utf-8")
log("Comment/metadata lines above header", 3, "Skipped on read")
df.columns = ["company", "industry", "people_cut", "workforce_pct_text",
              "total_workforce", "date_raw", "category", "source_url"]
n_raw = len(df)

# ---------------------------------------------------------------- text hygiene
for c in ["company", "industry", "category", "date_raw", "source_url"]:
    df[c] = df[c].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)

exact_dupes = df.duplicated().sum()
df = df.drop_duplicates()
log("Exact duplicate rows", exact_dupes, "Dropped")

same_day = df.duplicated(["company", "date_raw"], keep=False).sum()
log("Same company + same date (different sites/sources)", same_day,
    "Kept - separate events (e.g. Tyson Foods: two plants, two sources)")

# ---------------------------------------------------------------- dates
# Formats seen: 'Oct 6' (day), 'Mar 2026' (month), '2026' (year), '2025-26' / '2025-30' (multi-year plan)
def parse_date(s):
    if m := re.fullmatch(r"([A-Z][a-z]{2}) (\d{1,2})", s):
        return pd.to_datetime(f"{s} {YEAR}", format="%b %d %Y"), "Day"
    if m := re.fullmatch(r"([A-Z][a-z]{2}) (\d{4})", s):
        return pd.to_datetime(f"1 {s}", format="%d %b %Y"), "Month"
    if re.fullmatch(r"\d{4}", s):
        return pd.NaT, "Year"
    if re.fullmatch(r"\d{4}-\d{2}", s):
        return pd.NaT, "Multi-year plan"
    return pd.NaT, "Unparsed"


parsed = df["date_raw"].apply(parse_date)
df["event_date"] = [p[0] for p in parsed]
df["date_precision"] = [p[1] for p in parsed]
for prec, action in [
    ("Month", "Set to 1st of month; precision flag = 'Month'"),
    ("Year", "Date left blank; excluded from monthly trend, kept in totals"),
    ("Multi-year plan", "Date left blank; flagged as multi-year program (e.g. Bosch 2025-30)"),
    ("Unparsed", "Date left blank"),
]:
    n = (df["date_precision"] == prec).sum()
    if n:
        log(f"Date given at '{prec}' level instead of a day", n, action)

future = (df["event_date"] > AS_OF).sum()
log("Event date after dataset 'as of' date", future, "None found" if future == 0 else "Investigate")

df["month_start"] = df["event_date"].dt.to_period("M").dt.to_timestamp()
df["period_label"] = np.where(df["event_date"].notna(),
                              df["event_date"].dt.strftime("%b %Y"),
                              np.where(df["date_precision"] == "Year", "2026 (no month)",
                                       df["date_raw"] + " program"))

# ---------------------------------------------------------------- numbers
df["workforce_pct"] = df["workforce_pct_text"].str.rstrip("%").astype(float) / 100
log("Workforce % stored as text ('7.4%')", len(df), "Converted to decimal fraction (0.074)")

calc = df["people_cut"] / df["total_workforce"]
mismatch = ((calc - df["workforce_pct"]).abs() > 0.01).sum()
log("Workforce % != people_cut / total_workforce (>1pp)", mismatch,
    "None found - source % is consistent" if mismatch == 0 else "Recomputed from counts")

df["is_shutdown"] = (df["workforce_pct"] >= 0.999).astype(int)
log("100% of workforce cut (business closure)", df["is_shutdown"].sum(),
    "Kept; flagged is_shutdown = 1 so it can be filtered")

bad_num = ((df["people_cut"] <= 0) | (df["total_workforce"] <= 0)).sum()
log("Non-positive headcount values", bad_num, "None found" if bad_num == 0 else "Dropped")

# ---------------------------------------------------------------- enrichment
df["is_ai_driven"] = (df["category"] == "AI-DRIVEN").astype(int)
df["category_label"] = df["category"].str.title().str.replace("Ai-Driven", "AI-Driven")

df["company_size_band"] = pd.cut(
    df["total_workforce"], [0, 1_000, 10_000, 50_000, 100_000, np.inf], right=False,
    labels=["1 - <1K", "2 - 1K-10K", "3 - 10K-50K", "4 - 50K-100K", "5 - 100K+"]).astype(str)
df["severity_band"] = pd.cut(
    df["workforce_pct"], [0, 0.05, 0.10, 0.25, 0.999, np.inf], right=False,
    labels=["1 - <5%", "2 - 5-10%", "3 - 10-25%", "4 - 25-99%", "5 - Shutdown"]).astype(str)
df["layoff_size_band"] = pd.cut(
    df["people_cut"], [0, 100, 500, 1_000, 5_000, np.inf], right=False,
    labels=["1 - <100", "2 - 100-499", "3 - 500-999", "4 - 1K-4.9K", "5 - 5K+"]).astype(str)

df["source_domain"] = df["source_url"].str.extract(r"https?://(?:www\.)?([^/]+)")[0].str.lower()
df["source_type"] = np.select(
    [df["source_domain"].str.contains(r"\.gov|warn", regex=True, na=False),
     df["source_domain"].str.contains("sec.gov|investor|ir\\.", regex=True, na=False)],
    ["Government / WARN filing", "Company filing"], default="News media")
df.loc[df["source_domain"] == "sec.gov", "source_type"] = "Company filing (SEC)"

TECH_SECTORS = {"Tech", "Crypto & Fintech", "Telecom"}
df["sector_group"] = np.where(df["industry"].isin(TECH_SECTORS), "Tech & Digital", "Non-Tech")

# repeat layoffs: order each company's events (undated ones last)
df = df.sort_values(["company", "event_date"], na_position="last").reset_index(drop=True)
df["company_event_no"] = df.groupby("company").cumcount() + 1
df["company_event_count"] = df.groupby("company")["company"].transform("size")
df["is_repeat_layoffer"] = (df["company_event_count"] > 1).astype(int)
log("Companies with more than one layoff event", df.loc[df.is_repeat_layoffer == 1, "company"].nunique(),
    "Kept all events; added company_event_no / is_repeat_layoffer")

df["event_id"] = np.arange(1, len(df) + 1)

# ---------------------------------------------------------------- reconcile with the publisher's own aggregates
ind = pd.read_csv(RAW / "industries-2026.csv", comment="#")
ours = df.groupby("industry")["people_cut"].sum()
ind["ours"] = ind["Industry"].map(ours)
diff = (ind["ours"] != ind["Total Jobs Cut"]).sum()
log("Industry totals vs publisher's industries-2026.csv", diff,
    "All 13 industries reconcile exactly" if diff == 0 else "Differences - see console")
if diff:
    print(ind)

mon = pd.read_csv(RAW / "monthly-2026.csv", comment="#")
mon["month_start"] = pd.to_datetime(mon["Month"], format="%B %Y")
ours_m = df.groupby("month_start")["people_cut"].sum()
mon["ours"] = mon["month_start"].map(ours_m)
mdiff = (mon["ours"] != mon["Total Jobs Cut"]).sum()
log("Monthly totals vs publisher's monthly-2026.csv", mdiff,
    "All months reconcile exactly" if mdiff == 0 else "Differences - see console")
if mdiff:
    print(mon[["Month", "Total Jobs Cut", "ours"]])

# ---------------------------------------------------------------- outputs: flat table
flat_cols = ["event_id", "company", "industry", "sector_group", "category_label", "is_ai_driven",
             "people_cut", "total_workforce", "workforce_pct", "event_date", "month_start",
             "date_precision", "period_label", "date_raw", "company_size_band", "severity_band",
             "layoff_size_band", "is_shutdown", "company_event_no", "company_event_count",
             "is_repeat_layoffer", "source_type", "source_domain", "source_url"]
flat = df[flat_cols]
flat.to_csv(OUT / "layoffs_clean.csv", index=False, date_format="%Y-%m-%d")

# ---------------------------------------------------------------- outputs: star schema
dim_industry = (df[["industry", "sector_group"]].drop_duplicates().sort_values("industry")
                .reset_index(drop=True))
dim_industry.insert(0, "industry_id", dim_industry.index + 1)

cat_desc = {
    "AI-Driven": "Company explicitly cited AI / automation as a reason for the cuts",
    "Restructure": "Reorganisation, site closures, strategic refocus",
    "Cost Cut": "Cost reduction / margin programs",
    "Weak Demand": "Falling sales, tariffs, lost contracts",
    "Merger": "Post-merger or acquisition integration",
}
dim_category = pd.DataFrame({"category_label": list(cat_desc), "description": list(cat_desc.values())})
dim_category.insert(0, "category_id", dim_category.index + 1)
dim_category["sort_order"] = dim_category["category_id"]

comp = (df.groupby("company")
        .agg(industry=("industry", "first"), total_workforce=("total_workforce", "max"),
             events=("event_id", "count"), total_cut=("people_cut", "sum"))
        .reset_index())
comp["company_size_band"] = pd.cut(
    comp["total_workforce"], [0, 1_000, 10_000, 50_000, 100_000, np.inf], right=False,
    labels=["1 - <1K", "2 - 1K-10K", "3 - 10K-50K", "4 - 50K-100K", "5 - 100K+"]).astype(str)
comp["is_repeat_layoffer"] = (comp["events"] > 1).astype(int)
comp.insert(0, "company_id", comp.index + 1)
dim_company = comp[["company_id", "company", "industry", "total_workforce",
                    "company_size_band", "is_repeat_layoffer"]]

dates = pd.date_range("2026-01-01", "2026-12-31", freq="D")
dim_date = pd.DataFrame({"date": dates})
dim_date["date_key"] = dim_date["date"].dt.strftime("%Y%m%d").astype(int)
dim_date["year"] = dim_date["date"].dt.year
dim_date["quarter"] = "Q" + dim_date["date"].dt.quarter.astype(str)
dim_date["month_no"] = dim_date["date"].dt.month
dim_date["month_name"] = dim_date["date"].dt.strftime("%b")
dim_date["month_start"] = dim_date["date"].dt.to_period("M").dt.to_timestamp()
dim_date["week_of_year"] = dim_date["date"].dt.isocalendar().week.astype(int)
dim_date["day_name"] = dim_date["date"].dt.day_name()
dim_date["is_weekend"] = dim_date["date"].dt.dayofweek.ge(5).astype(int)
dim_date = dim_date[["date_key", "date", "year", "quarter", "month_no", "month_name",
                     "month_start", "week_of_year", "day_name", "is_weekend"]]

fact = (df.merge(dim_company[["company_id", "company"]], on="company")
          .merge(dim_industry[["industry_id", "industry"]], on="industry")
          .merge(dim_category[["category_id", "category_label"]], on="category_label"))
fact["date_key"] = fact["event_date"].dt.strftime("%Y%m%d").astype("Int64")
fact = fact[["event_id", "company_id", "industry_id", "category_id", "date_key", "date_precision",
             "period_label", "people_cut", "total_workforce", "workforce_pct", "is_ai_driven",
             "is_shutdown", "severity_band", "layoff_size_band", "company_event_no",
             "source_type", "source_url"]].sort_values("event_id")

# ---------------------------------------------------------------- macro context (BLS via FRED)
def fred(sid, name):
    s = pd.read_csv(RAW / f"{sid}.csv", parse_dates=["observation_date"])
    return s.rename(columns={"observation_date": "month_start", sid: name}).set_index("month_start")

macro = pd.concat([fred("JTSLDL", "us_layoffs_discharges_k"),
                   fred("JTU510099LDL", "info_sector_layoffs_k"),
                   fred("JTSJOL", "us_job_openings_k"),
                   fred("UNRATE", "unemployment_rate_pct")], axis=1, sort=True)
macro = macro.loc["2019-01-01":].reset_index()
macro["year"] = macro["month_start"].dt.year
macro["openings_per_layoff"] = (macro["us_job_openings_k"] / macro["us_layoffs_discharges_k"]).round(2)

# ---------------------------------------------------------------- write
for name, frame in {"fact_layoff_events": fact, "dim_company": dim_company,
                    "dim_industry": dim_industry, "dim_category": dim_category,
                    "dim_date": dim_date, "macro_monthly": macro}.items():
    frame.to_csv(OUT / f"{name}.csv", index=False, date_format="%Y-%m-%d")

log("Rows in -> rows out", n_raw, f"{len(flat)} clean events, {flat.company.nunique()} companies")
pd.DataFrame(dq).to_csv(OUT / "data_quality_log.csv", index=False)

print(f"\nClean events : {len(flat):,}")
print(f"Jobs cut     : {flat.people_cut.sum():,}")
print(f"AI-driven    : {flat.loc[flat.is_ai_driven == 1, 'people_cut'].sum():,} jobs "
      f"({flat.loc[flat.is_ai_driven == 1, 'people_cut'].sum() / flat.people_cut.sum():.1%})")
print("Outputs ->", OUT)

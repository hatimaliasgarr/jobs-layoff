"""
Step 3 - LOAD to SQL + run the analysis
  * builds database/layoffs_2026.db from sql/01_schema.sql
  * loads the processed star-schema CSVs
  * runs every query in sql/02_analysis_queries.sql and saves each result
    to data/processed/sql_results/Qxx_<name>.csv (used by the Excel workbook)

Run:  python python/03_load_sql.py
"""
from pathlib import Path
import re
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
DB = ROOT / "database" / "layoffs_2026.db"
RES = PROC / "sql_results"
DB.parent.mkdir(exist_ok=True)
RES.mkdir(exist_ok=True)

TABLES = ["dim_industry", "dim_category", "dim_company", "dim_date",
          "fact_layoff_events", "macro_monthly"]

con = sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys = ON")
con.executescript((ROOT / "sql" / "01_schema.sql").read_text(encoding="utf-8"))

for t in TABLES:
    df = pd.read_csv(PROC / f"{t}.csv")
    if t == "fact_layoff_events":
        df["date_key"] = df["date_key"].astype("Int64")
    df.to_sql(t, con, if_exists="append", index=False)  # append keeps the typed schema + constraints
    print(f"  loaded {t:20s} {len(df):>5} rows")
con.commit()

# integrity checks
orphans = con.execute("""
    SELECT COUNT(*) FROM fact_layoff_events f
    LEFT JOIN dim_company c USING (company_id)
    LEFT JOIN dim_date d USING (date_key)
    WHERE c.company_id IS NULL OR (f.date_key IS NOT NULL AND d.date_key IS NULL)""").fetchone()[0]
print(f"  orphan fact rows: {orphans}")
assert orphans == 0

# run analysis queries
sql = (ROOT / "sql" / "02_analysis_queries.sql").read_text(encoding="utf-8")
blocks = re.split(r"^-- (Q\d{2}): (.*)$", sql, flags=re.M)[1:]
for qid, title, body in zip(blocks[0::3], blocks[1::3], blocks[2::3]):
    query = body.strip().rstrip(";")
    out = pd.read_sql_query(query, con)
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:40]
    out.to_csv(RES / f"{qid}_{slug}.csv", index=False)
    print(f"\n{qid}: {title}\n{out.head(8).to_string(index=False)}")

con.close()
print("\nDatabase ->", DB)

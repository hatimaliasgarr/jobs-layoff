-- =====================================================================
-- AI Layoffs 2026 | Star schema
-- Engine: SQLite (database/layoffs_2026.db). Standard SQL - ports to
-- SQL Server / PostgreSQL / MySQL with only type-name changes.
-- =====================================================================

DROP TABLE IF EXISTS fact_layoff_events;
DROP TABLE IF EXISTS dim_company;
DROP TABLE IF EXISTS dim_industry;
DROP TABLE IF EXISTS dim_category;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS macro_monthly;

CREATE TABLE dim_industry (
    industry_id     INTEGER PRIMARY KEY,
    industry        TEXT    NOT NULL UNIQUE,
    sector_group    TEXT    NOT NULL            -- 'Tech & Digital' | 'Non-Tech'
);

CREATE TABLE dim_category (
    category_id     INTEGER PRIMARY KEY,
    category_label  TEXT    NOT NULL UNIQUE,    -- AI-Driven, Restructure, ...
    description     TEXT,
    sort_order      INTEGER
);

CREATE TABLE dim_company (
    company_id         INTEGER PRIMARY KEY,
    company            TEXT    NOT NULL UNIQUE,
    industry           TEXT,
    total_workforce    INTEGER,
    company_size_band  TEXT,
    is_repeat_layoffer INTEGER CHECK (is_repeat_layoffer IN (0,1))
);

CREATE TABLE dim_date (
    date_key      INTEGER PRIMARY KEY,           -- yyyymmdd
    date          TEXT    NOT NULL,
    year          INTEGER,
    quarter       TEXT,
    month_no      INTEGER,
    month_name    TEXT,
    month_start   TEXT,
    week_of_year  INTEGER,
    day_name      TEXT,
    is_weekend    INTEGER
);

CREATE TABLE fact_layoff_events (
    event_id          INTEGER PRIMARY KEY,
    company_id        INTEGER NOT NULL REFERENCES dim_company(company_id),
    industry_id       INTEGER NOT NULL REFERENCES dim_industry(industry_id),
    category_id       INTEGER NOT NULL REFERENCES dim_category(category_id),
    date_key          INTEGER          REFERENCES dim_date(date_key),  -- NULL = year-level / multi-year plan
    date_precision    TEXT,
    period_label      TEXT,
    people_cut        INTEGER NOT NULL CHECK (people_cut > 0),
    total_workforce   INTEGER NOT NULL CHECK (total_workforce > 0),
    workforce_pct     REAL    CHECK (workforce_pct BETWEEN 0 AND 1),
    is_ai_driven      INTEGER CHECK (is_ai_driven IN (0,1)),
    is_shutdown       INTEGER CHECK (is_shutdown IN (0,1)),
    severity_band     TEXT,
    layoff_size_band  TEXT,
    company_event_no  INTEGER,
    source_type       TEXT,
    source_url        TEXT
);

CREATE TABLE macro_monthly (
    month_start               TEXT PRIMARY KEY,
    us_layoffs_discharges_k   REAL,   -- BLS JOLTS JTSLDL (thousands, SA)
    info_sector_layoffs_k     REAL,   -- BLS JOLTS JTU510099LDL (thousands, NSA)
    us_job_openings_k         REAL,   -- BLS JOLTS JTSJOL (thousands, SA)
    unemployment_rate_pct     REAL,   -- BLS CPS UNRATE
    year                      INTEGER,
    openings_per_layoff       REAL
);

CREATE INDEX ix_fact_company  ON fact_layoff_events(company_id);
CREATE INDEX ix_fact_industry ON fact_layoff_events(industry_id);
CREATE INDEX ix_fact_category ON fact_layoff_events(category_id);
CREATE INDEX ix_fact_date     ON fact_layoff_events(date_key);

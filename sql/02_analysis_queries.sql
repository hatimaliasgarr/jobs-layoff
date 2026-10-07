-- =====================================================================
-- AI Layoffs 2026 | Business questions answered in SQL
-- Each query starts with a "-- Q<n>:" header; python/03_load_sql.py runs
-- them all and saves results to data/processed/sql_results/.
-- Techniques: CTEs, window functions (RANK, SUM OVER, LAG), CASE,
-- conditional aggregation, NULL handling, self-join-free share-of-total.
-- =====================================================================

-- Q01: Headline KPIs
SELECT
    COUNT(*)                                                         AS layoff_events,
    COUNT(DISTINCT company_id)                                       AS companies,
    SUM(people_cut)                                                  AS jobs_cut,
    SUM(CASE WHEN is_ai_driven = 1 THEN people_cut ELSE 0 END)       AS ai_jobs_cut,
    ROUND(100.0 * SUM(CASE WHEN is_ai_driven = 1 THEN people_cut END) / SUM(people_cut), 1) AS ai_share_of_jobs_pct,
    ROUND(100.0 * SUM(is_ai_driven) / COUNT(*), 1)                   AS ai_share_of_events_pct,
    ROUND(AVG(people_cut), 0)                                        AS avg_jobs_per_event,
    SUM(is_shutdown)                                                 AS full_shutdowns
FROM fact_layoff_events;

-- Q02: Why are companies cutting? Jobs, events and average layoff size by stated reason
SELECT
    c.category_label,
    COUNT(*)                                                   AS events,
    SUM(f.people_cut)                                          AS jobs_cut,
    ROUND(100.0 * SUM(f.people_cut) / SUM(SUM(f.people_cut)) OVER (), 1) AS share_of_jobs_pct,
    ROUND(AVG(f.people_cut), 0)                                AS avg_jobs_per_event,
    ROUND(100.0 * AVG(f.workforce_pct), 1)                     AS avg_workforce_pct
FROM fact_layoff_events f
JOIN dim_category c USING (category_id)
GROUP BY c.category_label
ORDER BY jobs_cut DESC;

-- Q03: AI-driven layoffs are bigger - median vs mean size, AI vs non-AI
WITH ranked AS (
    SELECT is_ai_driven, people_cut,
           ROW_NUMBER() OVER (PARTITION BY is_ai_driven ORDER BY people_cut) AS rn,
           COUNT(*)     OVER (PARTITION BY is_ai_driven)                     AS n
    FROM fact_layoff_events
)
SELECT CASE is_ai_driven WHEN 1 THEN 'AI-Driven' ELSE 'Other reasons' END AS reason,
       MAX(n)                                     AS events,
       ROUND(AVG(people_cut), 0)                  AS mean_jobs_cut,
       ROUND(AVG(CASE WHEN rn IN ((n + 1) / 2, (n + 2) / 2) THEN people_cut END), 0) AS median_jobs_cut,
       MAX(people_cut)                            AS largest_event
FROM ranked
GROUP BY is_ai_driven;

-- Q04: Which industries lean most on AI as the reason? (min 10 events)
SELECT
    i.industry,
    i.sector_group,
    COUNT(*)                                                              AS events,
    SUM(f.people_cut)                                                     AS jobs_cut,
    SUM(CASE WHEN f.is_ai_driven = 1 THEN f.people_cut ELSE 0 END)        AS ai_jobs_cut,
    ROUND(100.0 * SUM(CASE WHEN f.is_ai_driven = 1 THEN f.people_cut ELSE 0 END) / SUM(f.people_cut), 1) AS ai_share_pct
FROM fact_layoff_events f
JOIN dim_industry i USING (industry_id)
GROUP BY i.industry, i.sector_group
HAVING COUNT(*) >= 10
ORDER BY ai_share_pct DESC;

-- Q05: Monthly trend with running total and month-over-month change (dated events only)
WITH monthly AS (
    SELECT d.month_start,
           SUM(f.people_cut)                                                AS jobs_cut,
           SUM(CASE WHEN f.is_ai_driven = 1 THEN f.people_cut ELSE 0 END)   AS ai_jobs_cut,
           COUNT(*)                                                         AS events
    FROM fact_layoff_events f
    JOIN dim_date d USING (date_key)
    GROUP BY d.month_start
)
SELECT month_start,
       events,
       jobs_cut,
       ai_jobs_cut,
       SUM(jobs_cut) OVER (ORDER BY month_start)                         AS running_jobs_cut,
       jobs_cut - LAG(jobs_cut) OVER (ORDER BY month_start)              AS mom_change,
       ROUND(100.0 * ai_jobs_cut / jobs_cut, 1)                          AS ai_share_pct
FROM monthly
ORDER BY month_start;

-- Q06: Top 15 single layoff events of 2026
SELECT RANK() OVER (ORDER BY f.people_cut DESC) AS rnk,
       co.company, i.industry, c.category_label, f.period_label,
       f.people_cut, ROUND(100.0 * f.workforce_pct, 1) AS workforce_pct
FROM fact_layoff_events f
JOIN dim_company  co USING (company_id)
JOIN dim_industry i  USING (industry_id)
JOIN dim_category c  USING (category_id)
ORDER BY f.people_cut DESC
LIMIT 15;

-- Q07: Top AI-driven cutters and the share of their workforce affected
SELECT co.company, i.industry, SUM(f.people_cut) AS ai_jobs_cut,
       ROUND(100.0 * MAX(f.workforce_pct), 1)    AS max_workforce_pct,
       GROUP_CONCAT(f.period_label, ', ')        AS when_announced
FROM fact_layoff_events f
JOIN dim_company  co USING (company_id)
JOIN dim_industry i  USING (industry_id)
WHERE f.is_ai_driven = 1
GROUP BY co.company, i.industry
ORDER BY ai_jobs_cut DESC
LIMIT 15;

-- Q08: Repeat layoffers - companies that cut more than once in 2026
SELECT co.company, co.industry,
       COUNT(*)                     AS events,
       SUM(f.people_cut)            AS total_jobs_cut,
       SUM(f.is_ai_driven)          AS ai_driven_events
FROM fact_layoff_events f
JOIN dim_company co USING (company_id)
GROUP BY co.company, co.industry
HAVING COUNT(*) > 1
ORDER BY events DESC, total_jobs_cut DESC;

-- Q09: Big companies vs small - who cites AI?
SELECT co.company_size_band,
       COUNT(*)                                                         AS events,
       SUM(f.people_cut)                                                AS jobs_cut,
       ROUND(100.0 * SUM(f.is_ai_driven) / COUNT(*), 1)                 AS ai_events_pct,
       ROUND(100.0 * AVG(f.workforce_pct), 1)                           AS avg_workforce_pct
FROM fact_layoff_events f
JOIN dim_company co USING (company_id)
GROUP BY co.company_size_band
ORDER BY co.company_size_band;

-- Q10: Severity mix - how deep do cuts go?
SELECT severity_band, COUNT(*) AS events, SUM(people_cut) AS jobs_cut,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS share_of_events_pct
FROM fact_layoff_events
GROUP BY severity_band
ORDER BY severity_band;

-- Q11: Tech vs Non-Tech: reason mix (pivot with conditional aggregation)
SELECT i.sector_group,
       SUM(CASE WHEN c.category_label = 'AI-Driven'   THEN f.people_cut ELSE 0 END) AS ai_driven,
       SUM(CASE WHEN c.category_label = 'Restructure' THEN f.people_cut ELSE 0 END) AS restructure,
       SUM(CASE WHEN c.category_label = 'Cost Cut'    THEN f.people_cut ELSE 0 END) AS cost_cut,
       SUM(CASE WHEN c.category_label = 'Weak Demand' THEN f.people_cut ELSE 0 END) AS weak_demand,
       SUM(CASE WHEN c.category_label = 'Merger'      THEN f.people_cut ELSE 0 END) AS merger,
       SUM(f.people_cut)                                                            AS total
FROM fact_layoff_events f
JOIN dim_industry i USING (industry_id)
JOIN dim_category c USING (category_id)
GROUP BY i.sector_group;

-- Q12: Reality check - announced cuts vs the official US labour market (BLS JOLTS)
SELECT year,
       ROUND(AVG(us_layoffs_discharges_k), 0)  AS avg_monthly_us_layoffs_k,
       ROUND(AVG(info_sector_layoffs_k), 1)    AS avg_monthly_info_sector_layoffs_k,
       ROUND(AVG(us_job_openings_k), 0)        AS avg_monthly_job_openings_k,
       ROUND(AVG(unemployment_rate_pct), 2)    AS avg_unemployment_pct,
       ROUND(AVG(openings_per_layoff), 2)      AS openings_per_layoff
FROM macro_monthly
GROUP BY year
ORDER BY year;

-- Q13: Where does the information come from? Source credibility mix
SELECT source_type, COUNT(*) AS events, SUM(people_cut) AS jobs_cut
FROM fact_layoff_events
GROUP BY source_type
ORDER BY events DESC;

// =====================================================================
// Power Query (M) - load the star schema from data/processed/
// HOW TO USE
//   1. Home > Transform data > Manage Parameters > New parameter
//        Name: ProjectFolder   Type: Text
//        Current value: D:\Projects\anlytics-projects\p1\data\processed\
//      (keep the trailing backslash)
//   2. Home > New Source > Blank Query. Open Advanced Editor, paste ONE query
//      below, and rename the query to the name shown in its header.
//   3. Repeat for each query, then Close & Apply.
// Explicit types are set on every column so the model never relies on auto-detect.
// =====================================================================


// ---------------- Query name: fact_layoff_events
let
    Source   = Csv.Document(File.Contents(ProjectFolder & "fact_layoff_events.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"event_id", Int64.Type}, {"company_id", Int64.Type}, {"industry_id", Int64.Type},
        {"category_id", Int64.Type}, {"date_key", Int64.Type}, {"date_precision", type text},
        {"period_label", type text}, {"people_cut", Int64.Type}, {"total_workforce", Int64.Type},
        {"workforce_pct", Percentage.Type}, {"is_ai_driven", Int64.Type}, {"is_shutdown", Int64.Type},
        {"severity_band", type text}, {"layoff_size_band", type text}, {"company_event_no", Int64.Type},
        {"source_type", type text}, {"source_url", type text}}, "en-US")
in
    Typed


// ---------------- Query name: dim_company
let
    Source   = Csv.Document(File.Contents(ProjectFolder & "dim_company.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"company_id", Int64.Type}, {"company", type text}, {"industry", type text},
        {"total_workforce", Int64.Type}, {"company_size_band", type text}, {"is_repeat_layoffer", Int64.Type}}, "en-US")
in
    Typed


// ---------------- Query name: dim_industry
let
    Source   = Csv.Document(File.Contents(ProjectFolder & "dim_industry.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"industry_id", Int64.Type}, {"industry", type text}, {"sector_group", type text}}, "en-US")
in
    Typed


// ---------------- Query name: dim_category
let
    Source   = Csv.Document(File.Contents(ProjectFolder & "dim_category.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"category_id", Int64.Type}, {"category_label", type text}, {"description", type text}, {"sort_order", Int64.Type}}, "en-US")
in
    Typed


// ---------------- Query name: dim_date
let
    Source   = Csv.Document(File.Contents(ProjectFolder & "dim_date.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"date_key", Int64.Type}, {"date", type date}, {"year", Int64.Type}, {"quarter", type text},
        {"month_no", Int64.Type}, {"month_name", type text}, {"month_start", type date},
        {"week_of_year", Int64.Type}, {"day_name", type text}, {"is_weekend", Int64.Type}}, "en-US")
in
    Typed


// ---------------- Query name: macro_monthly
let
    Source   = Csv.Document(File.Contents(ProjectFolder & "macro_monthly.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"month_start", type date}, {"us_layoffs_discharges_k", type number}, {"info_sector_layoffs_k", type number},
        {"us_job_openings_k", type number}, {"unemployment_rate_pct", type number}, {"year", Int64.Type},
        {"openings_per_layoff", type number}}, "en-US")
in
    Typed

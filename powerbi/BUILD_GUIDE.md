# Power BI Build Guide: "Did AI Really Take the Jobs?"

> **Shortcut:** a finished version already exists. Double-click `AI_Layoffs_2026.pbip` in this folder.
> It opens with the model, 33 measures and 3 pages built. To get a single file, use File > Save as > Power BI file (*.pbix).
> If you moved the project folder: Transform data > Edit parameters > set `ProjectFolder` to your `data\processed\` path, then Refresh.
> Note: running `python python/06_build_pbip.py` again regenerates the project from scratch and **overwrites any edits you made in Power BI.**
>
> The rest of this guide shows how to build the report yourself. That's worth doing once so you can explain every step in an interview.

Time needed: about 2–3 hours. When you finish you'll have a 4-page report plus a tooltip page and a drill-through page.
All data is already clean. In Power BI the work is **modelling, DAX and design**.

Files in this folder:

| File | Use |
|---|---|
| `AI_Layoffs_Theme.json` | View > Themes > Browse for themes |
| `PowerQuery_Load.m` | Loads the 6 tables with explicit column types |
| `DAX_Measures.dax` | Every measure, with the expected value so you can check your work |

---

## Step 1: Load the data (10 min)

**Option A (fast):** Get Data > Text/CSV, then load these 6 files from `data/processed/`:
`fact_layoff_events`, `dim_company`, `dim_industry`, `dim_category`, `dim_date`, `macro_monthly`.
In Power Query, check each column type. `workforce_pct` should be Percentage, and the date columns should be Date.

**Option B (shows more skill, recommended):** build it with a `ProjectFolder` parameter and the M code in
`PowerQuery_Load.m`. If you share the .pbix, someone else can repoint the path in one place.

## Step 2: Model (15 min)

Model view. Build a **star schema** with single-direction, many-to-one relationships:

```
dim_company  (company_id)   1 ──< *  fact_layoff_events.company_id
dim_industry (industry_id)  1 ──< *  fact_layoff_events.industry_id
dim_category (category_id)  1 ──< *  fact_layoff_events.category_id
dim_date     (date_key)     1 ──< *  fact_layoff_events.date_key
macro_monthly                         (no relationship: separate BLS context table)
```

Then:
1. **Mark `dim_date` as a date table:** Table tools > Mark as date table > column `date`.
2. **Sort-by columns:**
   - `dim_date[month_name]` by `month_no`
   - `dim_category[category_label]` by `sort_order`
3. **Hide every ID/key column** in report view: `*_id`, `date_key`.
4. Set `fact_layoff_events[source_url]` to Data category = **Web URL**.
5. Create the `_Measures` table (Home > Enter data, then just Load). Add all the measures from `DAX_Measures.dax`
   and organise them into display folders: Core, AI, Time, Ranking, Macro, Formatting.

Check: a card showing `[Jobs Cut]` = **672,731** and `[AI Share of Jobs]` = **38.5%**.

## Step 3: Theme and canvas (5 min)

- View > Themes > Browse for themes, then pick `AI_Layoffs_Theme.json`.
- Canvas: 1280 × 720 (16:9).
- Design rule for every page: **orange means AI, grey means everything else.** Don't use any other colours except the blue BLS line on page 3.

---

## Page 1: "Overview" (the screenshot for LinkedIn)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ [Title Overview - dynamic]                              [Industry][Sector]   │
│ [Subtitle Overview]                                     [Size band] slicers  │
├──────────┬──────────┬──────────┬──────────┬──────────────────────────────────┤
│ Jobs Cut │ Layoff   │ AI Jobs  │ AI Share │ AI Size Multiplier               │
│ 672,731  │ Events   │ Cut      │ of Jobs  │ 2.9x                             │
├──────────┴──────────┴─────┬────┴──────────┴──────────────────────────────────┤
│ Jobs cut by stated reason │ Monthly jobs cut: AI-driven vs other             │
│ (bar, AI orange)          │ (stacked column, Jan–Oct)                        │
├───────────────────────────┼──────────────────────────────────────────────────┤
│ Share of events vs share  │ AI share H1 → Q3   (two cards with arrow text)   │
│ of jobs (100% stacked bar)│ + 3-line "what this means" text box              │
└───────────────────────────┴──────────────────────────────────────────────────┘
```

| Visual | Fields | Formatting |
|---|---|---|
| Title | Card (new) or text box bound to `[Title Overview]` | 20pt, Segoe UI Semibold |
| 5 KPI cards | `Jobs Cut`, `Layoff Events`, `AI Jobs Cut`, `AI Share of Jobs`, `AI Size Multiplier` | AI cards: callout colour #EB6834 |
| Reason bar | Y: `dim_category[category_label]`, X: `Jobs Cut` | Colors > fx > Field value > `Bar Colour AI`; data labels on; no gridlines |
| Monthly stacked column | X: `dim_date[month_start]` (type Categorical, format "mmm"), Y: `AI Jobs Cut`, `Non-AI Jobs Cut` | AI = orange, Non-AI = grey; tooltip: `Jobs Cut MoM %`, `AI Share of Jobs` |
| 100% stacked bar | Two rows: build with a small "Metric" table, or use 2 cards side by side: `AI Share of Events` (17.9%) vs `AI Share of Jobs` (38.5%) | Big numbers are the point |
| H1 vs Q3 | Cards: `AI Share H1` (49%), `AI Share Q3` (6%) | Caption: "AI share of jobs cut" |
| Slicers | `dim_industry[industry]` (dropdown), `dim_industry[sector_group]` (tiles), `dim_company[company_size_band]` (dropdown) | Put them in one row at the top right |

## Page 2: "Industries & Companies"

| Visual | Fields | Notes |
|---|---|---|
| Matrix (heatmap) | Rows `industry`, Columns `category_label`, Values `Jobs Cut` | Cell elements > Background colour > gradient #FCEDE6 → #EB6834 |
| Bar: AI share by industry | Y `industry`, X `AI Share of Jobs` | Colour fx `Bar Colour Industry AI Share`; filter: Layoff Events ≥ 10 |
| Scatter | X `Avg Workforce % Cut`, Y `Jobs Cut`, Details `dim_company[company]`, Legend `is_ai_driven` | Log scale on Y. Shows "big companies cut small %" |
| **Decomposition tree** | Analyse `Jobs Cut`; Explain by `sector_group` > `industry` > `category_label` > `company` | AI visual. Recruiters notice this one |
| Top-N table | `company`, `industry`, `Jobs Cut`, `Avg Workforce % Cut`, `Layoff Events` | Filter: Top 15 by Jobs Cut; data bars on Jobs Cut |

## Page 3: "Reality Check" (the twist)

| Visual | Fields | Notes |
|---|---|---|
| Line chart | X `macro_monthly[month_start]`, Y `US Monthly Layoffs` | Blue line. Y-axis max 3.5M so COVID (13M) runs off the chart; add a text-box note saying so |
| Card | `US Avg Monthly Layoffs 2026` | "US employers lay off ~1.7M people every month" |
| Card | `AI Jobs vs One US Month` | "All AI-driven cuts of 2026 = 15% of ONE month" |
| Small line | `info_sector_layoffs_k` | Information-sector layoffs: flat vs 2019 |
| Text box | Caveat: "Layoff dataset is global, BLS is US-only. Compared for scale, not like-for-like." | Being honest about limits is part of good analysis |

## Page 4: "Company Detail" (drill-through)

- Page type: Drill through. Drill-through field: `dim_company[company]`.
- Cards: Jobs Cut, Layoff Events, AI Share of Jobs, total_workforce.
- Table: `period_label`, `category_label`, `people_cut`, `workforce_pct`, `source_type`, `source_url` (shows as a link).
- To use it, right-click any company on page 2 > Drill through > Company Detail.

## Tooltip page

- New page > Page information > Allow use as tooltip. Canvas: Tooltip (320 × 240).
- Visuals: a small reason bar (`category_label` × `Jobs Cut`) plus the `AI Share of Jobs` card.
- Then on page 2's industry bar: Format > Tooltips > Type: Report page > pick this page.
  Hovering an industry then shows its reason mix.

## Final polish (this is what makes it stand out)

1. **Bookmark toggle "AI only / All reasons":** make two bookmarks (one with page filter `is_ai_driven = 1`) and add two buttons.
2. **Field parameter:** Modeling > New parameter > Fields with `Jobs Cut`, `Layoff Events`, `Avg Workforce % Cut`.
   Use it on the reason bar so viewers can switch the metric.
3. Put the `Data As Of` measure as a footer on every page.
4. Page navigation buttons (Insert > Buttons > Navigator > Page navigator).
5. Mobile layout for page 1 (View > Mobile layout).
6. Alt text on every visual (Format > General > Alt text). This is an accessibility signal.

## Publishing for LinkedIn

- **Screenshots:** export page 1 and page 3 at full size (File > Export > PDF, or Windows + Shift + S).
- **Screen recording (best reach):** record a 30–45 second walkthrough. Click a slicer, drill through to Meta, hover a tooltip.
  LinkedIn's native video gets far more reach than links.
- **Live link:** File > Publish > Power BI Service. Then **Publish to web** only if your tenant allows it.
  Publish to web makes the report public, which is fine here because all the data is public.
  Otherwise share screenshots and put the .pbix on GitHub.

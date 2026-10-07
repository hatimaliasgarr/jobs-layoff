# LinkedIn post kit

## What to upload
**Post type: Document (PDF carousel)** → `AI_Layoffs_2026_carousel.pdf` (8 slides, 4:5).
Carousels get swiped, which keeps people on your post longer, and that is what LinkedIn's feed ranks on.
Name the document: **"Did AI really take the jobs? (2026 data)"**

Second post 3–5 days later: a 30–45 s screen recording of the Power BI report, with a "here's how I built it" angle.

---

## Post copy (main version, ~1,250 characters)

AI was blamed for 38.5% of all job cuts announced in 2026.

But it was named in fewer than 1 in 5 layoffs.

I analysed 475 layoff announcements from this year (672,731 jobs, 421 companies) and compared them with official US labour data. Here's what I found:

→ AI is now the #1 reason companies give for layoffs, ahead of restructuring
→ AI layoffs are ~3x bigger than other layoffs (avg 3,045 vs 1,061 jobs)
→ Banks now blame AI almost as much as Big Tech (72% vs 73% of their cuts)
→ The "AI layoff" wave was front-loaded: 49% of cuts in H1, just 6% in Q3
→ And the twist: US employers lay off ~1.7M people EVERY MONTH. All AI-driven cuts of 2026 add up to ~15% of one month.

So did AI take the jobs?
The headline is real. The wave isn't (yet).

How I built it, end to end:
🐍 Python: cleaned messy dates ("Mar 10", "2026", "2025-30"), engineered features, reconciled to the source's own totals
🗄️ SQL: star schema + 13 analyses (CTEs, window functions)
📊 Excel: interactive SUMIFS dashboard + PivotTable with slicers
📈 Power BI: 30+ DAX measures, decomposition tree, drill-through

Full project + code: [GitHub link]

Which number surprised you most? 👇

#DataAnalytics #PowerBI #SQL #Python #Excel #AI #FutureOfWork #Layoffs #DataVisualization #PortfolioProject

---

## Alternative hooks (A/B test across posts)
1. "Everyone says AI is taking jobs. I checked 475 layoffs. It's more complicated."
2. "Oracle, Meta and HSBC cut 66,000 jobs and blamed AI. Then the AI layoffs almost stopped."
3. "AI was the #1 reason for layoffs in 2026. It's still a rounding error in the US labour market."

## Posting checklist
- [ ] Post Tue–Thu, 8–10 am in your audience's time zone
- [ ] Put the GitHub link in the **first comment**, not the post (external links in the body get less reach)
- [ ] Reply to every comment in the first 60–90 minutes
- [ ] Tag 0–3 people who'd genuinely care (a mentor, a data community). Don't mass-tag
- [ ] Add the project to your profile under **Featured** and **Projects**
- [ ] Pin the Power BI screenshot to the GitHub README top once it's built

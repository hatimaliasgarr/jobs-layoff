"""
Step 4 - EDA CHARTS + LINKEDIN CAROUSEL
Creates 4:5 portrait slides (1080x1350 px, LinkedIn's best-performing size) in images/
and stitches them into linkedin/AI_Layoffs_2026_carousel.pdf (upload as a LinkedIn "document").

Design: one accent colour (AI-Driven) against neutral grey - the reader's eye goes
straight to the AI story. Every chart has a takeaway headline, not a label.

Run:  python python/04_charts.py
"""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parents[1]
PROC, IMG, LI = ROOT / "data" / "processed", ROOT / "images", ROOT / "linkedin"
IMG.mkdir(exist_ok=True)
LI.mkdir(exist_ok=True)

# ------------------------------------------------------------ style tokens
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e6e5e0"
ACCENT = "#eb6834"      # AI-Driven
NEUTRAL = "#c9c8c2"     # everything else
BLUE = "#2a78d6"        # official statistics (BLS)
FONT = "Segoe UI"
AUTHOR = "Hatim  |  Excel - Python - SQL - Power BI"
SOURCE = "Data: layoffhedge.com 2026 Layoff Dataset (as of 6 Oct 2026); BLS JOLTS via FRED"

plt.rcParams.update({
    "font.family": FONT, "font.size": 13, "text.color": INK, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.edgecolor": GRID,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
})
k = FuncFormatter(lambda v, _: f"{v/1000:,.0f}K" if v >= 1000 else f"{v:,.0f}")

df = pd.read_csv(PROC / "layoffs_clean.csv", parse_dates=["event_date", "month_start"])
macro = pd.read_csv(PROC / "macro_monthly.csv", parse_dates=["month_start"])
TOTAL = df.people_cut.sum()
AI = df.loc[df.is_ai_driven == 1, "people_cut"].sum()
EVENTS, AI_EVENTS = len(df), int(df.is_ai_driven.sum())

slides = []


def slide(n, kicker, title, subtitle=None):
    """Portrait canvas with headline block; returns (fig, plotting axes rect)."""
    fig = plt.figure(figsize=(7.2, 9), dpi=150)
    fig.text(0.07, 0.945, kicker.upper(), fontsize=11, color=ACCENT, weight="bold")
    fig.text(0.07, 0.915, title, fontsize=21, weight="bold", va="top", linespacing=1.15)
    if subtitle:
        fig.text(0.07, 0.80, subtitle, fontsize=12.5, color=INK2, va="top", linespacing=1.4)
    fig.text(0.07, 0.035, SOURCE, fontsize=8, color=MUTED)
    fig.text(0.93, 0.035, f"{n}", fontsize=10, color=MUTED, ha="right")
    return fig


def clean_axes(ax, grid_axis="x"):
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.grid(axis=grid_axis, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def save(fig, name):
    fig.savefig(IMG / f"{name}.png")
    slides.append(fig)


# ------------------------------------------------------------ 1. cover
fig = plt.figure(figsize=(7.2, 9), dpi=150)
fig.text(0.07, 0.86, "DATA STORY  |  OCTOBER 2026", fontsize=12, color=ACCENT, weight="bold")
fig.text(0.07, 0.82, "Did AI really\ntake the jobs?", fontsize=44, weight="bold", va="top", linespacing=1.05)
fig.text(0.07, 0.60, f"I analysed {EVENTS} layoff announcements from 2026\n"
                     f"({TOTAL:,} jobs, {df.company.nunique()} companies, 13 industries)\n"
                     "and checked them against official US labour data.",
         fontsize=14, color=INK2, va="top", linespacing=1.5)
ax = fig.add_axes([0.07, 0.25, 0.86, 0.14])
ax.barh([0], [AI], color=ACCENT, height=0.6)
ax.barh([0], [TOTAL - AI], left=[AI], color=NEUTRAL, height=0.6)
ax.set_xlim(0, TOTAL)
ax.axis("off")
ax.text(AI / 2, 0, f"AI-Driven\n{AI/TOTAL:.1%}", ha="center", va="center", color="white", weight="bold", fontsize=14)
ax.text(AI + (TOTAL - AI) / 2, 0, "Every other reason", ha="center", va="center", color=INK, fontsize=13)
fig.text(0.07, 0.20, "Share of 2026's announced job cuts", fontsize=11, color=MUTED)
fig.text(0.07, 0.10, AUTHOR, fontsize=12, weight="bold")
fig.text(0.07, 0.075, "Swipe  >", fontsize=12, color=ACCENT, weight="bold")
fig.text(0.07, 0.035, SOURCE, fontsize=8, color=MUTED)
save(fig, "01_cover")

# ------------------------------------------------------------ 2. events vs jobs
fig = slide(2, "Insight 1", "AI was named in 1 in 5 layoffs -\nbut those took 2 in 5 jobs",
            f"AI-driven layoffs averaged {df[df.is_ai_driven==1].people_cut.mean():,.0f} jobs each,\n"
            f"vs {df[df.is_ai_driven==0].people_cut.mean():,.0f} for every other reason - about 3x bigger.")
ax = fig.add_axes([0.27, 0.30, 0.66, 0.38])
rows = [("Share of\nlayoff events", AI_EVENTS / EVENTS), ("Share of\njobs cut", AI / TOTAL)]
for i, (lab, v) in enumerate(rows):
    ax.barh(i, v, color=ACCENT, height=0.5)
    ax.barh(i, 1 - v, left=v, color=NEUTRAL, height=0.5)
    ax.text(v + 0.015, i, f"{v:.1%}", va="center", fontsize=22, weight="bold", color=INK)
    ax.text(-0.02, i, lab, va="center", ha="right", fontsize=13, color=INK2)
ax.set_xlim(0, 1)
ax.set_ylim(1.6, -0.6)
ax.axis("off")
fig.text(0.07, 0.25, "Orange = AI-Driven   Grey = Restructure, Cost Cut, Weak Demand, Merger",
         fontsize=10.5, color=INK2)
save(fig, "02_events_vs_jobs")

# ------------------------------------------------------------ 3. reasons
by_reason = df.groupby("category_label").people_cut.sum().sort_values()
fig = slide(3, "Insight 2", "AI is now the #1 stated\nreason for job cuts",
            "Jobs cut in 2026 by the reason companies gave.\nAI-Driven beat classic restructuring by 56K jobs.")
ax = fig.add_axes([0.25, 0.12, 0.68, 0.62])
colors = [ACCENT if c == "AI-Driven" else NEUTRAL for c in by_reason.index]
ax.barh(by_reason.index, by_reason.values, color=colors, height=0.62)
for y, v in enumerate(by_reason.values):
    ax.text(v + 4000, y, f"{v:,.0f}", va="center", fontsize=12, color=INK)
ax.xaxis.set_major_formatter(k)
ax.set_xlim(0, by_reason.max() * 1.22)
clean_axes(ax)
ax.tick_params(axis="y", labelsize=13, labelcolor=INK)
save(fig, "03_reasons")

# ------------------------------------------------------------ 4. monthly trend
m = (df.dropna(subset=["month_start"])
       .assign(ai=lambda d: d.people_cut.where(d.is_ai_driven == 1, 0))
       .groupby("month_start").agg(total=("people_cut", "sum"), ai=("ai", "sum")))
h1 = m.loc["2026-01":"2026-06"]
q3 = m.loc["2026-07":"2026-09"]
h1_share, q3_share = h1.ai.sum() / h1.total.sum(), q3.ai.sum() / q3.total.sum()
fig = slide(4, "Insight 3", "The 'AI layoff' wave was\nfront-loaded into H1",
            f"AI-Driven share of jobs cut: {h1_share:.0%} in Jan-Jun vs {q3_share:.0%} in Jul-Sep.\n"
            "Q3 cuts were mostly restructures, plant closures and WARN notices.")
ax = fig.add_axes([0.10, 0.13, 0.83, 0.58])
x = m.index.strftime("%b")
ax.bar(x, m.ai, color=ACCENT, width=0.66, label="AI-Driven")
ax.bar(x, m.total - m.ai, bottom=m.ai, color=NEUTRAL, width=0.66, label="Other reasons",
       edgecolor=SURFACE, linewidth=1.5)
ax.yaxis.set_major_formatter(k)
clean_axes(ax, "y")
ax.legend(frameon=False, loc="upper right", fontsize=11)
ax.annotate("Oracle 30K, HSBC 20K,\nMeta 16K - all citing AI", xy=(2, m.total.iloc[2]), xytext=(3.3, 135000),
            fontsize=10.5, color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED))
fig.text(0.07, 0.085, "Oct 2026 is partial (to 6 Oct). Excludes 6 year-level / multi-year announcements.",
         fontsize=9, color=MUTED)
save(fig, "04_monthly_trend")

# ------------------------------------------------------------ 5. industries
ind = df.groupby("industry").agg(events=("event_id", "count"), jobs=("people_cut", "sum"),
                                 ai=("people_cut", lambda s: s[df.loc[s.index, "is_ai_driven"] == 1].sum()))
ind = ind[ind.events >= 10]
ind["share"] = ind.ai / ind.jobs
ind = ind.sort_values("share")
fig = slide(5, "Insight 4", "Banks now blame AI almost\nas much as Big Tech does",
            "Share of each industry's jobs cut that was AI-Driven\n(industries with 10+ layoff events).")
ax = fig.add_axes([0.36, 0.10, 0.57, 0.64])
colors = [ACCENT if s >= 0.5 else NEUTRAL for s in ind.share]
ax.barh(ind.index, ind.share, color=colors, height=0.62)
for y, (s, j) in enumerate(zip(ind.share, ind.jobs)):
    ax.text(s + 0.015, y, f"{s:.0%}", va="center", fontsize=12, weight="bold" if s >= 0.5 else "normal")
ax.set_xlim(0, 1)
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0%}"))
clean_axes(ax)
ax.tick_params(axis="y", labelsize=12, labelcolor=INK)
save(fig, "05_industries")

# ------------------------------------------------------------ 6. top AI cutters
top = (df[df.is_ai_driven == 1].groupby("company").agg(jobs=("people_cut", "sum"), pct=("workforce_pct", "max"))
       .nlargest(10, "jobs").sort_values("jobs"))
fig = slide(6, "Insight 5", "The 10 biggest AI-driven\ncuts of 2026",
            "Jobs cut, and the share of each company's workforce.\nMeta cut 1 in 5 employees.")
ax = fig.add_axes([0.22, 0.10, 0.71, 0.64])
ax.barh(top.index, top.jobs, color=ACCENT, height=0.62)
for y, (j, p) in enumerate(zip(top.jobs, top.pct)):
    ax.text(j + 500, y, f"{j:,.0f}  ({p:.0%} of staff)", va="center", fontsize=11)
ax.set_xlim(0, top.jobs.max() * 1.45)
ax.xaxis.set_major_formatter(k)
clean_axes(ax)
ax.tick_params(axis="y", labelsize=12, labelcolor=INK)
save(fig, "06_top_ai_cutters")

# ------------------------------------------------------------ 7. reality check (BLS)
mm = macro.dropna(subset=["us_layoffs_discharges_k"])
us_2026 = mm.loc[mm.month_start.dt.year == 2026, "us_layoffs_discharges_k"]
avg_month_2026 = us_2026.mean() * 1000
fig = slide(7, "Reality check", "Zoom out: US layoffs are\nflat - not spiking",
            f"Official BLS data: US employers lay off ~{avg_month_2026/1e6:.1f}M people every month.\n"
            f"All AI-driven cuts announced worldwide in 2026 ({AI/1000:,.0f}K)\n"
            f"= about {AI/avg_month_2026:.0%} of ONE month of US layoffs.")
ax = fig.add_axes([0.10, 0.19, 0.83, 0.49])
ax.plot(mm.month_start, mm.us_layoffs_discharges_k * 1000, color=BLUE, lw=2)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v/1e6:.1f}M"))
ax.set_ylim(0, 3.5e6)
clean_axes(ax, "y")
peak = mm.loc[mm.us_layoffs_discharges_k.idxmax()]
ax.text(peak.month_start + pd.Timedelta(days=120), 3.3e6,
        f"COVID: {peak.us_layoffs_discharges_k/1000:.1f}M in {peak.month_start:%b %Y} (off scale)",
        fontsize=10.5, color=INK2, va="center")
ax.text(mm.month_start.iloc[-1], 2.25e6, f"Aug 2026: {us_2026.iloc[-1]/1000:.2f}M",
        ha="right", fontsize=11, color=INK, weight="bold")
fig.text(0.07, 0.10, "US layoffs & discharges, total nonfarm, monthly, seasonally adjusted (BLS JOLTS, JTSLDL).\n"
                     "Layoff dataset is global; BLS is US-only - compared for scale, not like-for-like.",
         fontsize=9, color=MUTED, linespacing=1.4)
ax.set_title("")
save(fig, "07_reality_check")

# ------------------------------------------------------------ 8. takeaways / CTA
fig = plt.figure(figsize=(7.2, 9), dpi=150)
fig.text(0.07, 0.90, "SO, DID AI TAKE THE JOBS?", fontsize=12, color=ACCENT, weight="bold")
fig.text(0.07, 0.86, "The headline is real.\nThe wave is not (yet).", fontsize=30, weight="bold", va="top",
         linespacing=1.1)
points = [
    f"AI was the #1 stated reason for job cuts in 2026 ({AI/TOTAL:.1%} of jobs).",
    "It's a big-company story: few announcements, huge numbers.",
    "Tech, fintech and banking say 'AI' most. Autos and retail don't.",
    f"The AI share fell from {h1_share:.0%} (H1) to {q3_share:.0%} (Q3).",
    "Official US layoff rates are flat vs 2024-25: 'AI' is a reason\ncompanies give, not yet a labour-market shock.",
]
y = 0.64
for i, p in enumerate(points, 1):
    fig.text(0.07, y, f"{i}", fontsize=18, weight="bold", color=ACCENT, va="top")
    fig.text(0.14, y - 0.003, p, fontsize=13, va="top", linespacing=1.35)
    y -= 0.085 if "\n" not in p else 0.11
fig.text(0.07, 0.15, "Built end-to-end: Python (clean) -> SQL (model + analysis)\n"
                     "-> Excel (pivot & QA) -> Power BI (dashboard)", fontsize=11.5, color=INK2, linespacing=1.4)
fig.text(0.07, 0.085, "What surprised you most? Comment below.", fontsize=13, weight="bold")
fig.text(0.07, 0.035, SOURCE, fontsize=8, color=MUTED)
save(fig, "08_takeaways")

with PdfPages(LI / "AI_Layoffs_2026_carousel.pdf") as pdf:
    for f in slides:
        pdf.savefig(f)
print(f"{len(slides)} slides -> {IMG} and {LI / 'AI_Layoffs_2026_carousel.pdf'}")
print(f"H1 AI share {h1_share:.1%} | Q3 AI share {q3_share:.1%} | AI vs 1 month US layoffs {AI/avg_month_2026:.1%}")

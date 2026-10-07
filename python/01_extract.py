"""
Step 1 - EXTRACT
Downloads the raw data used in this project into data/raw/.

Sources
  1. layoffhedge.com 2026 Layoff Dataset (free to use with attribution)
     https://layoffhedge.com/data/
  2. U.S. Bureau of Labor Statistics JOLTS + CPS, via FRED (public domain)
     JTSLDL        Layoffs & discharges, total nonfarm (thousands, SA)
     JTU510099LDL  Layoffs & discharges, Information sector (thousands, NSA)
     JTSJOL        Job openings, total nonfarm (thousands, SA)
     UNRATE        Unemployment rate (%)

Run:  python python/01_extract.py
"""
from pathlib import Path
import urllib.request

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

SOURCES = {
    "layoffs-2026.csv":    "https://layoffhedge.com/data/layoffs-2026.csv",
    "industries-2026.csv": "https://layoffhedge.com/data/industries-2026.csv",
    "monthly-2026.csv":    "https://layoffhedge.com/data/monthly-2026.csv",
}
for series in ["JTSLDL", "JTU510099LDL", "JTSJOL", "UNRATE"]:
    SOURCES[f"{series}.csv"] = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"


def download(name: str, url: str) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (portfolio project)"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        (RAW / name).write_bytes(data)
        print(f"  OK   {name:24s} {len(data):>9,} bytes")
    except Exception as e:  # keep the cached copy if the source is unreachable
        status = "cached copy kept" if (RAW / name).exists() else "MISSING"
        print(f"  FAIL {name:24s} {e} -> {status}")


if __name__ == "__main__":
    print("Downloading raw data ->", RAW)
    for name, url in SOURCES.items():
        download(name, url)

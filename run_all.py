"""
Run the whole pipeline end to end:
  extract -> clean/transform -> SQL load + analysis -> charts/carousel -> Excel (+ pivot & recalc in Excel)

  python run_all.py            # re-downloads the latest data first
  python run_all.py --offline  # uses the files already in data/raw
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
steps = ["01_extract.py", "02_clean_transform.py", "03_load_sql.py", "04_charts.py", "05_build_excel.py"]
if "--offline" in sys.argv:
    steps.remove("01_extract.py")

for s in steps:
    print(f"\n=== {s} ===")
    subprocess.run([sys.executable, str(ROOT / "python" / s)], check=True)

if sys.platform == "win32":
    print("\n=== Excel: pivot, slicers, recalc, error scan ===")
    subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File",
                    str(ROOT / "excel" / "add_pivot_and_recalc.ps1")], check=True)
else:
    print("\n(Skipping Excel pivot step: needs Windows + Microsoft Excel)")
print("\nDone.")

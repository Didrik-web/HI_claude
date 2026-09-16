from pathlib import Path
import shutil
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "submission"
if OUT.exists(): shutil.rmtree(OUT)
(OUT / "01_notebooks").mkdir(parents=True)
(OUT / "02_inputs").mkdir(parents=True)
(OUT / "03_outputs").mkdir(parents=True)
shutil.copytree(ROOT / "notebooks", OUT / "01_notebooks" / "notebooks")
shutil.copytree(ROOT / "src", OUT / "01_notebooks" / "src")
shutil.copytree(ROOT / "data", OUT / "02_inputs" / "data")
shutil.copytree(ROOT / "results", OUT / "03_outputs" / "results")
shutil.copy2(ROOT / "requirements.txt", OUT / "01_notebooks" / "requirements.txt")
print(f"Built submission folder at {OUT}")

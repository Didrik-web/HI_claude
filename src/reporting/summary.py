from pathlib import Path
import pandas as pd


def combine_summaries(files, outfile):
    frames = []
    for scenario, path in files.items():
        path = Path(path)
        if path.exists():
            df = pd.read_csv(path)
            if "scenario" not in df.columns:
                df.insert(0, "scenario", scenario)
            frames.append(df)
    if not frames:
        raise FileNotFoundError("No scenario summary files found")
    out = pd.concat(frames, ignore_index=True, sort=False)
    outfile = Path(outfile); outfile.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(outfile, index=False)
    return out

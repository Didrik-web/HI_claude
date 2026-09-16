from pathlib import Path
import sys, argparse
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from src import config

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set one common logistics-area connection bus")
    parser.add_argument("bus", type=int)
    args = parser.parse_args()
    df = pd.DataFrame({"depot": config.DEPOTS, "bus": [args.bus] * len(config.DEPOTS)})
    config.NETWORK_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.DEPOT_BUS_MAPPING, index=False)
    for stale in [config.NETWORK_LIMITS, config.LOSS_FACTORS, config.BUS_SCREENING]:
        if stale.exists(): stale.unlink()
    print(df.to_string(index=False))
    print("Rerun notebooks 02 -> 05.")

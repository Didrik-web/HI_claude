from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from src.preprocess.fleet import build_processed
from src.preprocess.prices import build_processed_prices

if __name__ == "__main__":
    build_processed()
    build_processed_prices()
    print("Processed fleet and market data regenerated.")

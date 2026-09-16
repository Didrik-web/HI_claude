from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from src import config

inputs = [config.RAW_FREIGHT, config.RAW_PRICES, config.FLEET_INTERFACE, config.BASE_LOAD_P, config.BASE_LOAD_Q, config.CHARGER_DESIGN, config.PRICE_DATA, config.DEPOT_BUS_MAPPING]
generated = [config.BUS_SCREENING, config.NETWORK_LIMITS, config.LOSS_FACTORS]
print("INPUTS")
for p in inputs: print(f"{'OK' if p.exists() else 'MISSING':8} {p.relative_to(config.ROOT)}")
print("\nGENERATED DURING NOTEBOOKS")
for p in generated: print(f"{'OK' if p.exists() else 'MISSING':8} {p.relative_to(config.ROOT)}")

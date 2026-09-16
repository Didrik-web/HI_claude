from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
RESULTS = ROOT / "results"

RAW_FREIGHT = RAW / "freight" / "Load_profiles_Freight_transports.xlsx"
RAW_PRICES = RAW / "market" / "entsoe_se1_january_2024.csv"

FLEET_DIR = PROCESSED / "fleet"
MARKET_DIR = PROCESSED / "market"
NETWORK_DIR = PROCESSED / "network"

FLEET_INTERFACE = FLEET_DIR / "fleet_interface.csv"
FLEET_ASSUMPTIONS = FLEET_DIR / "fleet_assumptions.csv"
CHARGER_DESIGN = FLEET_DIR / "charger_design.csv"
BASE_LOAD_P = FLEET_DIR / "depot_base_load_MW.csv"
BASE_LOAD_Q = FLEET_DIR / "depot_base_load_Mvar.csv"
PRICE_DATA = MARKET_DIR / "se1_day_ahead_2024.csv"

DEPOT_BUS_MAPPING = NETWORK_DIR / "depot_bus_mapping.csv"
BUS_SCREENING = NETWORK_DIR / "connection_point_screening.csv"
NETWORK_LIMITS = NETWORK_DIR / "network_limits.csv"          # generated in Step 3
LOSS_FACTORS = NETWORK_DIR / "marginal_loss_factors.csv"     # generated in Step 5

DEPOTS = ["ICA", "Mathem", "Postnord", "Airmee"]
DT_H = 1.0

V_MIN = 0.90
V_MAX = 1.10
V_MIN_STRICT = 0.95
V_MAX_STRICT = 1.05
LINE_LOADING_MAX = 100.0
TRAFO_LOADING_MAX = 100.0
EV_POWER_FACTOR = 1.0

HEADROOM_TOL_MW = 0.005
HEADROOM_GROWTH_FACTOR = 2.0
HEADROOM_HARD_LIMIT_MW = 100.0

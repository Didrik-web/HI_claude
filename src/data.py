from pathlib import Path
import pandas as pd
from . import config


def _read_csv(path: Path, required=None, parse_time=True):
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    df = pd.read_csv(path)
    if required:
        missing = set(required) - set(df.columns)
        if missing:
            raise ValueError(f"{path.name} missing columns: {sorted(missing)}")
    if parse_time and "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], errors="raise", utc=True)
    return df


def load_fleet():
    df = _read_csv(config.FLEET_INTERFACE, [
        "time", "depot", "availability", "dt_h", "day",
        "energy_required_MWh", "charger_power_MW",
        "charging_efficiency", "base_load_MW",
    ])
    df["day"] = pd.to_datetime(df["day"], errors="raise", utc=True)
    return df.sort_values(["time", "depot"]).reset_index(drop=True)


def load_fleet_assumptions():
    return _read_csv(config.FLEET_ASSUMPTIONS, parse_time=False)


def load_charger_design():
    return _read_csv(config.CHARGER_DESIGN, parse_time=False)


def load_base_loads():
    p = _read_csv(config.BASE_LOAD_P, ["time", *config.DEPOTS]).set_index("time").sort_index()
    q = _read_csv(config.BASE_LOAD_Q, ["time", *config.DEPOTS]).set_index("time").sort_index()
    if not p.index.equals(q.index):
        raise ValueError("Active and reactive base-load timestamps differ")
    return p, q


def load_prices():
    return _read_csv(config.PRICE_DATA, ["time", "price_EUR_MWh"]).sort_values("time")


def load_bus_mapping(require_shared=True):
    df = _read_csv(config.DEPOT_BUS_MAPPING, ["depot", "bus"], parse_time=False)
    if df["depot"].duplicated().any():
        raise ValueError("Each depot must appear exactly once in depot_bus_mapping.csv")
    missing = set(config.DEPOTS) - set(df["depot"])
    extra = set(df["depot"]) - set(config.DEPOTS)
    if missing or extra:
        raise ValueError(f"Mapping mismatch. Missing={sorted(missing)}, extra={sorted(extra)}")
    mapping = dict(zip(df["depot"], df["bus"].astype(int)))
    if require_shared and len(set(mapping.values())) != 1:
        raise ValueError(
            "Final project model assumes one shared logistics-area connection bus. "
            f"Found buses: {sorted(set(mapping.values()))}"
        )
    return mapping


def shared_bus(bus_map):
    buses = set(bus_map.values())
    if len(buses) != 1:
        raise ValueError(f"Expected one shared connection bus, found {sorted(buses)}")
    return int(next(iter(buses)))


def installed_charger_power(fleet=None):
    if fleet is None:
        fleet = load_fleet()
    return (
        fleet.groupby("depot")["charger_power_MW"]
        .first().reindex(config.DEPOTS).astype(float).to_dict()
    )


def load_network_limits():
    df = _read_csv(config.NETWORK_LIMITS, [
        "time", "depot", "bus", "charger_power_MW",
        "safe_charging_limit_MW", "all_installed_feasible",
    ])
    if df.duplicated(["time", "depot"]).any():
        raise ValueError("network_limits.csv contains duplicate (time, depot) rows")
    if (~df["all_installed_feasible"].astype(bool)).any():
        bad = df.loc[~df["all_installed_feasible"].astype(bool), "time"].nunique()
        raise ValueError(
            f"Step 3 found {bad} hours where full installed charging is not network-feasible. "
            "Resolve the charger design/connection point before running optimization."
        )
    return df.sort_values(["time", "depot"]).reset_index(drop=True)


def load_loss_factors():
    return _read_csv(config.LOSS_FACTORS, ["time", "depot", "loss_coefficient"]).sort_values(["time", "depot"])

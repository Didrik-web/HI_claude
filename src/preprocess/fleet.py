import numpy as np
import pandas as pd
from .. import config

# COURSE-SUPPLIED DATA:
#   four 336 h depot base-load profiles and operating-pattern descriptions.
# ENGINEERING ASSUMPTIONS BELOW:
#   fleet size/mix, daily vehicle energy, charger catalogue, pf and efficiency.
POWER_FACTOR = 0.95
CHARGING_EFFICIENCY = 0.92

VEHICLE_CLASSES = {
    "N1_van": {"daily_kWh": 36.0},
    "N2_truck": {"daily_kWh": 105.0},
    "N3_reefer": {"daily_kWh": 220.0},
}

FLEET = {
    "ICA": {"N3_reefer": 12, "N2_truck": 8},
    "Mathem": {"N2_truck": 6, "N1_van": 14},
    "Postnord": {"N2_truck": 4, "N1_van": 30},
    "Airmee": {"N1_van": 12},
}

# Project slide operating schedules [start, end). Vehicles are assumed available
# for charging outside operating hours.
OPERATING_WINDOWS = {
    "weekday": {
        "ICA": (5, 23), "Mathem": (7, 22),
        "Postnord": (4, 22), "Airmee": (8, 20),
    },
    "weekend": {
        "ICA": (7, 18), "Mathem": (8, 18),
        "Postnord": (4, 22), "Airmee": (9, 17),
    },
}

CHARGERS_KW = [11, 22, 50, 150]


def load_raw_freight(path=config.RAW_FREIGHT):
    xls = pd.ExcelFile(path)
    sheet = "Load_profiles_Freight transport"
    if sheet not in xls.sheet_names:
        sheet = xls.sheet_names[0]
    df = pd.read_excel(path, sheet_name=sheet)
    required = {"Date", "Time", *config.DEPOTS}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Raw freight file missing columns: {sorted(missing)}")

    dates = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    times = df["Time"].astype(str).str.extract(r"(\d{2}:\d{2}:\d{2})", expand=False)
    timestamps = pd.to_datetime(dates + " " + times).dt.tz_localize("Europe/Stockholm")

    out = df[config.DEPOTS].copy()
    out.insert(0, "time", timestamps)
    if len(out) != 336 or out[config.DEPOTS].isna().any().any():
        raise ValueError("Expected 336 complete hourly freight rows")
    return out


def _availability(timestamp, depot):
    daytype = "weekend" if timestamp.weekday() >= 5 else "weekday"
    start, end = OPERATING_WINDOWS[daytype][depot]
    return 0.0 if start <= timestamp.hour < end else 1.0


def _daily_energy_mwh(depot):
    return sum(
        n * VEHICLE_CLASSES[vehicle_class]["daily_kWh"]
        for vehicle_class, n in FLEET[depot].items()
    ) / 1000.0


def build_assumption_table():
    rows = []
    for depot, classes in FLEET.items():
        for cls, n in classes.items():
            wd = OPERATING_WINDOWS["weekday"][depot]
            we = OPERATING_WINDOWS["weekend"][depot]
            rows.append({
                "depot": depot,
                "vehicle_class": cls,
                "number_of_vehicles": n,
                "daily_kWh_per_vehicle": VEHICLE_CLASSES[cls]["daily_kWh"],
                "weekday_operating_start": wd[0],
                "weekday_operating_end": wd[1],
                "weekend_operating_start": we[0],
                "weekend_operating_end": we[1],
                "charging_efficiency": CHARGING_EFFICIENCY,
                "base_load_power_factor": POWER_FACTOR,
            })
    return pd.DataFrame(rows)


def build_charger_design():
    rows = []
    for depot, classes in FLEET.items():
        available_windows = []
        for daytype in ("weekday", "weekend"):
            start, end = OPERATING_WINDOWS[daytype][depot]
            available_windows.append(24 - (end - start))
        shortest_window_h = min(available_windows)

        for cls, n in classes.items():
            daily_kwh = VEHICLE_CLASSES[cls]["daily_kWh"]
            required_kw = daily_kwh / (shortest_window_h * CHARGING_EFFICIENCY)
            rating_kw = next(r for r in CHARGERS_KW if r >= required_kw)
            rows.append({
                "depot": depot,
                "vehicle_class": cls,
                "number_of_vehicles": n,
                "daily_kWh_per_vehicle": daily_kwh,
                "shortest_charging_window_h": shortest_window_h,
                "minimum_required_kW_per_vehicle": round(required_kw, 2),
                "charger_type": "AC" if rating_kw <= 22 else "DC",
                "charger_kW_per_vehicle": rating_kw,
                "installed_kW": n * rating_kw,
            })
    return pd.DataFrame(rows)


def build_processed():
    raw = load_raw_freight()

    # Course file values are treated as kW and converted to MW.
    p = raw.set_index("time")[config.DEPOTS] / 1000.0
    tan_phi = np.sqrt(1 - POWER_FACTOR**2) / POWER_FACTOR
    q = p * tan_phi

    assumptions = build_assumption_table()
    design = build_charger_design()
    installed_mw = design.groupby("depot")["installed_kW"].sum() / 1000.0

    rows = []
    for row in raw.itertuples(index=False):
        for depot in config.DEPOTS:
            rows.append({
                "time": row.time,
                "depot": depot,
                "availability": _availability(row.time, depot),
                "dt_h": 1.0,
                "day": row.time.normalize(),
                "energy_required_MWh": _daily_energy_mwh(depot),
                "charger_power_MW": float(installed_mw.loc[depot]),
                "charging_efficiency": CHARGING_EFFICIENCY,
                "base_load_MW": float(getattr(row, depot)) / 1000.0,
            })
    fleet = pd.DataFrame(rows)

    config.FLEET_DIR.mkdir(parents=True, exist_ok=True)
    p.reset_index().to_csv(config.BASE_LOAD_P, index=False)
    q.reset_index().to_csv(config.BASE_LOAD_Q, index=False)
    assumptions.to_csv(config.FLEET_ASSUMPTIONS, index=False)
    design.to_csv(config.CHARGER_DESIGN, index=False)
    fleet.to_csv(config.FLEET_INTERFACE, index=False)
    return fleet, p, q, assumptions, design


if __name__ == "__main__":
    fleet, p, q, assumptions, design = build_processed()
    print(f"Wrote {len(fleet)} fleet rows and {len(p)} hourly rows to {config.FLEET_DIR}")

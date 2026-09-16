import pandas as pd


def build_uncontrolled_schedule(fleet):
    """Charge immediately at installed power whenever vehicles are available."""
    fleet = fleet.sort_values(["depot", "day", "time"]).copy()
    rows = []
    for (depot, day), group in fleet.groupby(["depot", "day"], sort=False):
        required = float(group.energy_required_MWh.iloc[0])
        remaining = required
        for r in group.itertuples():
            p = 0.0
            if float(r.availability) > 0 and remaining > 1e-12:
                deliverable = float(r.charger_power_MW) * float(r.dt_h) * float(r.charging_efficiency)
                delivered = min(remaining, deliverable)
                p = delivered / (float(r.dt_h) * float(r.charging_efficiency))
                remaining -= delivered
            rows.append({
                "time": r.time, "depot": depot, "day": day,
                "availability": r.availability, "dt_h": r.dt_h,
                "charging_efficiency": r.charging_efficiency,
                "energy_required_MWh": required,
                "charger_power_MW": r.charger_power_MW,
                "charging_MW": p,
            })
        if remaining > 1e-8:
            raise ValueError(f"Uncontrolled schedule infeasible for {depot} {day}: {remaining:.3f} MWh unmet")
    return pd.DataFrame(rows).sort_values(["time", "depot"]).reset_index(drop=True)


def charging_summary(schedule):
    s = schedule.copy()
    s["grid_energy_MWh"] = s.charging_MW * s.dt_h
    s["delivered_energy_MWh"] = s.grid_energy_MWh * s.charging_efficiency
    return s.groupby("depot", as_index=False).agg(
        grid_energy_MWh=("grid_energy_MWh", "sum"),
        delivered_energy_MWh=("delivered_energy_MWh", "sum"),
        peak_charging_MW=("charging_MW", "max"),
        charging_hours=("charging_MW", lambda x: int((x > 1e-9).sum())),
    )

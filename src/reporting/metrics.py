import pandas as pd
from .. import config


def schedule_cost(schedule, prices):
    s = schedule.copy(); s["time"] = pd.to_datetime(s.time, utc=True)
    p = prices.copy(); p["time"] = pd.to_datetime(p.time, utc=True)
    price = dict(zip(p.time, p.price_EUR_MWh.astype(float)))
    return float(sum(float(r.charging_MW) * float(getattr(r, "dt_h", 1.0)) * price[r.time] for r in s.itertuples()))


def scenario_metrics(name, schedule, prices, network_results, n1_summary=None):
    s = schedule.copy(); s["time"] = pd.to_datetime(s.time, utc=True)
    total_ev = s.groupby("time").charging_MW.sum()
    active_times = total_ev[total_ev > 1e-9].index
    nr = network_results.copy(); nr["time"] = pd.to_datetime(nr.time, utc=True)
    active_nr = nr[nr.time.isin(active_times)]

    out = {
        "scenario": name,
        "electricity_cost_EUR": schedule_cost(s, prices),
        "grid_energy_MWh": float((s.charging_MW * (s.dt_h if "dt_h" in s.columns else 1.0)).sum()),
        "peak_ev_charging_MW": float(total_ev.max()),
        "peak_total_depot_load_MW": float(nr.total_depot_load_MW.max()),
        "min_voltage_pu": float(nr.min_voltage_pu.min()),
        "max_line_loading_percent": float(nr.max_line_loading_percent.max()),
        "max_trafo_loading_percent": float(nr.max_trafo_loading_percent.max()),
        "network_losses_MWh": float(nr.total_losses_MW.sum() * config.DT_H),
        "failed_powerflows": int((~nr.converged).sum()),
    }
    if len(active_nr):
        out.update({
            "min_voltage_during_EV_charging_pu": float(active_nr.min_voltage_pu.min()),
            "max_line_loading_during_EV_charging_percent": float(active_nr.max_line_loading_percent.max()),
            "max_trafo_loading_during_EV_charging_percent": float(active_nr.max_trafo_loading_percent.max()),
        })
    if n1_summary is not None and len(n1_summary):
        out["n1_total_cases"] = len(n1_summary)
        out["n1_electrical_limits_ok_cases"] = int(n1_summary.electrical_limits_ok.sum())
        out["n1_electrical_limit_violation_cases"] = int((~n1_summary.electrical_limits_ok).sum())
        out["n1_full_supply_ok_cases"] = int(n1_summary.full_supply_ok.sum())
        out["n1_islanding_cases"] = int((pd.to_numeric(n1_summary.buses_isolated, errors="coerce").fillna(0) > 0).sum())
    return pd.DataFrame([out])

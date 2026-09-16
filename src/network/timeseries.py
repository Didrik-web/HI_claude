import numpy as np
import pandas as pd
import pandapower as pp
from .. import config
from .model import add_depot_loads, set_depot_snapshot


def schedule_to_wide(schedule):
    s = schedule.copy()
    s["time"] = pd.to_datetime(s["time"], errors="raise", utc=True)
    wide = s.pivot(index="time", columns="depot", values="charging_MW").reindex(columns=config.DEPOTS).sort_index()
    if wide.isna().any().any():
        raise ValueError("Charging schedule is incomplete")
    return wide


def zero_schedule(times):
    return pd.DataFrame([
        {"time": t, "depot": d, "charging_MW": 0.0}
        for t in times for d in config.DEPOTS
    ])


def constraint_status(net, v_min=config.V_MIN, v_max=config.V_MAX,
                      line_max=config.LINE_LOADING_MAX, trafo_max=config.TRAFO_LOADING_MAX):
    try:
        pp.runpp(net)
    except pp.LoadflowNotConverged:
        return {"feasible": False, "converged": False,
                "min_voltage_pu": np.nan, "max_voltage_pu": np.nan,
                "max_line_loading_percent": np.nan, "max_trafo_loading_percent": np.nan,
                "binding_reason": "power_flow_not_converged"}
    vm = net.res_bus.vm_pu.dropna()
    min_v = float(vm.min()) if len(vm) else np.nan
    max_v = float(vm.max()) if len(vm) else np.nan
    max_line = float(net.res_line.loading_percent.max()) if len(net.res_line) else 0.0
    max_trafo = float(net.res_trafo.loading_percent.max()) if len(net.res_trafo) else 0.0
    reasons = []
    if np.isnan(min_v) or min_v < v_min: reasons.append("low_voltage")
    if np.isnan(max_v) or max_v > v_max: reasons.append("high_voltage")
    if max_line > line_max: reasons.append("line_loading")
    if max_trafo > trafo_max: reasons.append("trafo_loading")
    return {"feasible": not reasons, "converged": True,
            "min_voltage_pu": min_v, "max_voltage_pu": max_v,
            "max_line_loading_percent": max_line,
            "max_trafo_loading_percent": max_trafo,
            "binding_reason": "+".join(reasons) if reasons else "none"}


def _simulate(network_factory, base_p, base_q, schedule, bus_map, collect_line_losses=False):
    charging = schedule_to_wide(schedule)
    if not base_p.index.equals(base_q.index) or not base_p.index.equals(charging.index):
        raise ValueError("Base-load and charging timestamps must match exactly")
    net = network_factory()
    idx = add_depot_loads(net, bus_map)
    rows, line_rows = [], []

    for t in base_p.index:
        set_depot_snapshot(net, idx, base_p.loc[t].to_dict(), base_q.loc[t].to_dict(), charging.loc[t].to_dict(), config.EV_POWER_FACTOR)
        try:
            pp.runpp(net)
            converged = True
        except pp.LoadflowNotConverged:
            converged = False

        if converged:
            line_loss = float(net.res_line.pl_mw.sum()) if len(net.res_line) else 0.0
            trafo_loss = float(net.res_trafo.pl_mw.sum()) if len(net.res_trafo) else 0.0
            rows.append({
                "time": t, "converged": True,
                "min_voltage_pu": float(net.res_bus.vm_pu.min()),
                "max_voltage_pu": float(net.res_bus.vm_pu.max()),
                "max_line_loading_percent": float(net.res_line.loading_percent.max()),
                "max_trafo_loading_percent": float(net.res_trafo.loading_percent.max()) if len(net.res_trafo) else 0.0,
                "line_losses_MW": line_loss, "trafo_losses_MW": trafo_loss,
                "total_losses_MW": line_loss + trafo_loss,
                "total_base_load_MW": float(base_p.loc[t].sum()),
                "total_ev_charging_MW": float(charging.loc[t].sum()),
                "total_depot_load_MW": float(base_p.loc[t].sum() + charging.loc[t].sum()),
            })
            if collect_line_losses:
                for line_idx, r in net.res_line.iterrows():
                    line_rows.append({
                        "time": t, "line": net.line.loc[line_idx, "name"],
                        "loss_MW": float(r.pl_mw), "loading_percent": float(r.loading_percent),
                    })
        else:
            rows.append({
                "time": t, "converged": False,
                "min_voltage_pu": np.nan, "max_voltage_pu": np.nan,
                "max_line_loading_percent": np.nan, "max_trafo_loading_percent": np.nan,
                "line_losses_MW": np.nan, "trafo_losses_MW": np.nan,
                "total_losses_MW": np.nan,
                "total_base_load_MW": float(base_p.loc[t].sum()),
                "total_ev_charging_MW": float(charging.loc[t].sum()),
                "total_depot_load_MW": float(base_p.loc[t].sum() + charging.loc[t].sum()),
            })
    return pd.DataFrame(rows), pd.DataFrame(line_rows)


def run_timeseries(network_factory, base_p, base_q, schedule, bus_map):
    return _simulate(network_factory, base_p, base_q, schedule, bus_map, False)[0]


def run_timeseries_detailed(network_factory, base_p, base_q, schedule, bus_map):
    return _simulate(network_factory, base_p, base_q, schedule, bus_map, True)


def network_summary(results, scenario):
    return pd.DataFrame([{
        "scenario": scenario,
        "hours": len(results),
        "failed_powerflows": int((~results.converged).sum()),
        "min_voltage_pu": results.min_voltage_pu.min(),
        "max_line_loading_percent": results.max_line_loading_percent.max(),
        "max_trafo_loading_percent": results.max_trafo_loading_percent.max(),
        "network_losses_MWh": results.total_losses_MW.sum() * config.DT_H,
        "peak_ev_charging_MW": results.total_ev_charging_MW.max(),
        "peak_total_depot_load_MW": results.total_depot_load_MW.max(),
    }])


def _base_snapshot(network_factory, base_p_row, base_q_row, bus_map):
    net = network_factory()
    idx = add_depot_loads(net, bus_map)
    set_depot_snapshot(net, idx, base_p_row.to_dict(), base_q_row.to_dict())
    return net, idx


def _set_extra_ev(net, idx, p_by_depot):
    tan_phi = 0.0 if np.isclose(config.EV_POWER_FACTOR, 1.0) else np.tan(np.arccos(config.EV_POWER_FACTOR))
    for depot, p in p_by_depot.items():
        net.load.loc[idx[depot], "p_mw"] += float(p)
        net.load.loc[idx[depot], "q_mvar"] += float(p) * tan_phi


def check_installed_chargers_feasibility(network_factory, base_p, base_q, bus_map, charger_power_by_depot):
    rows = []
    for t in base_p.index:
        net, idx = _base_snapshot(network_factory, base_p.loc[t], base_q.loc[t], bus_map)
        _set_extra_ev(net, idx, charger_power_by_depot)
        status = constraint_status(net)
        for depot in config.DEPOTS:
            rows.append({
                "time": t, "depot": depot, "bus": int(bus_map[depot]),
                "charger_power_MW": float(charger_power_by_depot[depot]),
                "safe_charging_limit_MW": float(charger_power_by_depot[depot]) if status["feasible"] else 0.0,
                "all_installed_feasible": bool(status["feasible"]),
                "min_voltage_pu_at_full_charge": status["min_voltage_pu"],
                "max_line_loading_percent_at_full_charge": status["max_line_loading_percent"],
                "max_trafo_loading_percent_at_full_charge": status["max_trafo_loading_percent"],
                "full_charge_failure_reason": status["binding_reason"],
            })
    return pd.DataFrame(rows)


def _search_limit(make_net, initial_high, tol=config.HEADROOM_TOL_MW):
    low, high = 0.0, max(float(initial_high), tol)
    reason = "none"
    while True:
        status = constraint_status(make_net(high))
        if not status["feasible"]:
            reason = status["binding_reason"]
            break
        low = high
        if high >= config.HEADROOM_HARD_LIMIT_MW:
            return low, True, "above_search_limit"
        high = min(high * config.HEADROOM_GROWTH_FACTOR, config.HEADROOM_HARD_LIMIT_MW)
    while high - low > tol:
        mid = (low + high) / 2
        if constraint_status(make_net(mid))["feasible"]:
            low = mid
        else:
            high = mid
    return low, False, reason


def calculate_shared_bus_critical_headroom(network_factory, base_p, base_q, bus_map, critical_times, initial_high=1.0):
    """Physical aggregate EV headroom at a few critical hours only."""
    rows = []
    for raw_t in critical_times:
        t = pd.to_datetime(raw_t, utc=True)
        def make(extra_mw):
            net, idx = _base_snapshot(network_factory, base_p.loc[t], base_q.loc[t], bus_map)
            # All depots share one bus; place the diagnostic extra load on one depot element.
            _set_extra_ev(net, idx, {config.DEPOTS[0]: float(extra_mw)})
            return net
        headroom, capped, reason = _search_limit(make, initial_high)
        rows.append({
            "time": t, "shared_bus": int(next(iter(set(bus_map.values())))),
            "aggregate_extra_EV_headroom_MW": headroom,
            "search_capped": capped, "binding_reason": reason,
        })
    return pd.DataFrame(rows)


def build_snapshot_network(network_factory, base_p, base_q, schedule, bus_map, time):
    charging = schedule_to_wide(schedule)
    t = pd.to_datetime(time, utc=True)
    net = network_factory()
    idx = add_depot_loads(net, bus_map)
    set_depot_snapshot(net, idx, base_p.loc[t].to_dict(), base_q.loc[t].to_dict(), charging.loc[t].to_dict(), config.EV_POWER_FACTOR)
    pp.runpp(net)
    return net

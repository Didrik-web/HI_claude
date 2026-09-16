from __future__ import annotations
import numpy as np
import pandas as pd
import pandapower as pp
from .. import config
from .timeseries import constraint_status


def candidate_mv_buses(net):
    ext_buses = set(net.ext_grid["bus"].astype(int)) if len(net.ext_grid) else set()
    eligible = net.bus.loc[~net.bus.index.isin(ext_buses)].copy()
    if eligible.empty:
        return []
    dominant_vn = float(eligible["vn_kv"].value_counts().idxmax())
    return [int(i) for i in eligible.index[np.isclose(eligible["vn_kv"], dominant_vn)]]


def screen_shared_connection_points(network_factory, base_p, base_q, candidate_buses=None):
    """Rank one common connection bus for the aggregated logistics area."""
    probe = network_factory()
    buses = candidate_buses or candidate_mv_buses(probe)
    aggregate_p = base_p[config.DEPOTS].sum(axis=1)
    aggregate_q = base_q[config.DEPOTS].sum(axis=1)
    peak_time = aggregate_p.idxmax()
    p_peak, q_peak = float(aggregate_p.loc[peak_time]), float(aggregate_q.loc[peak_time])

    rows = []
    for bus in buses:
        net = network_factory()
        pp.create_load(net, bus=int(bus), p_mw=p_peak, q_mvar=q_peak, name="Aggregated logistics area")
        status = constraint_status(net)
        losses = np.nan
        if status["converged"]:
            losses = float(net.res_line.pl_mw.sum()) + (float(net.res_trafo.pl_mw.sum()) if len(net.res_trafo) else 0.0)
        rows.append({
            "candidate_bus": int(bus), "peak_time": peak_time,
            "aggregate_depot_P_MW": p_peak, "aggregate_depot_Q_Mvar": q_peak,
            "feasible": bool(status["feasible"]),
            "min_voltage_pu": status["min_voltage_pu"],
            "max_line_loading_percent": status["max_line_loading_percent"],
            "max_trafo_loading_percent": status["max_trafo_loading_percent"],
            "total_losses_MW": losses, "failure_reason": status["binding_reason"],
        })

    out = pd.DataFrame(rows)
    penalty = (~out["feasible"]).astype(int) * 1e6
    out["screening_score"] = (
        penalty
        + (1.0 - out["min_voltage_pu"].fillna(0.0)).clip(lower=0) * 1000
        + out["max_line_loading_percent"].fillna(1e4)
        + out["max_trafo_loading_percent"].fillna(1e4)
        + out["total_losses_MW"].fillna(1e4) * 100
    )
    out["rank"] = out["screening_score"].rank(method="dense", ascending=True).astype(int)
    return out.sort_values(["rank", "candidate_bus"]).reset_index(drop=True)

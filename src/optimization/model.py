import pandas as pd
import pulp


def _prepare_fleet(fleet):
    f = fleet.copy()
    f["time"] = pd.to_datetime(f.time, utc=True)
    f["day"] = pd.to_datetime(f.day, utc=True)
    return f.sort_values(["time", "depot"]).reset_index(drop=True)


def _prepare_limits(network_limits):
    n = network_limits.copy()
    n["time"] = pd.to_datetime(n.time, utc=True)
    if n.duplicated(["time", "depot"]).any():
        raise ValueError("network_limits has duplicate (time, depot) rows")
    return n.set_index(["depot", "time"])["safe_charging_limit_MW"].astype(float).to_dict()


def _common_model(fleet, network_limits, name):
    f = _prepare_fleet(fleet)
    safe = _prepare_limits(network_limits)
    model = pulp.LpProblem(name, pulp.LpMinimize)
    P = {}
    for r in f.itertuples():
        key = (r.depot, r.time)
        if key not in safe:
            raise ValueError(f"Missing network limit for {key}")
        upper = min(float(r.charger_power_MW) * float(r.availability), float(safe[key]))
        P[key] = pulp.LpVariable(f"P_{r.depot}_{r.Index}", lowBound=0, upBound=max(0.0, upper))

    for (depot, day), g in f.groupby(["depot", "day"]):
        required = float(g.energy_required_MWh.iloc[0])
        model += pulp.lpSum(
            P[(r.depot, r.time)] * float(r.dt_h) * float(r.charging_efficiency)
            for r in g.itertuples()
        ) >= required
    return model, P, f


def _build_schedule(P, fleet):
    lookup = fleet.set_index(["depot", "time"])
    rows = []
    for (depot, time), var in P.items():
        src = lookup.loc[(depot, time)]
        p = float(pulp.value(var) or 0.0)
        rows.append({
            "time": time, "depot": depot, "charging_MW": p,
            "base_load_MW": float(src.base_load_MW),
            "total_depot_load_MW": float(src.base_load_MW) + p,
            "availability": float(src.availability), "day": src.day,
            "dt_h": float(src.dt_h), "charging_efficiency": float(src.charging_efficiency),
        })
    return pd.DataFrame(rows).sort_values(["time", "depot"]).reset_index(drop=True)


def optimize_cost(fleet, network_limits, prices):
    model, P, f = _common_model(fleet, network_limits, "Cost_Minimization")
    prices = prices.copy(); prices["time"] = pd.to_datetime(prices.time, utc=True)
    price = dict(zip(prices.time, prices.price_EUR_MWh.astype(float)))
    model += pulp.lpSum(P[(r.depot, r.time)] * float(r.dt_h) * price[r.time] for r in f.itertuples())
    model.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[model.status] != "Optimal":
        raise RuntimeError(f"Cost optimization status: {pulp.LpStatus[model.status]}")
    schedule = _build_schedule(P, f)
    return schedule, pd.DataFrame([{
        "status": "Optimal", "objective": "electricity_cost",
        "total_cost_EUR": float(pulp.value(model.objective)),
        "grid_energy_MWh": float((schedule.charging_MW * schedule.dt_h).sum()),
        "delivered_energy_MWh": float((schedule.charging_MW * schedule.dt_h * schedule.charging_efficiency).sum()),
        "peak_charging_MW": float(schedule.groupby("time").charging_MW.sum().max()),
    }])


def optimize_loss(fleet, network_limits, loss_factors):
    model, P, f = _common_model(fleet, network_limits, "Loss_Minimization")
    lf = loss_factors.copy(); lf["time"] = pd.to_datetime(lf.time, utc=True)
    factor = lf.set_index(["depot", "time"]).loss_coefficient.astype(float).to_dict()
    model += pulp.lpSum(
        factor[(r.depot, r.time)] * P[(r.depot, r.time)] * float(r.dt_h)
        for r in f.itertuples()
    )
    model.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[model.status] != "Optimal":
        raise RuntimeError(f"Loss optimization status: {pulp.LpStatus[model.status]}")
    schedule = _build_schedule(P, f)
    return schedule, pd.DataFrame([{
        "status": "Optimal", "objective": "linearized_marginal_losses",
        "loss_proxy_MWh": float(pulp.value(model.objective)),
        "grid_energy_MWh": float((schedule.charging_MW * schedule.dt_h).sum()),
        "delivered_energy_MWh": float((schedule.charging_MW * schedule.dt_h * schedule.charging_efficiency).sum()),
        "peak_charging_MW": float(schedule.groupby("time").charging_MW.sum().max()),
    }])

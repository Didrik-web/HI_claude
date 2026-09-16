import pandas as pd
import pandapower as pp
from .. import config

SWITCH_CONFIGS_STEP1 = {
    "Base": [False, False, False],
    "Config1": [True, False, False],
    "Config2": [False, True, False],
    "Config3": [False, False, True],
}
SWITCH_CONFIGS_ALL_CLOSED = {"AllClosed": [True, True, True]}
TIE_LINE_NAMES = ("Line 6-7", "Line 11-4", "Line 14-8")


def _norm_name(value):
    return str(value).replace("–", "-").replace("—", "-").strip().lower()


def _switch_rows(net):
    rows = []
    for name in ("S1", "S2", "S3"):
        matches = net.switch.index[net.switch["name"] == name].tolist()
        if len(matches) != 1:
            raise ValueError(f"Expected one switch named {name}, found {len(matches)}")
        rows.append(matches[0])
    return rows


def _ordinary_contingency_lines(net):
    tie_names = {_norm_name(n) for n in TIE_LINE_NAMES}
    tie_indices = [i for i in net.line.index if _norm_name(net.line.loc[i, "name"]) in tie_names]
    if len(tie_indices) != 3:
        raise ValueError(
            "Could not identify the three switch/tie lines by the corrected names "
            f"{TIE_LINE_NAMES}. Found indices {tie_indices}."
        )
    ordinary = [i for i in net.line.index if i not in tie_indices]
    if len(ordinary) != 12:
        raise ValueError(f"Expected 12 ordinary contingency lines, found {len(ordinary)}")
    return ordinary


def run_n1(net, v_min=config.V_MIN, v_max=config.V_MAX,
           line_max=config.LINE_LOADING_MAX, trafo_max=config.TRAFO_LOADING_MAX,
           switch_configs=None):
    """Run temporary single-line outages.

    Step 1 default: four switching configurations.
    Step 2-5: pass SWITCH_CONFIGS_ALL_CLOSED.
    Each line is restored before the next outage; the input network is restored
    before returning.
    """
    if switch_configs is None:
        switch_configs = SWITCH_CONFIGS_STEP1

    switch_rows = _switch_rows(net)
    lines = _ordinary_contingency_lines(net)
    original_switch = net.switch.loc[switch_rows, "closed"].copy()
    original_lines = net.line["in_service"].copy()
    summary, violations = [], []

    try:
        for config_name, states in switch_configs.items():
            for row, state in zip(switch_rows, states):
                net.switch.loc[row, "closed"] = bool(state)

            for line in lines:
                net.line.loc[line, "in_service"] = False
                line_name = net.line.loc[line, "name"]
                try:
                    pp.runpp(net)
                    supplied = net.res_bus.vm_pu.dropna()
                    isolated = net.res_bus.index[net.res_bus.vm_pu.isna()].tolist()
                    min_v = float(supplied.min()) if len(supplied) else float("nan")
                    max_v = float(supplied.max()) if len(supplied) else float("nan")
                    max_line = float(net.res_line.loading_percent.max()) if len(net.res_line) else 0.0
                    max_trafo = float(net.res_trafo.loading_percent.max()) if len(net.res_trafo) else 0.0
                    line_loss = float(net.res_line.pl_mw.sum()) if len(net.res_line) else 0.0
                    trafo_loss = float(net.res_trafo.pl_mw.sum()) if len(net.res_trafo) else 0.0
                    total_loss = line_loss + trafo_loss

                    voltage_ok = bool(len(supplied) and min_v >= v_min and max_v <= v_max)
                    line_ok = bool(max_line <= line_max)
                    trafo_ok = bool(max_trafo <= trafo_max)
                    electrical_ok = voltage_ok and line_ok and trafo_ok
                    full_supply_ok = electrical_ok and len(isolated) == 0

                    reasons = []
                    if isolated: reasons.append("islanding")
                    if not voltage_ok: reasons.append("voltage")
                    if not line_ok: reasons.append("line_loading")
                    if not trafo_ok: reasons.append("trafo_loading")

                    summary.append({
                        "switch_scenario": config_name,
                        "line_removed": line_name,
                        "powerflow_converged": True,
                        "buses_isolated": len(isolated),
                        "min_voltage_pu": min_v,
                        "max_voltage_pu": max_v,
                        "max_line_loading_percent": max_line,
                        "max_trafo_loading_percent": max_trafo,
                        "total_losses_MW": total_loss,
                        "voltage_limits_ok": voltage_ok,
                        "line_limits_ok": line_ok,
                        "trafo_limits_ok": trafo_ok,
                        "electrical_limits_ok": electrical_ok,
                        "full_supply_ok": full_supply_ok,
                        "feasible": full_supply_ok,
                        "failure_reason": "+".join(reasons) if reasons else "none",
                    })

                    for b in isolated:
                        violations.append({
                            "switch_scenario": config_name, "line_removed": line_name,
                            "broken_by": "Bus", "element_name": net.bus.loc[b, "name"],
                            "measured_value": None, "limit_broken": "isolated - no supply",
                        })
                    for b, r in net.res_bus[net.res_bus.vm_pu < v_min].iterrows():
                        violations.append({
                            "switch_scenario": config_name, "line_removed": line_name,
                            "broken_by": "Bus", "element_name": net.bus.loc[b, "name"],
                            "measured_value": r.vm_pu, "limit_broken": f"voltage below {v_min} pu",
                        })
                    for b, r in net.res_bus[net.res_bus.vm_pu > v_max].iterrows():
                        violations.append({
                            "switch_scenario": config_name, "line_removed": line_name,
                            "broken_by": "Bus", "element_name": net.bus.loc[b, "name"],
                            "measured_value": r.vm_pu, "limit_broken": f"voltage above {v_max} pu",
                        })
                    for l, r in net.res_line[net.res_line.loading_percent > line_max].iterrows():
                        violations.append({
                            "switch_scenario": config_name, "line_removed": line_name,
                            "broken_by": "Line", "element_name": net.line.loc[l, "name"],
                            "measured_value": r.loading_percent, "limit_broken": f"loading above {line_max}%",
                        })
                    if len(net.res_trafo):
                        for tr, r in net.res_trafo[net.res_trafo.loading_percent > trafo_max].iterrows():
                            violations.append({
                                "switch_scenario": config_name, "line_removed": line_name,
                                "broken_by": "Transformer", "element_name": net.trafo.loc[tr, "name"],
                                "measured_value": r.loading_percent, "limit_broken": f"loading above {trafo_max}%",
                            })
                except pp.LoadflowNotConverged:
                    summary.append({
                        "switch_scenario": config_name, "line_removed": line_name,
                        "powerflow_converged": False, "buses_isolated": None,
                        "min_voltage_pu": None, "max_voltage_pu": None,
                        "max_line_loading_percent": None, "max_trafo_loading_percent": None,
                        "total_losses_MW": None, "voltage_limits_ok": False,
                        "line_limits_ok": False, "trafo_limits_ok": False,
                        "electrical_limits_ok": False, "full_supply_ok": False,
                        "feasible": False, "failure_reason": "power_flow_not_converged",
                    })
                finally:
                    net.line.loc[line, "in_service"] = True
    finally:
        net.switch.loc[switch_rows, "closed"] = original_switch
        net.line["in_service"] = original_lines

    return pd.DataFrame(summary), pd.DataFrame(violations)

import pandas as pd
import pandapower as pp
from .. import config
from .model import add_depot_loads, set_depot_snapshot


def _total_loss(net):
    return float(net.res_line.pl_mw.sum()) + (float(net.res_trafo.pl_mw.sum()) if len(net.res_trafo) else 0.0)


def calculate_marginal_loss_factors(network_factory, base_p, base_q, bus_map, delta_p_mw=0.05):
    """Local AC marginal-loss sensitivity around the Step-2 base operating point.

    When all depots share one bus, one perturbation per hour is sufficient and
    the same coefficient is copied to all depots. This is physically expected:
    the grid sees the same marginal location irrespective of company name.
    """
    shared = len(set(bus_map.values())) == 1
    rows = []

    for t in base_p.index:
        base = network_factory()
        idx = add_depot_loads(base, bus_map)
        set_depot_snapshot(base, idx, base_p.loc[t].to_dict(), base_q.loc[t].to_dict())
        pp.runpp(base)
        base_loss = _total_loss(base)

        if shared:
            net = network_factory()
            idx2 = add_depot_loads(net, bus_map)
            set_depot_snapshot(net, idx2, base_p.loc[t].to_dict(), base_q.loc[t].to_dict())
            net.load.loc[idx2[config.DEPOTS[0]], "p_mw"] += delta_p_mw
            pp.runpp(net)
            perturbed = _total_loss(net)
            k = (perturbed - base_loss) / delta_p_mw
            for depot in config.DEPOTS:
                rows.append({
                    "time": t, "depot": depot, "bus": int(bus_map[depot]),
                    "loss_coefficient": k, "base_loss_MW": base_loss,
                    "perturbed_loss_MW": perturbed, "delta_p_MW": delta_p_mw,
                })
        else:
            for depot in config.DEPOTS:
                net = network_factory()
                idx2 = add_depot_loads(net, bus_map)
                set_depot_snapshot(net, idx2, base_p.loc[t].to_dict(), base_q.loc[t].to_dict())
                net.load.loc[idx2[depot], "p_mw"] += delta_p_mw
                pp.runpp(net)
                perturbed = _total_loss(net)
                rows.append({
                    "time": t, "depot": depot, "bus": int(bus_map[depot]),
                    "loss_coefficient": (perturbed - base_loss) / delta_p_mw,
                    "base_loss_MW": base_loss, "perturbed_loss_MW": perturbed,
                    "delta_p_MW": delta_p_mw,
                })
    return pd.DataFrame(rows)

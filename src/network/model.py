import numpy as np
import pandapower as pp
from pandapower.networks import create_cigre_network_mv
from .. import config

RING_SWITCH_NAMES = ("S1", "S2", "S3")


def set_ring_switches(net, closed=True):
    for name in RING_SWITCH_NAMES:
        matches = net.switch.index[net.switch["name"] == name].tolist()
        if len(matches) != 1:
            raise ValueError(f"Expected one switch named {name}, found {len(matches)}")
        net.switch.loc[matches[0], "closed"] = bool(closed)
    return net


def build_network(halve_existing_loads=False, close_ring_switches=False):
    """Build the CIGRE MV benchmark network.

    Step 1: default CIGRE topology, full original load.
    Step 2-5: original loads halved AND S1/S2/S3 closed, per project update.
    """
    net = create_cigre_network_mv(with_der=False)
    if close_ring_switches:
        set_ring_switches(net, True)
    if halve_existing_loads:
        net.load["p_mw"] *= 0.5
        net.load["q_mvar"] *= 0.5
    return net


def validate_bus_map(net, bus_map):
    missing = set(config.DEPOTS) - set(bus_map)
    extra = set(bus_map) - set(config.DEPOTS)
    if missing or extra:
        raise ValueError(f"bus_map mismatch. Missing={sorted(missing)}, extra={sorted(extra)}")
    invalid = {d: int(b) for d, b in bus_map.items() if int(b) not in net.bus.index}
    if invalid:
        raise ValueError(f"Mapping contains non-existing buses: {invalid}")
    return {d: int(bus_map[d]) for d in config.DEPOTS}


def add_depot_loads(net, bus_map):
    bus_map = validate_bus_map(net, bus_map)
    return {
        depot: pp.create_load(
            net, bus=bus_map[depot], p_mw=0.0, q_mvar=0.0,
            name=f"Depot {depot}",
        )
        for depot in config.DEPOTS
    }


def set_depot_snapshot(net, load_idx, p_by_depot, q_by_depot=None, ev_by_depot=None, ev_pf=1.0):
    q_by_depot = q_by_depot or {d: 0.0 for d in config.DEPOTS}
    ev_by_depot = ev_by_depot or {d: 0.0 for d in config.DEPOTS}
    tan_phi = 0.0 if np.isclose(ev_pf, 1.0) else np.tan(np.arccos(ev_pf))
    for depot in config.DEPOTS:
        p = float(p_by_depot[depot]) + float(ev_by_depot[depot])
        q = float(q_by_depot[depot]) + float(ev_by_depot[depot]) * tan_phi
        net.load.loc[load_idx[depot], ["p_mw", "q_mvar"]] = [p, q]

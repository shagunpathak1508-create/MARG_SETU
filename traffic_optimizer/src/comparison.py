"""
Before / After comparison engine.

Computes network-wide traffic metrics under the current (default)
signal timing and again after applying congestion-proportional
signal optimization, then returns both snapshots + improvement %.
"""
from routing import get_emergency_route, CONGESTION_PENALTY
from signals import (
    compute_default_signal_state,
    optimize_signal_timing,
)


# ── Metric snapshot ───────────────────────────────────────────
def _compute_network_metrics(G, label="current"):
    """Aggregate traffic metrics from graph edge attributes."""
    edges = list(G.edges(data=True))
    n = len(edges)
    if n == 0:
        return {}

    sum_ratio    = 0.0
    sum_speed    = 0.0
    sum_wait     = 0.0
    sum_queue    = 0.0
    sum_vehicles = 0
    sum_capacity = 0
    congested    = 0

    for _, _, d in edges:
        ratio     = d.get("congestion_ratio", 0)
        speed_lim = d.get("speed_limit_kmh", 40)
        vehicles  = d.get("current_vehicles", 0)
        capacity  = d.get("capacity", 100)

        sum_ratio    += ratio
        sum_vehicles += vehicles
        sum_capacity += capacity

        # Effective speed degrades with congestion
        sum_speed += speed_lim * max(0.15, 1 - ratio * 0.6)

        # Average signal wait (seconds) grows with congestion
        sum_wait += 30 * (1 + ratio * 1.5)

        # Queue = excess vehicles beyond capacity
        sum_queue += max(0, vehicles - capacity)

        if ratio > 1.0:
            congested += 1

    # Sample emergency ETA  (J08 Ring Rd South → J04 Hospital)
    emerg     = get_emergency_route(G, "J08", "J04")
    emerg_eta = emerg.get("estimated_time_min", 0)

    return {
        "label":                 label,
        "avg_congestion_pct":    round((sum_ratio / n) * 100, 1),
        "avg_speed_kmh":         round(sum_speed / n, 1),
        "avg_waiting_time_sec":  round(sum_wait / n, 1),
        "avg_queue_length":      round(sum_queue / n, 1),
        "total_congested_roads": congested,
        "total_vehicles":        sum_vehicles,
        "total_capacity":        sum_capacity,
        "network_load_pct":      round((sum_vehicles / sum_capacity) * 100, 1)
                                 if sum_capacity else 0,
        "emergency_eta_min":     round(emerg_eta, 2),
    }


# ── Optimization effects ─────────────────────────────────────
def _build_optimized_graph(G, junctions_df=None):
    """
    Return a *copy* of *G* whose edge attributes reflect the
    throughput improvement from congestion-proportional signal timing.

    For each junction the default equal-split and the optimised
    green times are compared.  Approaches that receive *more*
    green have their effective congestion reduced proportionally.
    """
    # 1. Collect per-junction improvement factors
    #    junction_effects[jid][neighbour] = opt_green / default_green
    junction_effects = {}
    for jid in G.nodes:
        default   = compute_default_signal_state(G, jid, junctions_df)
        optimized, _ = optimize_signal_timing(G, jid, junctions_df)
        if not default or not optimized:
            continue
        eff = {}
        for dp, op in zip(default["phases"], optimized["phases"]):
            dg = dp["green_time_sec"]
            if dg > 0:
                eff[dp["from_junction"]] = op["green_time_sec"] / dg
        junction_effects[jid] = eff

    # 2. Apply to a copy of the graph
    G_opt = G.copy()
    for u, v, d in G_opt.edges(data=True):
        # Factor at v for traffic arriving from u (flow u→v)
        f_uv = junction_effects.get(v, {}).get(u, 1.0)
        # Factor at u for traffic arriving from v (flow v→u)
        f_vu = junction_effects.get(u, {}).get(v, 1.0)
        # Use the average; net improvement if > 1
        avg_f = (f_uv + f_vu) / 2

        if avg_f > 1.0:
            cap      = d["capacity"]
            new_veh  = max(0, int(d["current_vehicles"] / avg_f))
            new_r    = new_veh / cap if cap > 0 else 0
            dist     = d["distance_km"]
            speed    = d["speed_limit_kmh"]
            base_t   = (dist / speed) * 60 if speed > 0 else float("inf")

            d["current_vehicles"]    = new_veh
            d["congestion_ratio"]    = round(new_r, 4)
            d["effective_cost"]      = round(dist * (1 + CONGESTION_PENALTY * new_r), 4)
            d["adjusted_travel_time"] = round(base_t * (1 + new_r * 2), 4)

    return G_opt


# ── Public API ────────────────────────────────────────────────
def compute_comparison(G, junctions_df=None):
    """
    Main entry point.

    Returns ``{before, after, improvements, optimization_applied}``.
    """
    before = _compute_network_metrics(G, "before")
    G_opt  = _build_optimized_graph(G, junctions_df)
    after  = _compute_network_metrics(G_opt, "after")

    # Improvement % (positive = better)
    improvements = {}
    for key in ("avg_congestion_pct", "avg_waiting_time_sec",
                "avg_queue_length", "total_congested_roads",
                "emergency_eta_min"):
        b, a = before.get(key, 0), after.get(key, 0)
        pct  = round(((b - a) / b) * 100, 1) if b else 0
        improvements[key] = {"before": b, "after": a,
                             "improvement_pct": pct}

    # Speed — higher is better
    bs, afs = before.get("avg_speed_kmh", 0), after.get("avg_speed_kmh", 0)
    improvements["avg_speed_kmh"] = {
        "before": bs, "after": afs,
        "improvement_pct": round(((afs - bs) / bs) * 100, 1) if bs else 0,
    }

    return {
        "before":               before,
        "after":                after,
        "improvements":         improvements,
        "optimization_applied": "congestion_proportional_signal_timing",
    }

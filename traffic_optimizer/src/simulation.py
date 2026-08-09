"""
Scenario simulation engine.

Applies user-specified parameters (traffic multiplier, road closure,
emergency presence, incident severity) to a *copy* of the current
network state, then runs the comparison engine to produce
before/after metrics.  The live state is never mutated.
"""
from routing import create_graph, CONGESTION_PENALTY
from comparison import compute_comparison


def run_simulation(segments_df, junctions_df, params):
    """
    Execute a "what-if" simulation.

    Parameters (all optional, in *params* dict)
    --------------------------------------------
    traffic_multiplier : float   Scale all vehicle counts (default 1.0)
    road_closure       : str     segment_id to block
    incident_segment   : str     segment_id where incident occurs
    incident_severity  : float   1.0–3.0, multiplies congestion at incident
    emergency          : bool    include emergency-vehicle ETA in output
    congestion_override: float   override ALL ratios to this value (demo)

    Returns
    -------
    dict  with ``params``, ``before``, ``after``, ``improvements``
    """
    multiplier    = params.get("traffic_multiplier", 1.0)
    closure       = params.get("road_closure", None)
    inc_seg       = params.get("incident_segment", None)
    inc_severity  = params.get("incident_severity", 2.0)
    cong_override = params.get("congestion_override", None)

    # ── Build a fresh graph from the canonical CSV data ──────
    G = create_graph(segments_df)

    # ── Apply traffic multiplier ─────────────────────────────
    if multiplier != 1.0:
        for u, v, d in G.edges(data=True):
            cap     = d["capacity"]
            new_veh = max(0, int(d["current_vehicles"] * multiplier))
            new_r   = new_veh / cap if cap > 0 else 0
            dist    = d["distance_km"]
            speed   = d["speed_limit_kmh"]
            base_t  = (dist / speed) * 60 if speed > 0 else float("inf")

            d["current_vehicles"]     = new_veh
            d["congestion_ratio"]     = round(new_r, 4)
            d["effective_cost"]       = round(dist * (1 + CONGESTION_PENALTY * new_r), 4)
            d["adjusted_travel_time"] = round(base_t * (1 + new_r * 2), 4)

    # ── Apply congestion override (demo knob) ────────────────
    if cong_override is not None:
        for u, v, d in G.edges(data=True):
            cap   = d["capacity"]
            new_r = float(cong_override)
            d["current_vehicles"]     = int(cap * new_r)
            d["congestion_ratio"]     = round(new_r, 4)
            dist  = d["distance_km"]
            speed = d["speed_limit_kmh"]
            base_t = (dist / speed) * 60 if speed > 0 else float("inf")
            d["effective_cost"]       = round(dist * (1 + CONGESTION_PENALTY * new_r), 4)
            d["adjusted_travel_time"] = round(base_t * (1 + new_r * 2), 4)

    # ── Apply incident ───────────────────────────────────────
    if inc_seg:
        for u, v, d in G.edges(data=True):
            if d.get("segment_id") == inc_seg:
                cap     = d["capacity"]
                new_veh = int(d["current_vehicles"] * inc_severity)
                new_r   = new_veh / cap if cap > 0 else 0
                dist    = d["distance_km"]
                speed   = d["speed_limit_kmh"]
                base_t  = (dist / speed) * 60 if speed > 0 else float("inf")

                d["current_vehicles"]     = new_veh
                d["congestion_ratio"]     = round(new_r, 4)
                d["effective_cost"]       = round(
                    dist * (1 + CONGESTION_PENALTY * new_r), 4)
                d["adjusted_travel_time"] = round(
                    base_t * (1 + new_r * 2), 4)
                break

    # ── Apply road closure ───────────────────────────────────
    if closure:
        for u, v, d in G.edges(data=True):
            if d.get("segment_id") == closure:
                d["blocked"] = True
                break

    # ── Run the comparison engine on the modified graph ──────
    result = compute_comparison(G, junctions_df)
    result["simulation_params"] = params
    return result

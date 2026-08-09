"""
Diversion / road-closure management.

Given a blocked segment, recommends an alternative route,
estimates delay impact, and can "activate" the diversion
(marking the closure + adjusting signal state).
"""
import uuid
import time as _time

from routing import (
    create_graph,
    get_optimal_route,
    CONGESTION_PENALTY,
)
from signals import (
    get_junction_approaches,
    optimize_signal_timing,
)

# In-memory store of active diversions
_active_diversions = {}


# ── Recommend ─────────────────────────────────────────────────
def recommend_diversion(G, blocked_segment_id, junctions_df=None):
    """
    Propose a diversion around *blocked_segment_id*.

    Returns the blocked-road details, an alternative route,
    the expected delay increase, and affected junctions.
    """
    # Locate the segment
    target = None
    for u, v, d in G.edges(data=True):
        if d.get("segment_id") == blocked_segment_id:
            target = (u, v, dict(d))
            break
    if target is None:
        return {"error": f"Segment '{blocked_segment_id}' not found."}

    u, v, edge_data = target

    # Block in a graph copy
    G_mod = G.copy()
    G_mod[u][v]["blocked"] = True

    # Alternative route
    alt = get_optimal_route(G_mod, u, v, avoid_blocked=True)
    if "error" in alt:
        return {"error": f"No alternative route: {alt['error']}"}

    orig_time = edge_data.get("adjusted_travel_time", 0)
    orig_dist = edge_data.get("distance_km", 0)
    div_time  = alt.get("estimated_time_min", 0)
    div_dist  = alt.get("total_distance_km", 0)

    # Affected junctions along the diversion
    affected = []
    for jid in alt["path"]:
        appr = get_junction_approaches(G, jid)
        max_c = max((a["congestion_ratio"] for a in appr), default=0)
        affected.append({
            "junction_id":            jid,
            "current_max_congestion": round(max_c, 2),
            "expected_impact":        ("High" if max_c > 0.8
                                       else "Moderate" if max_c > 0.5
                                       else "Low"),
        })

    # Signal recommendations for busy junctions on diversion
    signal_recs = []
    for jid in alt["path"]:
        opt_state, expl = optimize_signal_timing(G, jid, junctions_df)
        if opt_state:
            signal_recs.append({
                "junction_id":   jid,
                "recommendation": opt_state,
                "explanation":    expl,
            })

    div_id = f"DIV-{uuid.uuid4().hex[:6].upper()}"

    proposal = {
        "diversion_id": div_id,
        "status":       "PROPOSED",
        "blocked_segment": {
            "segment_id":              blocked_segment_id,
            "name":                    edge_data.get("name", ""),
            "from_junction":           u,
            "to_junction":             v,
            "original_travel_time_min": round(orig_time, 2),
            "original_distance_km":    round(orig_dist, 2),
        },
        "diversion": {
            "path":            alt["path"],
            "distance_km":     div_dist,
            "travel_time_min": round(div_time, 2),
            "segments":        alt.get("segments", []),
        },
        "impact": {
            "additional_delay_min":  round(div_time - orig_time, 2),
            "distance_increase_km":  round(div_dist - orig_dist, 2),
            "delay_reduction_vs_stuck": (
                f"Diversion adds {round(div_time - orig_time, 1)} min "
                f"but avoids indefinite wait on closed road"
            ),
            "affected_junctions": affected,
        },
        "signal_recommendations": signal_recs,
    }
    _active_diversions[div_id] = proposal
    return proposal


# ── Activate ──────────────────────────────────────────────────
def activate_diversion(diversion_id, signal_store=None):
    """
    Mark diversion ACTIVE and (optionally) push signal
    recommendations into *signal_store*.
    """
    div = _active_diversions.get(diversion_id)
    if not div:
        return {"error": f"Diversion '{diversion_id}' not found."}

    div["status"]       = "ACTIVE"
    div["activated_at"]  = _time.time()

    # Push signal recommendations
    if signal_store is not None:
        for rec in div.get("signal_recommendations", []):
            jid = rec["junction_id"]
            signal_store[jid] = rec["recommendation"]

    return div


# ── Query ─────────────────────────────────────────────────────
def get_diversion(diversion_id):
    d = _active_diversions.get(diversion_id)
    if not d:
        return {"error": f"Diversion '{diversion_id}' not found."}
    return d


def list_diversions():
    return list(_active_diversions.values())

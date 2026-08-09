"""
Emergency corridor management.

Creates, activates, and tracks emergency vehicle corridors
through the road network with signal priority.
State lives in-memory (suitable for a hackathon prototype).
"""
import time
import uuid

from routing import get_emergency_route, get_optimal_route
from signals import generate_emergency_signal_priority

# ── In-memory store ───────────────────────────────────────────
_corridors = {}


# ── Create ────────────────────────────────────────────────────
def create_corridor(G, vehicle_type, origin, destination,
                    priority_level="high", junctions_df=None):
    """
    Build a *proposed* emergency corridor.

    Returns a corridor dict with route, per-junction signal
    recommendations, ETA, and time saved vs. normal routing.
    """
    emer = get_emergency_route(G, origin, destination)
    if "error" in emer:
        return emer

    normal = get_optimal_route(G, origin, destination)
    normal_eta = normal.get("estimated_time_min",
                            emer["estimated_time_min"])

    path = emer["path"]

    # Per-junction signal recommendations
    jstates = []
    for i, jid in enumerate(path):
        approach_from = path[i - 1] if i > 0 else None
        sig = (generate_emergency_signal_priority(
                   G, jid, approach_from, junctions_df)
               if approach_from else None)

        jstates.append({
            "junction_id":           jid,
            "junction_name":         (sig["junction_name"]
                                      if sig else jid),
            "position_index":        i,
            "status":                "PREPARING" if i == 0 else "PENDING",
            "signal_recommendation": sig,
        })

    cid = f"EM-{uuid.uuid4().hex[:6].upper()}"

    # Priority discount on ETA (signal preemption effect)
    pfactor = {"high": 0.70, "medium": 0.80,
               "low": 0.90}.get(priority_level, 0.75)
    adj_eta    = emer["estimated_time_min"] * pfactor
    time_saved = normal_eta - adj_eta

    corridor = {
        "id":                     cid,
        "vehicle_type":           vehicle_type.capitalize(),
        "origin":                 origin,
        "destination":            destination,
        "priority_level":         priority_level,
        "status":                 "PROPOSED",
        "route":                  emer,
        "path":                   path,
        "junctions":              jstates,
        "emergency_eta_min":      round(adj_eta, 2),
        "normal_eta_min":         round(normal_eta, 2),
        "time_saved_min":         round(max(0, time_saved), 2),
        "current_position_index": 0,
        "created_at":             time.time(),
    }
    _corridors[cid] = corridor
    return corridor


# ── Activate ──────────────────────────────────────────────────
def activate_corridor(corridor_id, signal_store):
    """
    Mark corridor ACTIVE and push signal recommendations into
    the shared *signal_store* dict.
    """
    c = _corridors.get(corridor_id)
    if not c:
        return {"error": f"Corridor '{corridor_id}' not found."}
    if c["status"] not in ("PROPOSED", "ACTIVE"):
        return {"error": f"Corridor is '{c['status']}', cannot activate."}

    c["status"]       = "ACTIVE"
    c["activated_at"] = time.time()

    _refresh_junction_statuses(c)

    for js in c["junctions"]:
        rec = js["signal_recommendation"]
        if rec:
            signal_store[js["junction_id"]] = rec

    return c


# ── Query ─────────────────────────────────────────────────────
def get_corridor(corridor_id):
    c = _corridors.get(corridor_id)
    if not c:
        return {"error": f"Corridor '{corridor_id}' not found."}
    return c


def list_corridors():
    return list(_corridors.values())


# ── Progress simulation ──────────────────────────────────────
def advance_corridor(corridor_id, signal_store):
    """Move the vehicle one step along the route."""
    c = _corridors.get(corridor_id)
    if not c:
        return {"error": f"Corridor '{corridor_id}' not found."}
    if c["status"] != "ACTIVE":
        return {"error": f"Corridor is '{c['status']}', not ACTIVE."}

    last = len(c["path"]) - 1
    if c["current_position_index"] >= last:
        c["status"] = "COMPLETED"
        for js in c["junctions"]:
            js["status"] = "CLEARED"
        return c

    c["current_position_index"] += 1
    _refresh_junction_statuses(c)

    if c["current_position_index"] >= last:
        c["status"] = "COMPLETED"
        for js in c["junctions"]:
            js["status"] = "CLEARED"

    return c


# ── Reroute ───────────────────────────────────────────────────
def reroute_corridor(corridor_id, G, blocked_segment_id,
                     junctions_df=None, signal_store=None):
    """
    Reroute around a newly blocked segment.
    Recomputes from the vehicle's current position.
    """
    c = _corridors.get(corridor_id)
    if not c:
        return {"error": f"Corridor '{corridor_id}' not found."}

    # Block the edge in the graph
    for u, v, d in G.edges(data=True):
        if d.get("segment_id") == blocked_segment_id:
            d["blocked"] = True
            break

    cur_jid = c["path"][c["current_position_index"]]
    dest    = c["destination"]

    emer = get_emergency_route(G, cur_jid, dest)
    if "error" in emer:
        return {"error": f"Cannot reroute: {emer['error']}"}

    normal = get_optimal_route(G, cur_jid, dest, avoid_blocked=True)
    normal_eta = normal.get("estimated_time_min",
                            emer["estimated_time_min"])

    new_path = emer["path"]
    c["route"]                  = emer
    c["path"]                   = new_path
    c["current_position_index"] = 0

    pfactor = {"high": 0.70, "medium": 0.80,
               "low": 0.90}.get(c["priority_level"], 0.75)
    adj_eta = emer["estimated_time_min"] * pfactor
    c["emergency_eta_min"] = round(adj_eta, 2)
    c["normal_eta_min"]    = round(normal_eta, 2)
    c["time_saved_min"]    = round(max(0, normal_eta - adj_eta), 2)
    c["rerouted_at"]       = time.time()
    c["reroute_reason"]    = f"Blocked segment {blocked_segment_id}"

    # Rebuild junction states
    jstates = []
    for i, jid in enumerate(new_path):
        approach_from = new_path[i - 1] if i > 0 else None
        sig = (generate_emergency_signal_priority(
                   G, jid, approach_from, junctions_df)
               if approach_from else None)
        status = ("ACTIVE"    if i == 0 else
                  "PREPARING" if i == 1 else "PENDING")
        jstates.append({
            "junction_id":           jid,
            "junction_name":         sig["junction_name"] if sig else jid,
            "position_index":        i,
            "status":                status,
            "signal_recommendation": sig,
        })
    c["junctions"] = jstates

    # Push new signals
    if signal_store is not None:
        for js in jstates:
            rec = js["signal_recommendation"]
            if rec:
                signal_store[js["junction_id"]] = rec

    return c


# ── Internal ──────────────────────────────────────────────────
def _refresh_junction_statuses(corridor):
    pos = corridor["current_position_index"]
    for i, js in enumerate(corridor["junctions"]):
        if i < pos:
            js["status"] = "CLEARED"
        elif i == pos:
            js["status"] = "ACTIVE"
        elif i == pos + 1:
            js["status"] = "PREPARING"
        else:
            js["status"] = "PENDING"

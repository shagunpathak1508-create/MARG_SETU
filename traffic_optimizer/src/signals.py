"""
Signal timing optimization module.

For each junction, analyses incoming traffic on all approach roads
and recommends green-phase durations proportional to congestion.
"""

MIN_GREEN_SEC    = 15
MAX_GREEN_SEC    = 90
TARGET_CYCLE_MIN = 90
TARGET_CYCLE_MAX = 150
DEFAULT_GREEN    = 30          # seconds per phase when no optimisation applied


# ── Helpers ───────────────────────────────────────────────────
def _junction_name(junction_id, junctions_df):
    """Resolve human-readable name from a junctions DataFrame."""
    if junctions_df is None:
        return junction_id
    match = junctions_df[junctions_df["junction_id"].str.strip() == junction_id]
    if match.empty:
        return junction_id
    return str(match.iloc[0].get("name", junction_id))


def get_junction_approaches(G, junction_id):
    """Return a list of approach dicts for every edge touching *junction_id*."""
    if junction_id not in G.nodes:
        return []
    approaches = []
    for neighbour in G.neighbors(junction_id):
        e = G[junction_id][neighbour]
        approaches.append({
            "segment_id":       e.get("segment_id", ""),
            "name":             e.get("name", ""),
            "from_junction":    neighbour,
            "to_junction":      junction_id,
            "congestion_ratio": e.get("congestion_ratio", 0),
            "current_vehicles": e.get("current_vehicles", 0),
            "capacity":         e.get("capacity", 100),
            "road_type":        e.get("road_type", "collector"),
        })
    return approaches


# ── Default (equal-split) state ───────────────────────────────
def compute_default_signal_state(G, junction_id, junctions_df=None):
    """Generate an equal-split signal state for *junction_id*."""
    approaches = get_junction_approaches(G, junction_id)
    if not approaches:
        return None

    n = len(approaches)
    green = max(DEFAULT_GREEN, TARGET_CYCLE_MIN // n)
    total = green * n

    phases = []
    for a in approaches:
        phases.append({
            "segment_id":       a["segment_id"],
            "approach":         f"{a['name']} (from {a['from_junction']})",
            "from_junction":    a["from_junction"],
            "green_time_sec":   green,
            "congestion_ratio": a["congestion_ratio"],
            "current_vehicles": a["current_vehicles"],
            "capacity":         a["capacity"],
        })

    return {
        "junction_id":    junction_id,
        "junction_name":  _junction_name(junction_id, junctions_df),
        "total_cycle_sec": total,
        "phases":          phases,
        "mode":            "default",
    }


# ── Congestion-optimised timing ───────────────────────────────
def optimize_signal_timing(G, junction_id, junctions_df=None):
    """
    Compute congestion-proportional green-phase durations.

    Returns
    -------
    (state_dict, explanation_str)   or   (None, error_str)
    """
    approaches = get_junction_approaches(G, junction_id)
    if not approaches:
        return None, "Junction not found or has no approaches."

    n = len(approaches)

    # Weight: base 1.0 + 2× congestion bonus
    weights    = [1.0 + a["congestion_ratio"] * 2.0 for a in approaches]
    total_w    = sum(weights)
    base_cycle = max(TARGET_CYCLE_MIN, min(TARGET_CYCLE_MAX, n * 30))

    raw    = [(w / total_w) * base_cycle for w in weights]
    greens = [max(MIN_GREEN_SEC, min(MAX_GREEN_SEC, round(g))) for g in raw]

    phases, explanations = [], []
    for i, a in enumerate(approaches):
        phases.append({
            "segment_id":       a["segment_id"],
            "approach":         f"{a['name']} (from {a['from_junction']})",
            "from_junction":    a["from_junction"],
            "green_time_sec":   greens[i],
            "congestion_ratio": a["congestion_ratio"],
            "current_vehicles": a["current_vehicles"],
            "capacity":         a["capacity"],
        })

        r = a["congestion_ratio"]
        label = a["name"]
        if r > 1.0:
            explanations.append(
                f"{label}: critically congested ({r:.2f}), "
                f"extending green to {greens[i]}s")
        elif r > 0.8:
            explanations.append(
                f"{label}: high traffic ({r:.2f}), green {greens[i]}s")
        elif r > 0.5:
            explanations.append(
                f"{label}: moderate traffic, green {greens[i]}s")
        else:
            explanations.append(
                f"{label}: low traffic, green reduced to {greens[i]}s")

    state = {
        "junction_id":    junction_id,
        "junction_name":  _junction_name(junction_id, junctions_df),
        "total_cycle_sec": sum(greens),
        "phases":          phases,
        "mode":            "optimized",
    }
    return state, "; ".join(explanations)


# ── Emergency signal preemption ───────────────────────────────
def generate_emergency_signal_priority(G, junction_id,
                                       approach_from, junctions_df=None):
    """
    Give *approach_from* direction maximum green; all others minimum.
    """
    approaches = get_junction_approaches(G, junction_id)
    if not approaches:
        return None

    phases = []
    for a in approaches:
        is_priority = (a["from_junction"] == approach_from)
        green = MAX_GREEN_SEC if is_priority else MIN_GREEN_SEC
        phases.append({
            "segment_id":       a["segment_id"],
            "approach":         f"{a['name']} (from {a['from_junction']})",
            "from_junction":    a["from_junction"],
            "green_time_sec":   green,
            "congestion_ratio": a["congestion_ratio"],
            "current_vehicles": a["current_vehicles"],
            "capacity":         a["capacity"],
            "priority":         "EMERGENCY" if is_priority else "HELD",
        })

    return {
        "junction_id":    junction_id,
        "junction_name":  _junction_name(junction_id, junctions_df),
        "total_cycle_sec": sum(p["green_time_sec"] for p in phases),
        "phases":          phases,
        "mode":            "emergency",
    }

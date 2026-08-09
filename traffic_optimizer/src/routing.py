"""
Congestion-weighted routing engine using NetworkX.

Builds a road graph from a segments DataFrame and provides three
routing modes:
  - get_optimal_route:           congestion-weighted cost, avoids blocked edges
  - get_shortest_distance_route: pure distance (ignores congestion)
  - get_emergency_route:         minimizes adjusted travel time, ignores blocks
"""
import networkx as nx

# How aggressively congestion increases route cost.
# At ratio=1.0 (100 % capacity) cost is  distance × (1 + 3) = 4×distance.
CONGESTION_PENALTY = 3.0


# ── Graph construction ────────────────────────────────────────
def create_graph(segments_df):
    """
    Build a road graph from a segments DataFrame.

    Expected columns:
        segment_id, name, from_junction, to_junction,
        distance_km, capacity, current_vehicles,
        speed_limit_kmh, road_type, blocked

    Each row becomes an undirected edge with congestion-derived
    attributes (congestion_ratio, effective_cost, travel times).
    """
    G = nx.Graph()

    for _, row in segments_df.iterrows():
        from_j   = str(row["from_junction"]).strip()
        to_j     = str(row["to_junction"]).strip()
        distance = float(row["distance_km"])
        capacity = int(row["capacity"])
        vehicles = int(row["current_vehicles"])
        speed    = int(row["speed_limit_kmh"])
        rtype    = str(row["road_type"]).strip()
        name     = str(row["name"]).strip()
        blocked  = str(row.get("blocked", "False")).strip().lower() in (
            "true", "1", "yes",
        )

        ratio = vehicles / capacity if capacity > 0 else 0.0

        # Base travel time (minutes) = distance / speed × 60
        base_time = (distance / speed) * 60 if speed > 0 else float("inf")

        # Congestion-weighted cost
        eff_cost = distance * (1 + CONGESTION_PENALTY * ratio)

        # Travel time stretched by congestion (vehicles slow down)
        adj_time = base_time * (1 + ratio * 2)

        G.add_edge(
            from_j, to_j,
            segment_id          = str(row.get("segment_id", "")).strip(),
            name                = name,
            distance_km         = round(distance, 4),
            capacity            = capacity,
            current_vehicles    = vehicles,
            congestion_ratio    = round(ratio, 4),
            speed_limit_kmh     = speed,
            road_type           = rtype,
            blocked             = blocked,
            effective_cost      = round(eff_cost, 4),
            base_travel_time    = round(base_time, 4),
            adjusted_travel_time = round(adj_time, 4),
        )

    return G


# ── Routing helpers ───────────────────────────────────────────
def _subgraph_without_blocked(G):
    """Return a subgraph view that excludes blocked edges."""
    edges = [
        (u, v)
        for u, v, d in G.edges(data=True)
        if not d.get("blocked", False)
    ]
    return G.edge_subgraph(edges)


def _collect_route_detail(G, path, time_key="adjusted_travel_time"):
    """Walk *path* and collect per-segment detail + totals."""
    segments = []
    total_dist = 0.0
    total_time = 0.0
    for i in range(len(path) - 1):
        e = G[path[i]][path[i + 1]]
        seg = {
            "from":             path[i],
            "to":               path[i + 1],
            "segment_id":       e.get("segment_id", ""),
            "name":             e.get("name", ""),
            "distance_km":      e["distance_km"],
            "congestion_ratio": e["congestion_ratio"],
            "road_type":        e.get("road_type", ""),
            "travel_time_min":  e[time_key],
        }
        segments.append(seg)
        total_dist += e["distance_km"]
        total_time += e[time_key]
    return segments, round(total_dist, 2), round(total_time, 2)


# ── Public routing functions ──────────────────────────────────
def get_optimal_route(G, start, end, avoid_blocked=True):
    """
    Congestion-optimized route.

    Returns dict with: path, total_cost, total_distance_km,
    estimated_time_min, segments list — or an error key.
    """
    H = _subgraph_without_blocked(G) if avoid_blocked else G

    try:
        path = nx.shortest_path(H, source=start, target=end,
                                weight="effective_cost")
        cost = nx.shortest_path_length(H, source=start, target=end,
                                       weight="effective_cost")
    except nx.NetworkXNoPath:
        return {"error": f"No path found from {start} to {end}"}
    except nx.NodeNotFound as exc:
        return {"error": str(exc)}

    segments, dist, time = _collect_route_detail(H, path)
    return {
        "path":               path,
        "total_cost":         round(cost, 4),
        "total_distance_km":  dist,
        "estimated_time_min": time,
        "segments":           segments,
    }


def get_shortest_distance_route(G, start, end):
    """
    Pure shortest-distance route (congestion ignored).

    Returns dict with: path, total_distance_km — or error key.
    """
    try:
        path = nx.shortest_path(G, source=start, target=end,
                                weight="distance_km")
        cost = nx.shortest_path_length(G, source=start, target=end,
                                       weight="distance_km")
    except (nx.NetworkXNoPath, nx.NodeNotFound) as exc:
        return {"error": str(exc)}

    return {"path": path, "total_distance_km": round(cost, 2)}


def get_emergency_route(G, start, end):
    """
    Fastest route (minimum adjusted travel time).
    Does NOT skip blocked edges — emergency vehicles can override.

    Returns dict with: path, estimated_time_min, segments — or error.
    """
    try:
        path = nx.shortest_path(G, source=start, target=end,
                                weight="adjusted_travel_time")
        total = nx.shortest_path_length(G, source=start, target=end,
                                        weight="adjusted_travel_time")
    except (nx.NetworkXNoPath, nx.NodeNotFound) as exc:
        return {"error": str(exc)}

    segments, _, _ = _collect_route_detail(G, path,
                                          time_key="adjusted_travel_time")
    return {
        "path":               path,
        "estimated_time_min": round(total, 2),
        "segments":           segments,
    }


# ── Legacy wrapper (kept for backward compat) ────────────────
def get_best_route(G, start, end):
    """Legacy function — wraps get_optimal_route."""
    result = get_optimal_route(G, start, end)
    return result.get("path", [])
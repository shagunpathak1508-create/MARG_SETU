import networkx as nx


def create_graph(df=None):
    """
    Build a road graph.
    If df is provided, edge weights are congestion-based (vehicles / capacity).
    Falls back to static weights if df is None.
    """
    G = nx.Graph()

    if df is not None:
        # Normalise column names
        df = df.copy()
        df.columns = df.columns.str.strip()

        # Add nodes with their congestion load
        for _, row in df.iterrows():
            road     = str(row.get("road", row.get("name", "Unknown")))
            vehicles = int(row.get("vehicles", row.get("vehicle_count", 0)))
            capacity = int(row.get("capacity", 1))
            load     = vehicles / capacity if capacity > 0 else 0
            G.add_node(road, load=load, vehicles=vehicles, capacity=capacity)

        # Ring of edges between road nodes
        roads = list(G.nodes())
        for i in range(len(roads)):
            u = roads[i]
            v = roads[(i + 1) % len(roads)]
            load_u = G.nodes[u]["load"]
            load_v = G.nodes[v]["load"]
            edge_w = (load_u + load_v) / 2
            G.add_edge(u, v, weight=edge_w)

    else:
        # Static fallback (single-letter node graph used by /emergency)
        G.add_weighted_edges_from([
            ("A", "B", 2),
            ("B", "C", 3),
            ("A", "D", 4),
            ("D", "E", 2),
            ("B", "E", 1),
        ])

    return G


def get_best_route(G, start, end):
    """Return the traffic-cost-minimising path between start and end."""
    path = nx.shortest_path(G, source=start, target=end, weight="weight")
    return path
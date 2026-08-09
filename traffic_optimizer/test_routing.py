"""
Routing verification script.

Run from the traffic_optimizer/ directory:
    python test_routing.py
"""
import os
import sys
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))

from routing import (
    create_graph,
    get_optimal_route,
    get_shortest_distance_route,
    get_emergency_route,
)


def main():
    # ── Load data ─────────────────────────────────────────────
    seg_path = os.path.join(BASE_DIR, "data", "road_segments.csv")
    seg_df   = pd.read_csv(seg_path)
    seg_df.columns = seg_df.columns.str.strip()

    G = create_graph(seg_df)

    print("=" * 72)
    print("  SMART TRAFFIC FLOW OPTIMIZER  —  Routing Verification")
    print("=" * 72)
    print(f"\n  Graph: {G.number_of_nodes()} junctions, "
          f"{G.number_of_edges()} road segments\n")

    # ── 1. Congestion table ───────────────────────────────────
    print("--- Congestion Ratios per Road Segment ---\n")
    header = (f"{'Seg':<5} {'Road Name':<25} {'From':>4} > {'To':<4} "
              f"{'Veh':>5}/{'Cap':<5} {'Ratio':>6}  {'Level':<10}")
    print(header)
    print("-" * len(header))

    congested_names = []
    for u, v, d in sorted(G.edges(data=True),
                          key=lambda x: x[2]["congestion_ratio"],
                          reverse=True):
        r = d["congestion_ratio"]
        lvl = ("CRITICAL" if r > 1.0
               else "HIGH" if r > 0.8
               else "MODERATE" if r > 0.5
               else "LOW")
        flag = " <<" if r > 1.0 else ""
        print(f"{d['segment_id']:<5} {d['name']:<25} {u:>4} > {v:<4} "
              f"{d['current_vehicles']:>5}/{d['capacity']:<5} "
              f"{r:>6.2f}  {lvl:<10}{flag}")
        if r > 1.0:
            congested_names.append(d["name"])

    print(f"\n  Congested roads ({len(congested_names)}): "
          + ", ".join(congested_names))

    # ── 2. Route comparisons ──────────────────────────────────
    pairs = [
        ("J01", "J09", "Central Station > Ring Road East"),
        ("J10", "J14", "Ring Road West > Airport"),
        ("J03", "J06", "Market Circle > Industrial Area"),
    ]

    routes_diverged = 0

    for start, end, label in pairs:
        print(f"\n{'=' * 72}")
        print(f"  ROUTE: {label}  ({start} > {end})")
        print("=" * 72)

        short = get_shortest_distance_route(G, start, end)
        opt   = get_optimal_route(G, start, end)

        print(f"\n  [Shortest Distance]")
        print(f"    Path:     {' > '.join(short['path'])}")
        print(f"    Distance: {short['total_distance_km']} km")

        print(f"\n  [Congestion-Optimized]")
        print(f"    Path:     {' > '.join(opt['path'])}")
        print(f"    Distance: {opt['total_distance_km']} km")
        print(f"    Cost:     {opt['total_cost']}")
        print(f"    Est time: {opt['estimated_time_min']:.1f} min")

        if short["path"] != opt["path"]:
            routes_diverged += 1
            print(f"\n    >> CONGESTION CHANGED THE ROUTE")
        else:
            print(f"\n    -- Same route (shortest path is also least congested)")

    # ── 3. Emergency routing ──────────────────────────────────
    print(f"\n{'=' * 72}")
    print("  EMERGENCY ROUTE: J08 (Ring Road South) > J04 (Hospital)")
    print("=" * 72)

    emerg = get_emergency_route(G, "J08", "J04")
    print(f"\n  Path:     {' > '.join(emerg['path'])}")
    print(f"  Est time: {emerg['estimated_time_min']:.1f} min")
    for s in emerg["segments"]:
        print(f"    {s['from']:>4} > {s['to']:<4}  {s['name']:<25} "
              f"cong={s['congestion_ratio']:.2f}  "
              f"t={s['travel_time_min']:.2f} min")

    # ── 4. Blocked-road avoidance ─────────────────────────────
    print(f"\n{'=' * 72}")
    print("  BLOCKED ROAD TEST: block IT Corridor (S04, J01 > J13)")
    print("=" * 72)

    # Block S04
    for u, v, d in G.edges(data=True):
        if d["segment_id"] == "S04":
            d["blocked"] = True
            print(f"\n  Blocked: {d['name']} ({u} > {v})")
            break

    blk   = get_optimal_route(G, "J01", "J13", avoid_blocked=True)
    noblk = get_optimal_route(G, "J01", "J13", avoid_blocked=False)

    print(f"\n  [Avoiding blocked roads]")
    print(f"    Path:     {' > '.join(blk['path'])}")
    print(f"    Distance: {blk['total_distance_km']} km")

    print(f"\n  [Ignoring blocked status]")
    print(f"    Path:     {' > '.join(noblk['path'])}")
    print(f"    Distance: {noblk['total_distance_km']} km")

    if blk["path"] != noblk["path"]:
        print(f"\n    >> BLOCKED-ROAD AVOIDANCE WORKS — route was diverted")
    else:
        print(f"\n    -- Paths identical (block had no effect)")

    # ── Summary ───────────────────────────────────────────────
    print(f"\n{'=' * 72}")
    print(f"  SUMMARY")
    print(f"    Junctions:        {G.number_of_nodes()}")
    print(f"    Road segments:    {G.number_of_edges()}")
    print(f"    Congested roads:  {len(congested_names)}")
    print(f"    Route pairs diverged by congestion: "
          f"{routes_diverged}/{len(pairs)}")
    print("=" * 72)


if __name__ == "__main__":
    main()

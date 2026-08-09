"""
Verification script for Step 2 (Signal Timing) and Step 3 (Emergency Corridor).

Run from the traffic_optimizer/ directory:
    python test_step2_3.py
"""
import os
import sys
import json
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))

from routing import create_graph
from signals import compute_default_signal_state, optimize_signal_timing
from corridor import (
    create_corridor,
    activate_corridor,
    advance_corridor,
    reroute_corridor,
)

SEP = "=" * 72


def load_data():
    seg = pd.read_csv(os.path.join(BASE_DIR, "data", "road_segments.csv"))
    seg.columns = seg.columns.str.strip()
    jdf = pd.read_csv(os.path.join(BASE_DIR, "data", "junctions.csv"))
    jdf.columns = jdf.columns.str.strip()
    return seg, jdf


def test_signals(G, jdf):
    """Step 2: signal timing optimization."""
    print(f"\n{SEP}")
    print("  STEP 2 — SIGNAL TIMING OPTIMIZATION")
    print(SEP)

    jid = "J01"  # Central Station — 6 approaches, high congestion

    # ── 1. Default state ──────────────────────────────────────
    default = compute_default_signal_state(G, jid, jdf)
    print(f"\n  [1] Default signal state for {jid} ({default['junction_name']})")
    print(f"      Mode: {default['mode']}")
    print(f"      Total cycle: {default['total_cycle_sec']}s")
    for p in default["phases"]:
        print(f"        {p['approach']:<45} green={p['green_time_sec']}s  "
              f"cong={p['congestion_ratio']:.2f}")

    # ── 2. Optimize ───────────────────────────────────────────
    optimized, explanation = optimize_signal_timing(G, jid, jdf)
    print(f"\n  [2] Optimized recommendation for {jid}")
    print(f"      Mode: {optimized['mode']}")
    print(f"      Total cycle: {optimized['total_cycle_sec']}s")
    for p in optimized["phases"]:
        print(f"        {p['approach']:<45} green={p['green_time_sec']}s  "
              f"cong={p['congestion_ratio']:.2f}")
    print(f"\n      Explanation: {explanation}")

    # ── 3. Verify timings changed ─────────────────────────────
    default_greens = [p["green_time_sec"] for p in default["phases"]]
    opt_greens     = [p["green_time_sec"] for p in optimized["phases"]]
    changed = default_greens != opt_greens
    print(f"\n      Timings changed from default? {'YES' if changed else 'NO'}")

    # Check that congested approaches got more green time
    max_cong_idx = max(range(len(optimized["phases"])),
                       key=lambda i: optimized["phases"][i]["congestion_ratio"])
    max_green_idx = max(range(len(optimized["phases"])),
                        key=lambda i: optimized["phases"][i]["green_time_sec"])
    print(f"      Most congested approach got most green? "
          f"{'YES' if max_cong_idx == max_green_idx else 'NO'}")

    # ── 4. Activate (simulated) ───────────────────────────────
    signal_store = {}
    for node in G.nodes:
        st = compute_default_signal_state(G, node, jdf)
        if st:
            signal_store[node] = st

    old_mode = signal_store[jid]["mode"]
    signal_store[jid] = optimized  # Apply
    new_mode = signal_store[jid]["mode"]

    print(f"\n  [3] Activate: mode changed {old_mode} -> {new_mode}")
    print(f"      Signal state for {jid} is now OPTIMIZED")

    # ── 5. Error handling ─────────────────────────────────────
    bad, msg = optimize_signal_timing(G, "INVALID_ID", jdf)
    print(f"\n  [4] Invalid junction test: "
          f"{'PASS (returned None + message)' if bad is None else 'FAIL'}")

    return signal_store


def test_corridor(G, jdf, signal_store):
    """Step 3: emergency corridor."""
    print(f"\n\n{SEP}")
    print("  STEP 3 — DYNAMIC EMERGENCY CORRIDOR")
    print(SEP)

    # ── 1. Create corridor ────────────────────────────────────
    print(f"\n  [1] Creating emergency corridor: J08 (Ring Road South) -> J04 (Hospital)")
    corridor = create_corridor(G, "ambulance", "J08", "J04", "high", jdf)

    cid = corridor["id"]
    print(f"      Corridor ID:    {cid}")
    print(f"      Status:         {corridor['status']}")
    print(f"      Vehicle:        {corridor['vehicle_type']}")
    print(f"      Path:           {' -> '.join(corridor['path'])}")
    print(f"      Emergency ETA:  {corridor['emergency_eta_min']} min")
    print(f"      Normal ETA:     {corridor['normal_eta_min']} min")
    print(f"      Time saved:     {corridor['time_saved_min']} min")

    print(f"\n      Junction states:")
    for js in corridor["junctions"]:
        sig = js["signal_recommendation"]
        sig_info = ""
        if sig:
            emerg_phases = [p for p in sig["phases"] if p.get("priority") == "EMERGENCY"]
            if emerg_phases:
                sig_info = f" | EMERGENCY green={emerg_phases[0]['green_time_sec']}s"
        print(f"        {js['junction_id']} ({js['junction_name']:<30}) "
              f"status={js['status']:<12}{sig_info}")

    # ── 2. Activate corridor ──────────────────────────────────
    print(f"\n  [2] Activating corridor {cid}...")
    activated = activate_corridor(cid, signal_store)
    print(f"      Status: {activated['status']}")

    print(f"\n      Junction states after activation:")
    for js in activated["junctions"]:
        print(f"        {js['junction_id']} -> {js['status']}")

    # Check signals were updated
    first_jid = corridor["path"][1]  # First junction AFTER origin
    sig_mode = signal_store.get(first_jid, {}).get("mode", "?")
    print(f"\n      Signal at {first_jid} mode: {sig_mode}")
    print(f"      Signal push verified? "
          f"{'YES' if sig_mode == 'emergency' else 'NO'}")

    # ── 3. Advance (simulate progress) ────────────────────────
    print(f"\n  [3] Simulating vehicle progress...")
    for step in range(len(corridor["path"])):
        result = advance_corridor(cid, signal_store)
        pos = result.get("current_position_index", "?")
        status = result.get("status", "?")
        cur_jid = corridor["path"][min(pos, len(corridor["path"]) - 1)]
        statuses = " | ".join(
            f"{js['junction_id']}:{js['status'][:3]}"
            for js in result.get("junctions", [])
        )
        print(f"      Step {step + 1}: pos={pos} ({cur_jid}) "
              f"corridor={status}  [{statuses}]")
        if status == "COMPLETED":
            break

    print(f"      Final status: {result.get('status')}")

    # ── 4. Reroute test ───────────────────────────────────────
    print(f"\n  [4] Reroute test: creating new corridor, then blocking a segment")

    # Fresh graph for reroute test
    seg2 = pd.read_csv(os.path.join(BASE_DIR, "data", "road_segments.csv"))
    seg2.columns = seg2.columns.str.strip()
    G2 = create_graph(seg2)

    corridor2 = create_corridor(G2, "fire", "J01", "J14", "high", jdf)
    cid2 = corridor2["id"]
    print(f"      New corridor {cid2}: {' -> '.join(corridor2['path'])}")
    print(f"      ETA: {corridor2['emergency_eta_min']} min")

    # Activate and advance one step
    activate_corridor(cid2, signal_store)
    advance_corridor(cid2, signal_store)
    cur_pos = corridor2["current_position_index"]
    print(f"      Advanced to position {cur_pos} ({corridor2['path'][cur_pos]})")

    # Block a segment on the current route
    # Find a segment that's on the route
    path2 = corridor2["path"]
    blocked_seg = None
    for i in range(cur_pos, len(path2) - 1):
        u, v = path2[i], path2[i + 1]
        edge = G2[u][v] if G2.has_edge(u, v) else None
        if edge:
            blocked_seg = edge.get("segment_id")
            break

    if blocked_seg:
        print(f"      Blocking segment {blocked_seg} on the route...")
        rerouted = reroute_corridor(cid2, G2, blocked_seg, jdf, signal_store)

        if "error" in rerouted:
            print(f"      Reroute error: {rerouted['error']}")
        else:
            print(f"      New path:  {' -> '.join(rerouted['path'])}")
            print(f"      New ETA:   {rerouted['emergency_eta_min']} min")
            print(f"      Reason:    {rerouted.get('reroute_reason', '?')}")
            changed = path2 != rerouted["path"]
            print(f"      Route changed? {'YES' if changed else 'NO'}")
    else:
        print(f"      Could not find a segment to block on route.")

    # ── 5. Error handling ─────────────────────────────────────
    print(f"\n  [5] Error handling tests:")
    from corridor import get_corridor
    bad = get_corridor("NONEXISTENT")
    print(f"      Invalid corridor ID: "
          f"{'PASS' if 'error' in bad else 'FAIL'}")

    bad2 = create_corridor(G2, "ambulance", "INVALID", "J04", "high", jdf)
    print(f"      Invalid junction:    "
          f"{'PASS' if 'error' in bad2 else 'FAIL'}")


def main():
    seg_df, jdf = load_data()
    G = create_graph(seg_df)

    print(SEP)
    print("  SMART TRAFFIC FLOW OPTIMIZER — Steps 2 & 3 Verification")
    print(SEP)
    print(f"  Graph: {G.number_of_nodes()} junctions, "
          f"{G.number_of_edges()} segments")

    signal_store = test_signals(G, jdf)
    test_corridor(G, jdf, signal_store)

    print(f"\n{SEP}")
    print("  ALL TESTS COMPLETED")
    print(SEP)


if __name__ == "__main__":
    main()

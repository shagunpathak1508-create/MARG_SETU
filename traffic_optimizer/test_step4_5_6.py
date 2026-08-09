"""
Verification script for Steps 4, 5, and 6.

    python test_step4_5_6.py
"""
import os, sys, json
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))

from routing import create_graph
from comparison import compute_comparison
from diversion import recommend_diversion, activate_diversion
from simulation import run_simulation
from signals import compute_default_signal_state

SEP = "=" * 72


def load():
    s = pd.read_csv(os.path.join(BASE_DIR, "data", "road_segments.csv"))
    j = pd.read_csv(os.path.join(BASE_DIR, "data", "junctions.csv"))
    s.columns = s.columns.str.strip()
    j.columns = j.columns.str.strip()
    return s, j


# -- Step 4: Before/After -----------------------------------------
def test_comparison(seg, jdf):
    print(f"\n{SEP}")
    print("  STEP 4 -- BEFORE / AFTER COMPARISON")
    print(SEP)

    G = create_graph(seg)
    result = compute_comparison(G, jdf)

    b = result["before"]
    a = result["after"]
    imp = result["improvements"]

    print(f"\n  {'Metric':<30} {'Before':>10} {'After':>10} {'Change':>10}")
    print(f"  {'-'*62}")

    rows = [
        ("Avg Congestion %",        "avg_congestion_pct",    "%"),
        ("Avg Speed (km/h)",        "avg_speed_kmh",         "km/h"),
        ("Avg Waiting Time (sec)",  "avg_waiting_time_sec",  "s"),
        ("Avg Queue Length (veh)",   "avg_queue_length",      "veh"),
        ("Congested Roads",         "total_congested_roads",  ""),
        ("Emergency ETA (min)",     "emergency_eta_min",      "min"),
    ]
    all_improved = True
    for label, key, unit in rows:
        bv = b.get(key, 0)
        av = a.get(key, 0)
        pct = imp.get(key, {}).get("improvement_pct", 0)
        if key == "avg_speed_kmh":
            arrow = "[+]" if pct > 0 else "[-]"
        else:
            arrow = "[+]" if pct > 0 else ("[-]" if pct < 0 else "[=]")
        print(f"  {label:<30} {bv:>10} {av:>10} {pct:>+8.1f}% {arrow}")
        if key != "avg_speed_kmh" and av >= bv and bv > 0:
            all_improved = False
        if key == "avg_speed_kmh" and av <= bv and bv > 0:
            all_improved = False

    print(f"\n  Optimization: {result['optimization_applied']}")
    print(f"  After-metrics meaningfully better? {'YES' if all_improved else 'PARTIAL'}")


# -- Step 5: Diversion ---------------------------------------------
def test_diversion(seg, jdf):
    print(f"\n\n{SEP}")
    print("  STEP 5 -- DIVERSION / ROAD CLOSURE")
    print(SEP)

    G = create_graph(seg)

    # Block IT Corridor (S04) -- highly congested arterial
    blocked = "S04"
    print(f"\n  [1] Recommending diversion for blocked segment {blocked}...")

    rec = recommend_diversion(G, blocked, jdf)
    bs = rec["blocked_segment"]
    dv = rec["diversion"]
    im = rec["impact"]

    print(f"      Blocked: {bs['name']} ({bs['from_junction']} -> {bs['to_junction']})")
    print(f"      Original: {bs['original_distance_km']} km, "
          f"{bs['original_travel_time_min']} min")
    print(f"\n      Diversion path: {' -> '.join(dv['path'])}")
    print(f"      Diversion: {dv['distance_km']} km, {dv['travel_time_min']} min")
    print(f"      Additional delay: {im['additional_delay_min']} min")
    print(f"      Distance increase: {im['distance_increase_km']} km")

    print(f"\n      Affected junctions:")
    for aj in im["affected_junctions"]:
        print(f"        {aj['junction_id']}  congestion={aj['current_max_congestion']:.2f}"
              f"  impact={aj['expected_impact']}")

    # Activate
    div_id = rec["diversion_id"]
    print(f"\n  [2] Activating diversion {div_id}...")

    signal_store = {}
    for jid in G.nodes:
        st = compute_default_signal_state(G, jid, jdf)
        if st:
            signal_store[jid] = st

    activated = activate_diversion(div_id, signal_store)
    print(f"      Status: {activated['status']}")

    # Check signals updated for diversion junctions
    updated_junctions = [r["junction_id"] for r in rec.get("signal_recommendations", [])]
    signals_changed = sum(1 for jid in updated_junctions
                          if signal_store.get(jid, {}).get("mode") == "optimized")
    print(f"      Signals updated at {signals_changed}/{len(updated_junctions)} junctions")

    # Also test a second road closure
    print(f"\n  [3] Second test: blocking S24 (Southern Ring Road)...")
    rec2 = recommend_diversion(G, "S24", jdf)
    dv2 = rec2["diversion"]
    im2 = rec2["impact"]
    print(f"      Diversion path: {' -> '.join(dv2['path'])}")
    print(f"      Additional delay: {im2['additional_delay_min']} min")

    # Error test
    print(f"\n  [4] Error test: invalid segment...")
    err = recommend_diversion(G, "INVALID", jdf)
    print(f"      Result: {'PASS (error returned)' if 'error' in err else 'FAIL'}")


# -- Step 6: Simulation --------------------------------------------
def test_simulation(seg, jdf):
    print(f"\n\n{SEP}")
    print("  STEP 6 -- SCENARIO SIMULATION")
    print(SEP)

    scenarios = [
        {
            "name": "Heavy congestion + road closure",
            "params": {
                "traffic_multiplier": 1.5,
                "road_closure": "S04",
            },
        },
        {
            "name": "Normal traffic + incident on Southern Ring",
            "params": {
                "incident_segment": "S24",
                "incident_severity": 2.5,
            },
        },
        {
            "name": "Light traffic (off-peak)",
            "params": {
                "traffic_multiplier": 0.5,
            },
        },
    ]

    prev_before_cong = None
    results_differ = True

    for i, sc in enumerate(scenarios, 1):
        print(f"\n  [{i}] Scenario: {sc['name']}")
        print(f"      Params: {json.dumps(sc['params'])}")

        result = run_simulation(seg, jdf, sc["params"])
        b = result["before"]
        a = result["after"]
        imp = result["improvements"]

        print(f"\n      {'Metric':<28} {'Before':>8} {'After':>8} {'Change':>8}")
        print(f"      {'-'*56}")
        for label, key in [("Congestion %", "avg_congestion_pct"),
                           ("Speed (km/h)", "avg_speed_kmh"),
                           ("Wait time (s)", "avg_waiting_time_sec"),
                           ("Queue length", "avg_queue_length"),
                           ("Congested roads", "total_congested_roads"),
                           ("Emergency ETA (min)", "emergency_eta_min")]:
            bv = b.get(key, 0)
            av = a.get(key, 0)
            pct = imp.get(key, {}).get("improvement_pct", 0)
            print(f"      {label:<28} {bv:>8} {av:>8} {pct:>+7.1f}%")

        # Check that different scenarios produce different numbers
        if prev_before_cong is not None and b["avg_congestion_pct"] == prev_before_cong:
            results_differ = False
        prev_before_cong = b["avg_congestion_pct"]

    print(f"\n  Scenarios produce different results? "
          f"{'YES' if results_differ else 'NO'}")


def main():
    seg, jdf = load()
    print(SEP)
    print("  SMART TRAFFIC FLOW OPTIMIZER -- Steps 4, 5, 6 Verification")
    print(SEP)

    test_comparison(seg, jdf)
    test_diversion(seg, jdf)
    test_simulation(seg, jdf)

    print(f"\n{SEP}")
    print("  ALL TESTS COMPLETED")
    print(SEP)


if __name__ == "__main__":
    main()

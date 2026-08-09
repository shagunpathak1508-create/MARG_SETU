"""
Smart Traffic Flow Optimizer — Flask API server.

Endpoints
---------
GET  /traffic                     Road-segment traffic status
GET  /junctions                   Junction list with coordinates
GET  /route/<s>/<e>               Congestion-optimized route
GET  /route/compare/<s>/<e>       Compare shortest vs optimized route
GET  /schedule                    Vehicle batch scheduling
GET  /emergency                   Legacy emergency routing
GET  /predict/<seg>               AI traffic prediction

GET  /api/signals                 Signal state (all or ?junction_id=)
POST /api/signals/optimize        Recommend optimized timing
POST /api/signals/activate        Apply optimized timing

POST /api/emergency/create        Create emergency corridor
POST /api/emergency/<id>/activate Activate corridor + signals
GET  /api/emergency/<id>          Corridor status
POST /api/emergency/<id>/advance  Simulate vehicle progress
POST /api/emergency/<id>/reroute  Reroute around blocked segment
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import os
import sys

# Make sure src/ is importable regardless of working directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))

from routing import (
    create_graph,
    get_optimal_route,
    get_shortest_distance_route,
    get_emergency_route,
)
from src_scheduling import generate_schedule
from emergency import is_emergency
from prediction import train_model, predict_traffic
from traffic_analysis import calculate_congestion_level
from signals import (
    compute_default_signal_state,
    optimize_signal_timing,
)
from corridor import (
    create_corridor,
    activate_corridor,
    get_corridor,
    advance_corridor,
    reroute_corridor,
)

app = Flask(__name__)
CORS(app)  # Allow browser requests from any origin (needed for frontend)

# ── Data paths ───────────────────────────────────────────────
JUNCTIONS_PATH = os.path.join(BASE_DIR, "data", "junctions.csv")
SEGMENTS_PATH  = os.path.join(BASE_DIR, "data", "road_segments.csv")

# Train prediction model once at startup
_prediction_model = train_model()

# In-memory signal state  (junction_id → signal dict)
_signal_states = {}


# ── Helpers ──────────────────────────────────────────────────
def load_junctions():
    df = pd.read_csv(JUNCTIONS_PATH)
    df.columns = df.columns.str.strip()
    return df


def load_segments():
    df = pd.read_csv(SEGMENTS_PATH)
    df.columns = df.columns.str.strip()
    return df


# ── 1.  GET /traffic ─────────────────────────────────────────
@app.route("/traffic")
def traffic():
    """Return per-segment traffic status."""
    seg = load_segments()

    records = []
    for _, row in seg.iterrows():
        v = int(row.get("current_vehicles", 0))
        c = int(row.get("capacity", 100))
        ratio = v / c if c > 0 else 0

        records.append({
            "segment_id":       str(row.get("segment_id", "")),
            "road":             str(row.get("name", "Unknown")),
            "from_junction":    str(row.get("from_junction", "")),
            "to_junction":      str(row.get("to_junction", "")),
            "vehicle_count":    v,
            "capacity":         c,
            "congestion_ratio": round(ratio, 4),
            "congestion_level": calculate_congestion_level(ratio),
            "congestion_status": (
                "Congested" if ratio > 1.0
                else ("Moderate" if ratio > 0.7 else "Normal")
            ),
            "speed_limit_kmh":  int(row.get("speed_limit_kmh", 40)),
            "road_type":        str(row.get("road_type", "collector")),
            "distance_km":      float(row.get("distance_km", 0)),
            "blocked":          str(row.get("blocked", "False")).strip().lower()
                                in ("true", "1", "yes"),
        })

    return jsonify(records)


# ── 1b. GET /junctions ───────────────────────────────────────
@app.route("/junctions")
def junctions():
    """Return junction list with coordinates."""
    jdf = load_junctions()

    records = []
    for _, row in jdf.iterrows():
        records.append({
            "junction_id": str(row.get("junction_id", "")),
            "name":        str(row.get("name", "Unknown")),
            "lat":         float(row.get("lat", 0)),
            "lng":         float(row.get("lng", 0)),
        })

    return jsonify(records)


# ── 2.  GET /route/<start>/<end> ─────────────────────────────
@app.route("/route/<start>/<end>")
def route(start, end):
    """Congestion-optimized route between two junctions."""
    G = create_graph(load_segments())

    if start not in G.nodes or end not in G.nodes:
        return jsonify({
            "error": f"Junction '{start}' or '{end}' not found.",
            "available": sorted(list(G.nodes)),
        }), 404

    if start == end:
        return jsonify({"path": [start], "total_cost": 0,
                         "total_distance_km": 0, "estimated_time_min": 0})

    result = get_optimal_route(G, start, end, avoid_blocked=True)
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)


# ── 2b. GET /route/compare/<start>/<end> ─────────────────────
@app.route("/route/compare/<start>/<end>")
def route_compare(start, end):
    """Compare shortest-distance vs congestion-optimized routes."""
    G = create_graph(load_segments())

    if start not in G.nodes or end not in G.nodes:
        return jsonify({
            "error": f"Junction '{start}' or '{end}' not found.",
            "available": sorted(list(G.nodes)),
        }), 404

    if start == end:
        same = {"path": [start], "total_distance_km": 0,
                "estimated_time_min": 0}
        return jsonify({"shortest_distance": same,
                         "congestion_optimized": same})

    shortest  = get_shortest_distance_route(G, start, end)
    optimized = get_optimal_route(G, start, end)

    return jsonify({
        "shortest_distance":    shortest,
        "congestion_optimized": optimized,
    })


# ── 3.  GET /schedule ────────────────────────────────────────
@app.route("/schedule")
def schedule():
    """Vehicle batch scheduling per road segment."""
    seg = load_segments()

    all_batches = []
    batch_num   = 1

    for _, row in seg.iterrows():
        road     = str(row.get("name", "Unknown"))
        vehicles = int(row.get("current_vehicles", 0))
        capacity = int(row.get("capacity", 100))

        # Use capacity-aware batch size (capped at 50 for readability)
        road_batches = generate_schedule(vehicles,
                                         batch_size=min(capacity, 50))
        for b in road_batches:
            all_batches.append({
                "batch":       f"Batch {batch_num}",
                "road":        road,
                "vehicles":    b["vehicles"],
                "token_start": b["token_start"],
                "token_end":   b["token_end"],
                "time_slot":   b["time_slot"],
            })
            batch_num += 1

    return jsonify({"batches": all_batches})


# ── 4.  GET /emergency ───────────────────────────────────────
@app.route("/emergency")
def emergency():
    """
    Emergency vehicle priority routing.

    Query params (all optional):
        vehicle_type  – ambulance | police | fire   (default: ambulance)
        origin        – junction id                  (default: first node)
        destination   – junction id                  (default: last node)
    """
    G = create_graph(load_segments())

    vehicle_type = request.args.get("vehicle_type", "ambulance")
    origin       = request.args.get("origin", None)
    destination  = request.args.get("destination", None)

    if not is_emergency(vehicle_type):
        return jsonify({"message": "Vehicle type is not classified as emergency."})

    # Defaults when caller omits origin / destination
    nodes = sorted(list(G.nodes))
    origin      = origin      or nodes[0]
    destination = destination or nodes[-1]

    if origin not in G.nodes or destination not in G.nodes:
        return jsonify({
            "error": f"Junction '{origin}' or '{destination}' not found.",
            "available": nodes,
        }), 404

    result = get_emergency_route(G, origin, destination)
    if "error" in result:
        return jsonify(result), 500

    result["vehicle_type"] = vehicle_type.capitalize()
    result["origin"]       = origin
    result["destination"]  = destination
    result["eta"]          = f"{result['estimated_time_min']:.1f} min"
    return jsonify(result)


# ── 5.  GET /predict/<segment_id_or_name> ────────────────────
@app.route("/predict/<path:segment_id>")
def predict(segment_id):
    """AI traffic prediction for a road segment (by ID or name)."""
    seg = load_segments()

    matches = seg[
        (seg["segment_id"].str.strip() == segment_id.strip()) |
        (seg["name"].str.strip() == segment_id.strip())
    ]
    if matches.empty:
        return jsonify({"error": f"Road segment '{segment_id}' not found."}), 404

    row     = matches.iloc[0]
    current = int(row.get("current_vehicles", 0))
    pred    = predict_traffic(_prediction_model, current)

    return jsonify({
        "segment_id": str(row.get("segment_id", "")),
        "road":       str(row.get("name", "")),
        "current":    current,
        "predicted":  pred,
    })



# ═══════════════════════════════════════════════════════════════
#  STEP 2 — Signal Timing Endpoints
# ═══════════════════════════════════════════════════════════════

def _ensure_signal_states():
    """Lazily populate _signal_states with defaults for every junction."""
    if _signal_states:
        return
    G   = create_graph(load_segments())
    jdf = load_junctions()
    for jid in sorted(G.nodes):
        st = compute_default_signal_state(G, jid, jdf)
        if st:
            _signal_states[jid] = st


# ── GET /api/signals ─────────────────────────────────────────
@app.route("/api/signals")
def api_signals():
    """
    Return signal state.  Optionally filter by ?junction_id=J01.
    """
    _ensure_signal_states()

    jid = request.args.get("junction_id")
    if jid:
        st = _signal_states.get(jid)
        if not st:
            return jsonify({"error": f"Junction '{jid}' not found."}), 404
        return jsonify(st)

    return jsonify(list(_signal_states.values()))


# ── POST /api/signals/optimize ───────────────────────────────
@app.route("/api/signals/optimize", methods=["POST"])
def api_signals_optimize():
    """
    Return recommended signal timings for a junction.
    Body: { "junction_id": "J01" }
    Does NOT apply the recommendation yet.
    """
    body = request.get_json(silent=True) or {}
    jid  = body.get("junction_id")
    if not jid:
        return jsonify({"error": "Missing 'junction_id' in request body."}), 400

    G   = create_graph(load_segments())
    jdf = load_junctions()

    if jid not in G.nodes:
        return jsonify({"error": f"Junction '{jid}' not found."}), 404

    state, explanation = optimize_signal_timing(G, jid, jdf)
    if state is None:
        return jsonify({"error": explanation}), 400

    return jsonify({
        "recommendation": state,
        "explanation":     explanation,
    })


# ── POST /api/signals/activate ───────────────────────────────
@app.route("/api/signals/activate", methods=["POST"])
def api_signals_activate():
    """
    Apply the optimized timing to simulated state.
    Body: { "junction_id": "J01" }
    """
    _ensure_signal_states()

    body = request.get_json(silent=True) or {}
    jid  = body.get("junction_id")
    if not jid:
        return jsonify({"error": "Missing 'junction_id' in request body."}), 400

    G   = create_graph(load_segments())
    jdf = load_junctions()

    if jid not in G.nodes:
        return jsonify({"error": f"Junction '{jid}' not found."}), 404

    state, explanation = optimize_signal_timing(G, jid, jdf)
    if state is None:
        return jsonify({"error": explanation}), 400

    _signal_states[jid] = state
    return jsonify({
        "applied":     state,
        "explanation": explanation,
    })


# ═══════════════════════════════════════════════════════════════
#  STEP 3 — Emergency Corridor Endpoints
# ═══════════════════════════════════════════════════════════════

# ── POST /api/emergency/create ───────────────────────────────
@app.route("/api/emergency/create", methods=["POST"])
def api_emergency_create():
    """
    Create a proposed emergency corridor.
    Body: { "vehicle_type": "ambulance",
            "origin": "J08", "destination": "J04",
            "priority_level": "high" }
    """
    body = request.get_json(silent=True) or {}
    vtype = body.get("vehicle_type")
    orig  = body.get("origin")
    dest  = body.get("destination")
    prio  = body.get("priority_level", "high")

    if not all([vtype, orig, dest]):
        return jsonify({
            "error": "Missing required fields: vehicle_type, origin, destination."
        }), 400

    if not is_emergency(vtype):
        return jsonify({"error": f"'{vtype}' is not a recognized emergency vehicle type."}), 400

    G   = create_graph(load_segments())
    jdf = load_junctions()

    if orig not in G.nodes or dest not in G.nodes:
        return jsonify({
            "error": f"Junction '{orig}' or '{dest}' not found.",
            "available": sorted(list(G.nodes)),
        }), 404

    result = create_corridor(G, vtype, orig, dest, prio, jdf)
    if "error" in result:
        return jsonify(result), 500

    return jsonify(result), 201


# ── POST /api/emergency/<id>/activate ────────────────────────
@app.route("/api/emergency/<corridor_id>/activate", methods=["POST"])
def api_emergency_activate(corridor_id):
    """Activate corridor and push signal priorities."""
    _ensure_signal_states()
    result = activate_corridor(corridor_id, _signal_states)
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)


# ── GET /api/emergency/<id> ──────────────────────────────────
@app.route("/api/emergency/<corridor_id>")
def api_emergency_get(corridor_id):
    """Get current corridor state."""
    result = get_corridor(corridor_id)
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)


# ── POST /api/emergency/<id>/advance ─────────────────────────
@app.route("/api/emergency/<corridor_id>/advance", methods=["POST"])
def api_emergency_advance(corridor_id):
    """Advance the emergency vehicle one step."""
    _ensure_signal_states()
    result = advance_corridor(corridor_id, _signal_states)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


# ── POST /api/emergency/<id>/reroute ─────────────────────────
@app.route("/api/emergency/<corridor_id>/reroute", methods=["POST"])
def api_emergency_reroute(corridor_id):
    """
    Reroute around a blocked segment.
    Body: { "blocked_segment": "S04" }
    """
    body = request.get_json(silent=True) or {}
    seg  = body.get("blocked_segment")
    if not seg:
        return jsonify({"error": "Missing 'blocked_segment' in request body."}), 400

    G   = create_graph(load_segments())
    jdf = load_junctions()
    _ensure_signal_states()

    result = reroute_corridor(corridor_id, G, seg, jdf, _signal_states)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


# ── Run ──────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)
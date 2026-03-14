from flask import Flask, jsonify
from flask_cors import CORS
import pandas as pd
import os
import sys

# Make sure src/ is importable regardless of working directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))

from routing import create_graph, get_best_route
from src_scheduling import generate_schedule
from emergency import is_emergency
from prediction import train_model, predict_traffic

app = Flask(__name__)
CORS(app)  # Allow browser requests from any origin (needed for frontend)

DATA_PATH = os.path.join(BASE_DIR, "data", "traffic_data.csv")

# Train prediction model once at startup
_prediction_model = train_model()

# ── Helpers ──────────────────────────────────────────────────
def load_df():
    df = pd.read_csv(DATA_PATH)
    df.columns = df.columns.str.strip()
    return df

def get_congestion_status(vehicles, capacity):
    """Return 'Congested' if load > 100%, else 'Normal'."""
    if capacity <= 0:
        return "Unknown"
    return "Congested" if vehicles > capacity else "Normal"


# ── 1.  GET /traffic ─────────────────────────────────────────
@app.route("/traffic")
def traffic():
    df = load_df()

    records = []
    for _, row in df.iterrows():
        v = int(row.get("vehicles", row.get("vehicle_count", 0)))
        c = int(row.get("capacity", 100))
        records.append({
            "road":              str(row.get("road", row.get("name", "Unknown"))),
            "vehicle_count":     v,
            "capacity":          c,
            "congestion_status": get_congestion_status(v, c),
        })

    return jsonify(records)


# ── 2.  GET /route/<start>/<end> ─────────────────────────────
@app.route("/route/<start>/<end>")
def route(start, end):
    df = load_df()
    G  = create_graph(df)  # congestion-weighted graph from live data

    # Validate that start and end exist as nodes
    if start not in G.nodes or end not in G.nodes:
        return jsonify({
            "error": f"Road '{start}' or '{end}' not found. Available: {list(G.nodes)}"
        }), 404

    if start == end:
        return jsonify({"path": [start], "cost": 0})

    try:
        import networkx as nx
        path = nx.shortest_path(G, source=start, target=end, weight="weight")
        cost = round(nx.shortest_path_length(G, source=start, target=end, weight="weight"), 4)
        return jsonify({"path": path, "cost": cost})
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500


# ── 3.  GET /schedule ────────────────────────────────────────
@app.route("/schedule")
def schedule():
    df = load_df()

    all_batches = []
    batch_num   = 1

    for _, row in df.iterrows():
        road     = str(row.get("road", row.get("name", "Unknown")))
        vehicles = int(row.get("vehicles", row.get("vehicle_count", 0)))

        road_batches = generate_schedule(vehicles, batch_size=20)
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
    # Emergency uses static single-letter node graph (A-E)
    G = create_graph()  # no df → static fallback

    vehicle_type = "ambulance"
    priority     = is_emergency(vehicle_type)

    if not priority:
        return jsonify({"message": "No active emergency."})

    try:
        import networkx as nx
        path = nx.shortest_path(G, source="A", target="E", weight="weight")
        cost = nx.shortest_path_length(G, source="A", target="E", weight="weight")
        return jsonify({
            "vehicle_type": vehicle_type.capitalize(),
            "path":         path,
            "cost":         cost,
            "eta":          f"{cost * 2} min",
        })
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500


# ── 5.  GET /predict/<road> ──────────────────────────────────
@app.route("/predict/<path:road>")
def predict(road):
    df = load_df()

    # Find the row matching this road name
    matches = df[df["road"].str.strip() == road.strip()]
    if matches.empty:
        return jsonify({"error": f"Road '{road}' not found."}), 404

    row     = matches.iloc[0]
    current = int(row.get("vehicles", row.get("vehicle_count", 0)))
    pred    = predict_traffic(_prediction_model, current)

    return jsonify({
        "road":      road,
        "current":   current,
        "predicted": pred,
    })


# ── Run ──────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)
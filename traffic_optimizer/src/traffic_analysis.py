"""
Traffic analysis utilities.

Provides congestion-level classification used by the API and
the routing engine.  The legacy ``calculate_traffic_level``
function is kept for notebook compatibility.
"""
import pandas as pd


def load_data(filepath):
    """Load a CSV file into a DataFrame with stripped column names."""
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip()
    return df


def calculate_congestion_level(ratio):
    """
    Classify congestion from a vehicle-to-capacity *ratio*.

    Returns
    -------
    str
        One of ``'Low'``, ``'Moderate'``, ``'High'``, ``'Critical'``.
    """
    if ratio < 0.5:
        return "Low"
    if ratio <= 0.8:
        return "Moderate"
    if ratio <= 1.0:
        return "High"
    return "Critical"


# ── Legacy helper (kept for notebook / backward compat) ──────
def calculate_traffic_level(row):
    """Classify from a DataFrame row that has *vehicles* and *capacity*."""
    cap = row.get("capacity", row.get("capacity", 1))
    veh = row.get("vehicles", row.get("current_vehicles", 0))
    ratio = veh / cap if cap > 0 else 0
    return calculate_congestion_level(ratio)
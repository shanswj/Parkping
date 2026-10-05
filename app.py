from flask import Flask, render_template, jsonify, request
from pathlib import Path
import sqlite3
import json
import joblib
import pandas as pd

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "parkping.db"
MODEL_PATH = BASE_DIR / "model.joblib"
MODEL_META_PATH = BASE_DIR / "model_meta.json"

# Prototype parking bays. Coordinates are illustrative demo data, not official MBPP bay data.
DEMO_SPOTS = [
    {"id": "CHU-A17", "street": "Lebuh Chulia", "status": "occupied", "x": 24, "y": 38, "section": "Zone A"},
    {"id": "CHU-A18", "street": "Lebuh Chulia", "status": "available", "x": 38, "y": 30, "section": "Zone A"},
    {"id": "ARM-B04", "street": "Lebuh Armenian", "status": "occupied", "x": 60, "y": 58, "section": "Zone B"},
    {"id": "CAR-C11", "street": "Lebuh Carnarvon", "status": "available", "x": 72, "y": 28, "section": "Zone C"},
    {"id": "KIM-D02", "street": "Lebuh Kimberley", "status": "occupied", "x": 49, "y": 74, "section": "Zone D"},
]

def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = connect_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            spot_id TEXT NOT NULL,
            minutes INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'leaving_soon',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            points INTEGER NOT NULL DEFAULT 120,
            helped_drivers INTEGER NOT NULL DEFAULT 8
        )
    """)
    conn.execute("INSERT OR IGNORE INTO user_profile (id, points, helped_drivers) VALUES (1, 120, 8)")
    conn.commit()
    conn.close()

def active_pings():
    conn = connect_db()
    rows = conn.execute("SELECT * FROM pings WHERE status = 'leaving_soon' ORDER BY created_at DESC").fetchall()
    conn.close()
    return {row["spot_id"]: dict(row) for row in rows}

def get_spots():
    pings = active_pings()
    spots = []
    for original in DEMO_SPOTS:
        spot = dict(original)
        if spot["id"] in pings:
            spot["status"] = "leaving_soon"
            spot["minutes"] = pings[spot["id"]]["minutes"]
            spot["ping_id"] = pings[spot["id"]]["id"]
        spots.append(spot)
    return spots

@app.route("/")
def home():
    return render_template("index.html")

@app.get("/api/spots")
def api_spots():
    return jsonify(get_spots())

@app.get("/api/profile")
def api_profile():
    conn = connect_db()
    row = conn.execute("SELECT points, helped_drivers FROM user_profile WHERE id = 1").fetchone()
    conn.close()
    return jsonify(dict(row))

@app.post("/api/pings")
def create_ping():
    data = request.get_json(force=True)
    spot_id = data.get("spot_id")
    minutes = int(data.get("minutes", 3))

    if spot_id not in {s["id"] for s in DEMO_SPOTS}:
        return jsonify({"error": "Unknown parking spot"}), 400
    if minutes not in (0, 3, 5):
        return jsonify({"error": "Minutes must be 0, 3, or 5"}), 400

    conn = connect_db()
    conn.execute("UPDATE pings SET status='expired' WHERE spot_id=? AND status='leaving_soon'", (spot_id,))
    cursor = conn.execute(
        "INSERT INTO pings (spot_id, minutes, status) VALUES (?, ?, 'leaving_soon')",
        (spot_id, minutes),
    )
    conn.commit()
    ping_id = cursor.lastrowid
    conn.close()

    return jsonify({"message": "Ping created", "ping_id": ping_id}), 201

@app.patch("/api/pings/<int:ping_id>/complete")
def complete_ping(ping_id):
    conn = connect_db()
    row = conn.execute("SELECT * FROM pings WHERE id=?", (ping_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Ping not found"}), 404

    if row["status"] != "completed":
        conn.execute("UPDATE pings SET status='completed' WHERE id=?", (ping_id,))
        conn.execute("""
            UPDATE user_profile
            SET points = points + 10,
                helped_drivers = helped_drivers + 1
            WHERE id = 1
        """)
        conn.commit()

    conn.close()
    return jsonify({"message": "Spot marked available. 10 points awarded."})

@app.post("/api/predict")
def predict():
    """
    Predict occupancy probability from historical data.

    Why this endpoint exists:
    Frontend sends user choices -> Flask converts them to a DataFrame ->
    saved ML pipeline preprocesses them -> model returns a probability ->
    frontend turns the probability into an understandable recommendation.
    """
    if not MODEL_PATH.exists() or not MODEL_META_PATH.exists():
        return jsonify({
            "trained": False,
            "message": "Model has not been trained yet. Run: python ml/train_model.py"
        })

    payload = request.get_json(force=True)
    model = joblib.load(MODEL_PATH)
    meta = json.loads(MODEL_META_PATH.read_text(encoding="utf-8"))

    row = {}
    for feature in meta["features"]:
        row[feature] = payload.get(feature, meta.get("defaults", {}).get(feature))

    input_df = pd.DataFrame([row])
    probability_occupied = float(model.predict_proba(input_df)[0][1])
    availability = 1 - probability_occupied

    if availability >= 0.65:
        recommendation = "Good chance of finding parking"
    elif availability >= 0.40:
        recommendation = "Moderate availability — watch nearby pings"
    else:
        recommendation = "High demand — try another zone or wait for a ping"

    return jsonify({
        "trained": True,
        "occupied_probability": round(probability_occupied, 3),
        "availability_probability": round(availability, 3),
        "recommendation": recommendation
    })

if __name__ == "__main__":
    init_db()
    app.run(debug=True)

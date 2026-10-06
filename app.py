from flask import Flask, render_template, jsonify, request
from functools import lru_cache
from pathlib import Path
import os
import sqlite3
import json
import joblib
import pandas as pd

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "parkping.db"
MODEL_PATH = BASE_DIR / "model.joblib"
MODEL_META_PATH = BASE_DIR / "model_meta.json"

BAY_COUNT = 12  # how many bays the demo street shows

# Columns the app needs from the Kaggle CSV (names after clean_name()).
SPOT_COL = "parking_spot_id"
STATUS_COL = "occupancy_status"
TIME_COL = "timestamp"


def clean_name(name):
    return str(name).strip().lower().replace(" ", "_").replace("/", "_").replace("-", "_")


@lru_cache(maxsize=1)
def load_history():
    """
    Read the Kaggle CSV once and keep only what the app needs.
    Returns None when no CSV has been placed in data/ yet.
    """
    csv_files = sorted(DATA_DIR.glob("*.csv"))
    if not csv_files:
        return None

    df = pd.read_csv(csv_files[0])
    df.columns = [clean_name(c) for c in df.columns]
    df[TIME_COL] = pd.to_datetime(df[TIME_COL], errors="coerce")
    df = df.dropna(subset=[TIME_COL, SPOT_COL])
    df["hour"] = df[TIME_COL].dt.hour
    df["occupied"] = (df[STATUS_COL].astype(str).str.strip().str.lower() == "occupied").astype(int)
    return df[[TIME_COL, SPOT_COL, "hour", "occupied"]]


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def seed_bays(conn):
    """Each bay starts as occupied or free according to its most recent reading in the dataset."""
    df = load_history()
    if df is None:
        return
    latest = df.sort_values(TIME_COL).groupby(SPOT_COL).tail(1).sort_values(SPOT_COL).head(BAY_COUNT)
    for record in latest.itertuples(index=False):
        status = "occupied" if record.occupied else "free"
        conn.execute("INSERT INTO bays (id, status) VALUES (?, ?)", (int(getattr(record, SPOT_COL)), status))


def init_db():
    conn = connect_db()
    conn.execute("CREATE TABLE IF NOT EXISTS bays (id INTEGER PRIMARY KEY, status TEXT NOT NULL)")
    if conn.execute("SELECT COUNT(*) FROM bays").fetchone()[0] == 0:
        seed_bays(conn)
    conn.commit()
    conn.close()


def set_status(bay_id, new_status, required_status, error_message):
    """Change one bay, but only if it is currently in the state we expect."""
    conn = connect_db()
    changed = conn.execute(
        "UPDATE bays SET status=? WHERE id=? AND status=?", (new_status, bay_id, required_status)
    ).rowcount
    conn.commit()
    conn.close()
    if not changed:
        return jsonify({"error": error_message}), 409
    return jsonify({"id": bay_id, "status": new_status})


@app.route("/")
def home():
    return render_template("index.html")


@app.get("/api/bays")
def api_bays():
    conn = connect_db()
    rows = conn.execute("SELECT id, status FROM bays ORDER BY id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.post("/api/bays/<int:bay_id>/leave")
def leave_bay(bay_id):
    """A driver presses "I'm leaving": the bay is free straight away."""
    return set_status(bay_id, "free", "occupied", "That bay is already free")


@app.post("/api/bays/<int:bay_id>/park")
def park_in_bay(bay_id):
    """A driver takes a free bay."""
    return set_status(bay_id, "occupied", "free", "That bay is not free")


@app.post("/api/reset")
def reset_demo():
    """Put every bay back to its starting state from the dataset."""
    conn = connect_db()
    conn.execute("DELETE FROM bays")
    seed_bays(conn)
    conn.commit()
    conn.close()
    return jsonify({"message": "Bays reset from dataset"})


@app.get("/api/outlook")
def api_outlook():
    """How full parking usually is at each hour: share of dataset rows marked Occupied."""
    df = load_history()
    if df is None:
        return jsonify([])
    by_hour = df.groupby("hour")["occupied"].mean()
    return jsonify([{"hour": int(hour), "occupied_pct": round(share * 100)} for hour, share in by_hour.items()])


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
    # PORT lets the app move when 5000 is busy (e.g. MLflow UI also uses 5000).
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))

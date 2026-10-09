# ParkPing: a small Flask app that asks the saved model "how likely is this zone to be occupied?"
import os
import joblib
import pandas as pd
from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

# Find our own folder so the app works no matter where you start it from.
BASE = os.path.dirname(os.path.abspath(__file__))

# Load once, when the app starts: the trained calculator and the cleaned history table.
model = joblib.load(os.path.join(BASE, "model", "parkping_model.joblib"))
history = pd.read_csv(os.path.join(BASE, "data", "final_parking_cleaned.csv"))

ZONES = ["Zone A", "Zone B", "Zone C", "Zone D"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Scores copied from the notebook (Part 7 and Part 8), measured on the 200 newest records.
LAZY_SCORE = 52.5
TREE_SCORE = 56.5


@app.route("/")
def home():
    return render_template("index.html", lazy=LAZY_SCORE, tree=TREE_SCORE)


@app.route("/api/predict", methods=["POST"])
def predict():
    data = request.get_json(silent=True) or {}
    zone = data.get("zone")
    day = data.get("day")
    try:
        hour = int(data.get("hour"))
    except (TypeError, ValueError):
        hour = -1

    # Refuse anything the model was not trained on.
    if zone not in ZONES or day not in DAYS or not 0 <= hour <= 23:
        return jsonify(error="Choose a zone, a day and an hour from 0 to 23."), 400

    # One row, same three column names as the notebook (Part 10).
    question = pd.DataFrame([{"Hour": hour, "Day": day, "Parking_Lot_Section": zone}])
    chance = model.predict_proba(question)[0][1]  # [1] = the "Occupied" column

    # History is a plain count from the table. No model involved.
    same_hour = history[history["Hour"] == hour]
    occupied = int(same_hour["Occupied"].sum())
    total = int(len(same_hour))

    return jsonify(
        chance=round(chance * 100),
        bays_taken=round(chance * 12),
        history_percent=round(occupied / total * 100),
        history_occupied=occupied,
        history_total=total,
    )


@app.route("/api/history")
def hourly_history():
    # Percent occupied for each hour of the day, for the small bar chart.
    by_hour = history.groupby("Hour")["Occupied"].mean() * 100
    return jsonify(hours=[round(float(by_hour[h])) for h in range(24)])


if __name__ == "__main__":
    app.run(debug=True)

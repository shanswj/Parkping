"""
Train ParkPing's simple occupancy model.

PURPOSE:
We are not predicting an exact future parking bay.
We estimate whether parking is likely to be occupied from historical/context features.
That prediction supports a decision: stay in this zone, watch for a leaving ping, or try another zone.

MODEL:
DecisionTreeClassifier(max_depth=5)
Reason: fast, works with non-linear rules, and is easier to explain during code review than a neural network.

IMPORTANT:
The script deliberately avoids obvious leakage columns such as Occupancy Rate,
sensor readings, exit time and parking duration if they directly reveal the target.
"""
from pathlib import Path
import json
import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
MODEL_PATH = BASE_DIR / "model.joblib"
META_PATH = BASE_DIR / "model_meta.json"

def clean_name(name):
    return (
        str(name).strip().lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("-", "_")
    )

def find_dataset():
    csv_files = [p for p in DATA_DIR.glob("*.csv") if p.name != "sample.csv"]
    if not csv_files:
        raise FileNotFoundError(
            "No Kaggle CSV found. Download the dataset and place its CSV inside the data/ folder."
        )
    return csv_files[0]

def first_existing(columns, candidates):
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None

dataset_path = find_dataset()
df = pd.read_csv(dataset_path)
df.columns = [clean_name(c) for c in df.columns]

print("Dataset:", dataset_path.name)
print("Rows:", len(df))
print("Columns:", list(df.columns))

target = first_existing(
    df.columns,
    ["occupancy_status", "occupancy", "status"]
)
if target is None:
    raise ValueError("Could not find the occupancy target column. Inspect your CSV column names.")

# Convert common text targets to 0/1.
target_text = df[target].astype(str).str.strip().str.lower()
occupied_words = {"occupied", "1", "true", "yes", "full"}
vacant_words = {"vacant", "available", "0", "false", "no", "empty"}

def encode_target(value):
    if value in occupied_words:
        return 1
    if value in vacant_words:
        return 0
    return None

y = target_text.map(encode_target)
valid = y.notna()
df = df.loc[valid].copy()
y = y.loc[valid].astype(int)

# Create safe time features from timestamp when available.
timestamp_col = first_existing(df.columns, ["timestamp", "date_time", "datetime"])
if timestamp_col:
    parsed = pd.to_datetime(df[timestamp_col], errors="coerce")
    df["hour"] = parsed.dt.hour
    df["day_of_week"] = parsed.dt.dayofweek
    df["is_weekend"] = (parsed.dt.dayofweek >= 5).astype(int)

# Only use columns that may realistically be known BEFORE the occupancy outcome.
candidate_features = [
    "hour",
    "day_of_week",
    "is_weekend",
    "parking_lot_section",
    "parking_section",
    "section",
    "vehicle_type",
    "user_type",
    "weather_conditions",
    "weather_condition",
    "nearby_traffic_conditions",
    "traffic_conditions",
    "parking_spot_size",
    "reserved_status",
    "electric_vehicle_charging_availability",
]

features = []
for name in candidate_features:
    if name in df.columns and name not in features:
        features.append(name)

if not features:
    raise ValueError(
        "No suitable model features were found. Print the columns and map your dataset's names "
        "to candidate_features in ml/train_model.py."
    )

X = df[features].copy()

numeric_features = [c for c in features if pd.api.types.is_numeric_dtype(X[c])]
categorical_features = [c for c in features if c not in numeric_features]

for c in numeric_features:
    X[c] = X[c].fillna(X[c].median())

for c in categorical_features:
    X[c] = X[c].fillna("Unknown").astype(str)

preprocessor = ColumnTransformer(
    transformers=[
        ("num", "passthrough", numeric_features),
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
    ]
)

model = DecisionTreeClassifier(
    max_depth=5,
    min_samples_leaf=5,
    random_state=42
)

pipeline = Pipeline([
    ("preprocess", preprocessor),
    ("model", model),
])

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y
)

pipeline.fit(X_train, y_train)
pred = pipeline.predict(X_test)

metrics = {
    "accuracy": round(accuracy_score(y_test, pred), 3),
    "precision": round(precision_score(y_test, pred, zero_division=0), 3),
    "recall": round(recall_score(y_test, pred, zero_division=0), 3),
    "f1": round(f1_score(y_test, pred, zero_division=0), 3),
}

defaults = {}
for feature in features:
    if feature in numeric_features:
        defaults[feature] = float(X[feature].median())
    else:
        defaults[feature] = str(X[feature].mode().iloc[0])

joblib.dump(pipeline, MODEL_PATH)
META_PATH.write_text(json.dumps({
    "dataset": dataset_path.name,
    "target": target,
    "features": features,
    "numeric_features": numeric_features,
    "categorical_features": categorical_features,
    "defaults": defaults,
    "metrics": metrics
}, indent=2), encoding="utf-8")

print("\nFeatures used:", features)
print("Metrics:", metrics)
print("Saved:", MODEL_PATH.name)
print("Saved:", META_PATH.name)

from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
csv_files = list(DATA_DIR.glob("*.csv"))

if not csv_files:
    raise FileNotFoundError("Put the Kaggle CSV inside data/ first.")

path = csv_files[0]
df = pd.read_csv(path)

print("FILE:", path.name)
print("SHAPE:", df.shape)
print("\nCOLUMNS:")
for i, col in enumerate(df.columns, start=1):
    print(f"{i:02d}. {col}")

print("\nFIRST 5 ROWS:")
print(df.head())

print("\nMISSING VALUES:")
print(df.isna().sum().sort_values(ascending=False).head(20))

print("\nDATA TYPES:")
print(df.dtypes)

# Put the Kaggle CSV here

1. Download the Smart Parking Management Dataset from Kaggle.
2. Copy the main `.csv` file into this folder.
3. Run:

```bash
python ml/inspect_data.py
python ml/train_model.py
```

Do not rename columns yet. First inspect exactly what the dataset contains.

The training script normalizes column names internally (e.g. `Occupancy Status` becomes `occupancy_status`).

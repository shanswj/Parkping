# ParkPing

Estimates the chance a parking zone in George Town is occupied, for a chosen day and hour.
Built for CU5 from the Kaggle "Smart Parking Management" dataset (1,000 records, 2021 to 2024).

This is an estimate from past records, not live data. On the 200 newest records the decision tree scored
56.5% against 52.5% for always guessing "occupied", so treat the percentage as a rough guide.

## Run it
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Files
- `Parkping_model.ipynb`: cleaning, charts, model, tests
- `data/final_parking_cleaned.csv`: cleaned table
- `model/parkping_model.joblib`: saved model
- `app.py`: Flask app
- `templates/index.html`: the page

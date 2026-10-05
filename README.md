# ParkPing — CU5 Project Starter

**Problem:** drivers waste time circling for parking because an empty bay is only obvious after it becomes empty.

**Target user:** drivers looking for public/street parking in a busy urban area.

**Solution:** ParkPing combines:
1. historical parking data -> estimate parking pressure,
2. community "I'm leaving" pings -> warn nearby drivers before a bay becomes free,
3. reward points -> encourage drivers to contribute useful pings.

> Important: This is a student prototype. Demo parking bays are illustrative and are not official Penang Smart Parking / MBPP data.

---

## 1. Architecture you must understand

```text
Browser
  |
  | HTTP request / JSON
  v
Flask (app.py)
  |\
  | \--> SQLite: pings + demo reward points
  |
  \----> saved scikit-learn model (model.joblib)
             ^
             |
       ml/train_model.py
             ^
             |
        Kaggle CSV
```

### Plain-English translation

- **HTML** = what exists on the page.
- **CSS** = how the page looks.
- **JavaScript** = what happens when the user clicks.
- **Flask** = receives requests from the browser and decides what to do.
- **SQLite** = remembers pings and points.
- **pandas** = reads/cleans the CSV.
- **scikit-learn** = learns patterns from historical parking data.
- **joblib** = saves/loads the trained model.

---

## 2. First setup

Open the project folder in VS Code.

### Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install libraries:

```powershell
pip install -r requirements.txt
```

Run the app:

```powershell
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

At this point the UI + parking ping workflow already works in demo mode.

---

## 3. Add the real Kaggle dataset

Download the Smart Parking Management Dataset and put its CSV in:

```text
data/
```

Then:

```powershell
python ml/inspect_data.py
```

Read the output. Know:
- number of rows,
- number of columns,
- target column,
- missing values,
- which features you will use.

Then:

```powershell
python ml/train_model.py
```

This creates:

```text
model.joblib
model_meta.json
```

Restart Flask and the "Historical Model" card can call the model.

---

## 4. The one workflow you MUST be able to explain

### A. Driver taps "I'm leaving"

1. `index.html` contains the button.
2. `app.js` listens for the click.
3. JavaScript sends a `POST /api/pings`.
4. Flask receives the JSON.
5. Flask inserts the ping into SQLite.
6. Frontend requests `/api/spots` again.
7. That bay changes from grey "occupied" to orange "leaving soon".

### B. Driver asks for parking outlook

1. User enters hour/day.
2. JavaScript sends JSON to `POST /api/predict`.
3. Flask loads the saved model.
4. Flask converts JSON into a one-row pandas DataFrame.
5. The scikit-learn pipeline performs preprocessing.
6. Decision tree returns occupied probability.
7. Flask converts it to availability probability.
8. Browser displays a useful recommendation.

If you can explain those 8 steps, you can explain the core application.

---

## 5. Why a Decision Tree?

Use this answer during presentation:

> "I chose a shallow Decision Tree because my goal is not to build the most complicated model. I need a model that can learn non-linear parking patterns, trains quickly, and is easy to explain and modify during review. I limit its depth to reduce overfitting."

Alternatives you can mention:
- Logistic Regression: simpler but mainly linear relationships.
- Random Forest: often stronger but harder to explain because it combines many trees.
- Neural networks: unnecessary complexity for this dataset and deadline.

---

## 6. Data leakage — very important

Do NOT blindly feed every column into the model.

If predicting whether a bay is occupied, columns such as:
- current sensor readings,
- occupancy rate,
- exit time,
- parking duration after the visit ends,

may reveal the answer or information you would not know at prediction time.

That is called **data leakage**.

Your model should mainly use information plausibly known before/during the parking search, such as:
- hour,
- day of week,
- parking section,
- weather,
- traffic,
- vehicle/user type where appropriate.

---

## 7. What is real vs simulated

### Real in our prototype
- Kaggle dataset analysis
- trained ML model
- Flask API
- parking ping creation
- status change
- points stored in SQLite
- frontend/backend communication

### Simulated
- official Penang parking bay locations
- real PSP integration
- real MBPP sensors
- real push notifications
- actual ZUS partnership/vouchers
- production GPS tracking

Never claim simulated parts are real integrations.

---

## 8. Git routine

First push:

```powershell
git init
git add .
git commit -m "Initial ParkPing project structure and parking ping prototype"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

Then make small meaningful commits:

```powershell
git add .
git commit -m "Add dataset inspection and preprocessing"
git push
```

```powershell
git add .
git commit -m "Train occupancy decision tree and add evaluation metrics"
git push
```

```powershell
git add .
git commit -m "Connect prediction API to ParkPing dashboard"
git push
```

```powershell
git add .
git commit -m "Add leaving-soon workflow and reward points"
git push
```

Do not fake dozens of meaningless commits. Your repository should tell the story of actual development.

---

## 9. Five files to know first

If overwhelmed, learn only these in this order:

1. `app.py`
2. `templates/index.html`
3. `static/js/app.js`
4. `ml/train_model.py`
5. `static/css/style.css`

For each file, be able to say:
- what its job is,
- what goes into it,
- what comes out,
- one thing you can modify.

---

## 10. Easy live changes your lecturer could ask

Practice these yourself:

### Change reward from 10 to 15 points
In `app.py`, find:

```python
points = points + 10
```

Change `10` to `15`.

### Add a 10-minute leaving option
- Add button in `index.html`
- Allow `10` in `app.py` validation

### Change model depth
In `ml/train_model.py`:

```python
max_depth=5
```

Change it and retrain.

### Change recommendation threshold
In `app.py`, find:

```python
if availability >= 0.65:
```

Change `0.65`.

### Add another parking bay
Add one dictionary to `DEMO_SPOTS` in `app.py`.

These are perfect code-review practice tasks.

---

## 11. Presentation sentence

Memorise the logic, not a script:

> "The problem is that drivers only learn that a parking bay is available after it becomes empty. ParkPing adds an earlier community signal: a driver who is about to leave can ping the bay. Historical parking data gives context about how difficult parking is likely to be, while the live ping gives the user an action they can take immediately. Rewards encourage people to contribute those pings."

---

## 12. Rule for every new feature

Before adding anything, answer:

1. What user problem does it solve?
2. Which file implements it?
3. What data does it use?
4. Can I explain it without AI?
5. Could I modify it live?

If you cannot answer those, do not add the feature before code freeze.

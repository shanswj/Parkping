# ParkPing in a container: a small Linux box with Python, the app, the saved model and the cleaned data.

# 1. Start from a small official Python image.
FROM python:3.12-slim

# 2. Work inside /app in the container.
WORKDIR /app

# 3. Install the libraries first, so Docker can reuse this step when only the code changes.
#    Gunicorn is a production web server; Flask's own app.run() is for development only.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# 4. Copy in only what the app needs to run.
COPY app.py .
COPY templates/ templates/
COPY model/ model/
COPY data/final_parking_cleaned.csv data/

# 5. The app listens on port 5000 inside the container.
EXPOSE 5000

# 6. Start the app: Gunicorn loads the `app` object from app.py and listens on every network address.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]

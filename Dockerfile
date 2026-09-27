FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    HOST=0.0.0.0

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Generate dataset if expanded data is not bundled
RUN python dataset/generate_dataset.py --seed-dir ./dataset --out ./dataset/expanded

EXPOSE 8080

CMD ["sh", "-c", "python -m uvicorn bot:app --host 0.0.0.0 --port ${PORT:-8080}"]

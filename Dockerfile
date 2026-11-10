FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py dashboard.html glass.css warm-glass.css layout.js greenhouse.jpg ai.js ai.css weather_adapter.py weather.js weather.css groq_adapter.py groq.js telemetry.js ./
COPY data ./data
CMD ["python", "app.py", "--live"]

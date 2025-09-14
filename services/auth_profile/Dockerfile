FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir fastapi uvicorn[standard] prometheus-client \
       aiokafka opentelemetry-sdk opentelemetry-exporter-otlp \
       opentelemetry-instrumentation-fastapi pydantic pydantic-settings \
       sqlalchemy alembic psycopg[binary] pyjwt

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

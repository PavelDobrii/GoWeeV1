# Template Service

Minimal FastAPI service template with OpenTelemetry, Prometheus metrics and a Kafka consumer loop.

## Running

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Endpoints

* `/healthz` – liveness probe
* `/readyz` – readiness probe
* `/metrics` – Prometheus metrics

### Kafka consumer

Set the environment variables `KAFKA_BROKERS` and `KAFKA_TOPIC_IN` to start the Kafka consumer loop. On startup, a log message confirms the loop launch and messages are processed idempotently using an in-memory cache.

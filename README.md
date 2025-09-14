# CityGuide Monorepo

Development stack for CityGuide services using Docker Compose.

## Services
- **Redpanda** broker on port 9092 with **Redpanda Console** at http://localhost:8080
- **Jaeger** tracing UI at http://localhost:16686 (OTLP ports 4317 and 4318)
- **Prometheus** metrics at http://localhost:9090
- **Grafana** dashboards at http://localhost:3000
- **Postgres** database at localhost:5432 (user `cg`, password `cg`, database `cityguide`)

## Usage
Run the entire stack:

```sh
docker compose up -d
```

View logs or stop:

```sh
docker compose logs -f
docker compose down
```

Makefile wrappers are also available:

```sh
make up
make logs
make down
```

Additional development targets:

```sh
make fmt
make lint
make tests
make build
```

All services are connected through the `core-net` network.

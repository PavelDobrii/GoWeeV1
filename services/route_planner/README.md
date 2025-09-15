# Сервис Route Planner

## Назначение
Route Planner принимает список точек интереса, рассчитывает удобный порядок их
посещения, оценивает длительность маршрута и сохраняет подтверждённые варианты.
При подтверждении маршрута сервис отправляет событие в Kafka, запускающее
дальнейший пайплайн генерации контента. Для уточнения дистанции и ETA сервис
при наличии ключа обращается к Google Maps Directions API и автоматически
переходит на локальный расчёт при его отсутствии.

## Основные возможности
- Формирует предварительный порядок посещения (TSP-подобный алгоритм) и
  рассчитывает дистанцию/ETA для выбранного режима транспорта.
- При наличии `GOOGLE_MAPS_API_KEY` уточняет расчёт через Google Maps с учётом
  возможной оптимизации `waypoint_order`.
- Сохраняет подтверждённый маршрут и снимок порядка POI в базе данных.
- Публикует событие `route.confirmed` для Orchestrator.
- Предоставляет health-check'и и метрики Prometheus.

## HTTP API
| Метод | Путь | Назначение |
| --- | --- | --- |
| `POST` | `/routes/preview` | Принимает `{poi_ids, mode}` и возвращает один или несколько вариантов маршрута с оценками по времени и дистанции. |
| `POST` | `/routes/confirm` | Принимает `{option_id}` из ответа `/routes/preview`, сохраняет маршрут и публикует Kafka-событие. |
| `GET` | `/healthz` | Проверка живости. |
| `GET` | `/readyz` | Проверка готовности. |
| `GET` | `/metrics` | Метрики Prometheus. |

Каталог точек интереса (POI) встроен в код и описывает объекты в России. После
запроса `/routes/preview` информация о вариантах хранится в памяти, чтобы
`/routes/confirm` мог сослаться на `option_id`.

## Kafka-топики
| Направление | Топик | Пайлоад |
| --- | --- | --- |
| Produce | `route.confirmed` | `{ "route_id": <int>, "mode": <str>, "eta_min": <float>, "distance_m": <float>, "order": [<poi_id>, ...] }` — отправляется после успешного подтверждения. |

Если `KAFKA_BROKERS` не установлен, подтверждение маршрута выполнится, но событие
отправлено не будет.

## Хранилище
По умолчанию используется SQLite (`route_planner.db`) с автоматическим
созданием таблиц `routes` и `route_snapshots` при старте. Можно переключиться на
любой поддерживаемый SQLAlchemy движок, задав `DATABASE_URL`.

## Конфигурация
| Переменная | Обязательна | По умолчанию | Описание |
| --- | --- | --- | --- |
| `DATABASE_URL` | Нет | `sqlite:///./route_planner.db` | URL базы данных SQLAlchemy. |
| `KAFKA_BROKERS` | Нет | – | Брокеры Kafka/Redpanda для публикации `route.confirmed`. |
| `GOOGLE_MAPS_API_KEY` | Нет | – | Ключ Google Maps Directions API. |
| `GOOGLE_MAPS_LANGUAGE` | Нет | `ru` | Язык ответов Google Maps. |
| `GOOGLE_MAPS_REGION` | Нет | `ru` | Регион, помогающий уточнить маршруты. |
| `GOOGLE_MAPS_TIMEOUT` | Нет | `5.0` | Тайм-аут HTTP-запросов к Google Maps. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Нет | – | Глобальный OTLP-эндпоинт для трассировок. |

## Локальный запуск
1. (Опционально) запустите Kafka для проверки событий:
   ```bash
   docker compose up -d redpanda
   export KAFKA_BROKERS=localhost:9092
   ```
2. Установите зависимости и подготовьте сервис:
   ```bash
   cd services/route_planner
   poetry install
   ```
   Для интеграции с Directions API установите пакет `googlemaps`:
   ```bash
   poetry run pip install googlemaps
   ```
3. (Опционально) переключитесь на PostgreSQL, задав `DATABASE_URL`:
   ```bash
   export DATABASE_URL=postgresql+psycopg://cg:cg@localhost:5432/cityguide
   ```
4. Укажите ключ Google Maps, чтобы получать данные Directions API:
   ```bash
   export GOOGLE_MAPS_API_KEY=AIza...
   ```
5. Запустите API:
   ```bash
   poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
6. Вызовите `/routes/preview` с нужными POI и подтвердите вариант через
   `/routes/confirm`.

## Наблюдаемость
- `/metrics` предоставляет `JOB_DURATION`, `KAFKA_CONSUMER_LAG` и другие
  стандартные метрики.
- Для трассировок задайте `OTEL_EXPORTER_OTLP_ENDPOINT` — сервис использует
  общий модуль `src.common.telemetry`.

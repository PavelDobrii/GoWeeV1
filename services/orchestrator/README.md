# Сервис Orchestrator

## Назначение
Orchestrator координирует полный цикл подготовки контента после подтверждения маршрута пользователем. Он хранит состояние workflow в PostgreSQL, реагирует на события Kafka и распределяет задачи между Story Service, TTS и Delivery Prefetch. Для операторов доступен небольшой HTTP-интерфейс наблюдения и перезапуска шагов.

## Основные возможности
- Создаёт запись `Workflow` при получении события `route.confirmed` и инициирует генерацию историй.
- Отслеживает события `story.generate.completed`, получает готовые тексты и отправляет задания в TTS cо встроенным текстом.
- Контролирует завершение TTS по событиям `tts.completed`, учитывая статус `completed`/`failed`, и после успешного окончания уведомляет Delivery Prefetch.
- Позволяет просматривать прогресс workflow и принудительно перезапускать пакет TTS через HTTP.
- Экспортирует Prometheus-метрики и стандартные health-check'и.

## HTTP API
| Метод | Путь | Назначение |
| --- | --- | --- |
| `GET` | `/workflows/{route_id}` | Текущее состояние workflow и статусы шагов для выбранного маршрута. |
| `POST` | `/workflows/{route_id}/restart?step=tts_batch` | Сбрасывает шаг TTS в состояние `pending`, увеличивает счётчик попыток и инициирует повторный запуск. |
| `GET` | `/healthz` | Проверка живости. |
| `GET` | `/readyz` | Проверка готовности. |
| `GET` | `/metrics` | Метрики Prometheus (`JOB_DURATION`, `KAFKA_CONSUMER_LAG`, пользовательские гистограммы). |

## Kafka-топики
| Направление | Топик | Пайлоад |
| --- | --- | --- |
| Consume | `route.confirmed` | `{ "route_id": <str>, "mode": <str>, ... }` — старт workflow, после чего отправляется команда истории. |
| Consume | `story.generate.completed` | `{ "route_id": <str>, "lang": <str>, "stories": [...] }` — уведомляет о готовых текстах. |
| Consume | `tts.completed` | `{ "route_id": <str>, "story_id": <str>, "status": <str>, ... }` — завершение синтеза с указанием статуса. |
| Produce | `story.generate` | `{ "route_id": <str>, "lang": "ru" }` — команда Story Service. |
| Produce | `tts.requested` | `{ "route_id": <str>, "story_id": <str>, "text": <str>, ... }` — задания для TTS на каждую историю. |
| Produce | `delivery.prefetch` | `{ "route_id": <str>, "next_audio": [...] }` — уведомление после завершения всех TTS-джобов. |

Kafka-интеграция построена на `src.common.kafka`, поэтому при включении OpenTelemetry все взаимодействия попадают в трассировки автоматически.

## Конфигурация
| Переменная | Обязательна | По умолчанию | Описание |
| --- | --- | --- | --- |
| `KAFKA_BROKERS` | Да | `kafka:9092` | Брокеры Kafka/Redpanda. Требуются для потребления и публикации событий. |
| `POSTGRES_DSN` | Да | `sqlite://` | Асинхронный DSN SQLAlchemy. Для локальной работы используйте, например, `postgresql+asyncpg://cg:cg@localhost:5432/cityguide`. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Нет | – | URL OTLP для экспорта трассировок (например, `http://localhost:4317`). |

Все переменные можно указать через `.env` или экспортировать в окружение shell.

## Подготовка инфраструктуры
1. Запустите брокер Kafka и PostgreSQL (можно воспользоваться `docker compose` из корня репозитория):
   ```bash
   docker compose up -d redpanda postgres
   ```
2. Установите зависимости проекта и примените миграции:
   ```bash
   poetry install
   export POSTGRES_DSN=postgresql+asyncpg://cg:cg@localhost:5432/cityguide
   poetry run alembic upgrade head
   ```
3. Убедитесь, что таблицы orchestration (см. `services/orchestrator/app/models.py`) созданы в базе.

## Локальный запуск
1. Установите зависимости сервиса:
   ```bash
   cd services/orchestrator
   poetry install
   ```
2. Настройте окружение:
   ```bash
   export KAFKA_BROKERS=localhost:9092
   export POSTGRES_DSN=postgresql+asyncpg://cg:cg@localhost:5432/cityguide
   # необязательно: export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
   ```
3. Запустите приложение FastAPI:
   ```bash
   poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
4. Проверьте состояние workflow по `http://localhost:8000/workflows/{route_id}` после появления событий.

## Наблюдаемость
- `/metrics` публикует метрики обработки HTTP и Kafka, а также гистограмму `route_to_first_audio_seconds` из `workflow.py`.
- При заданном `OTEL_EXPORTER_OTLP_ENDPOINT` в трассировки попадают все HTTP-запросы и операции Kafka.

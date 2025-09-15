# GoWeeV1 — монорепозиторий инфраструктуры CityGuide

## Обзор
Monorepo объединяет сервисы и общие библиотеки платформы CityGuide. Он содержит
готовую инфраструктуру разработчика: Kafka (Redpanda), Postgres, Prometheus,
Grafana, Jaeger, а также набор микросервисов. Все окружение поднимается одной
командой через Docker Compose либо целевыми командами из `Makefile`.

## Основные компоненты и порты
| Компонент              | Порт/URL                     | Назначение                                             |
|------------------------|------------------------------|--------------------------------------------------------|
| Redpanda               | `localhost:9092`             | Брокер Kafka для обмена событиями                      |
| Redpanda Console       | http://localhost:8080        | UI для мониторинга топиков                             |
| Postgres               | `localhost:5432`             | Основная БД (`cg`/`cg`, БД `cityguide`)                |
| Jaeger                 | http://localhost:16686       | Трассировка запросов (OTLP gRPC `4317`, HTTP `4318`)   |
| Prometheus             | http://localhost:9090        | Сбор метрик                                            |
| Grafana                | http://localhost:3000        | Дэшборды; дефолтные креды `admin`/`admin`              |
| Микросервисы*          | `http://localhost:8001-8007` | Демонстрационные сервисы (auth, orchestrator и др.)    |

\* подробные README каждого сервиса находятся в директориях `services/*`.

## Структура репозитория
- `src/common` — общая библиотека: настройки, БД, Kafka, метрики, телеметрия.
- `src/goweerv1` — корневой python-пакет.
- `services/*` — микросервисы (FastAPI + Kafka).
- `infra/*` — конфигурация Prometheus, Grafana, Postgres, Nginx.
- `contracts/*` — OpenAPI/AsyncAPI спецификации.
- `docs/*` — дополнительная документация и диаграммы.
- `tests/*` — автотесты уровня платформы.
- `scripts/*` — вспомогательные скрипты.
- `template_service/` — заготовка для новых сервисов.

## Быстрый старт через Docker Compose
1. Установите Docker и Docker Compose v2.
2. Склонируйте репозиторий и при необходимости создайте `.env` в корне (см.
   раздел про конфигурацию).
3. Запустите окружение:
   ```bash
   make up       # либо docker compose up -d
   ```
4. Проверяйте логи:
   ```bash
   make logs
   ```
5. Остановите окружение:
   ```bash
   make down
   ```

Все сервисы объединены в сеть `core-net` и автоматически подтягивают зависимости
(`depends_on` в `docker-compose.yml`).

## Локальная разработка без Docker
1. Убедитесь, что установлен Python 3.11 и Poetry 1.6+.
2. Установите зависимости:
   ```bash
   poetry install
   ```
3. Активируйте виртуальное окружение `poetry shell` или используйте `poetry run`.
4. Для запуска FastAPI-приложений вызывайте соответствующие точки входа, например:
   ```bash
   poetry run uvicorn services.orchestrator.app.main:app --reload
   ```
   Перед запуском убедитесь, что окружение (Kafka, Postgres) доступно и переменные
   окружения установлены.

## Конфигурация и секреты
Модуль `src/common/settings.py` использует `.env` в корне и переменные
окружения. Основные ключи:

| Переменная                             | Назначение и значение по умолчанию               |
|----------------------------------------|--------------------------------------------------|
| `KAFKA_BROKERS`                        | Адрес брокера Kafka (`kafka:9092`)               |
| `POSTGRES_DSN`                         | DSN БД для SQLAlchemy (`sqlite://` по умолчанию) |
| `OTEL_EXPORTER_OTLP_ENDPOINT`          | Endpoint OTEL-коллектора (по умолчанию отключено)|
| `DATABASE_URL`                         | DSN синхронного клиента (используется сервисами) |
| `JWT_SECRET`, `...`                    | Секреты конкретных сервисов (см. `docker-compose.yml`)|

Секреты и ключи рекомендуется задавать в файле `.env` или через переменные
среды вашего оркестратора. Docker Compose уже содержит значения для демо,
но перед продуктивным использованием их нужно заменить.

## Работа с БД и миграциями
- БД запускается в контейнере `postgres` с тестовыми данными из
  `infra/postgres/init.sql`.
- Миграции Alembic:
  ```bash
  poetry run alembic upgrade head
  ```
  Конфигурация автоматически подставляет текущее значение `POSTGRES_DSN`.
- Для временных тестов можно установить `POSTGRES_DSN=sqlite://` — код корректно
  переключится на in-memory SQLite.

## Kafka и шаблон outbox
- Используйте `KafkaProducer` и `KafkaConsumer` из `src/common/kafka.py`.
  Продюсер/консьюмер реализуют контекстный менеджер: 
  ```python
  from common.kafka import KafkaProducer

  async with KafkaProducer(brokers) as producer:
      await producer.send("topic", key="user-1", value={"event": "created"})
  ```
  Продюсер сериализует данные в компактный JSON и повторно использует соединение,
  исключая лишние запуски клиента.
- Модуль `src/common/outbox.py` реализует шаблон outbox: `enqueue` сохраняет
  сообщение в таблицу, `drain_outbox` читает очереди батчами и публикует их в
  Kafka без повторной JSON-сериализации. Параметр `poll_interval` контролирует
  частоту опроса (по умолчанию 1 секунда).

## Метрики и наблюдаемость
- `common.metrics.setup_metrics` добавляет middleware со счётчиками HTTP и
  эндпоинт `/metrics` для Prometheus.
- `common.telemetry.setup_otel` включает трассировку и метрики при наличии
  `OTEL_EXPORTER_OTLP_ENDPOINT`. Подключите Jaeger/Tempo или иной коллектор,
  указав его адрес в `.env`.
- Grafana и Prometheus уже настроены через файлы в `infra/`.

## Тестирование и контроль качества
Все основные проверки вынесены в `Makefile`:
- `make fmt` — автоформатирование (black).
- `make lint` — статический анализ (ruff).
- `make typecheck` — типизация (mypy).
- `make tests` — pytest.

Запустите их перед коммитами либо используйте CI.

## Дополнительные материалы
- `docs/` — инструкции по работе с OpenAPI/AsyncAPI, диаграммы.
- `contracts/` — спецификации API. Их можно просмотреть через Redocly либо
  Swagger UI (см. `docs/README.md`).
- `template_service/` — стартовый шаблон нового сервиса.

## Примечания по эксплуатации
- После первого входа в Grafana смените пароль пользователя `admin`.
- Для доступа в Redpanda Console используйте ссылку
  http://localhost:8080 после запуска окружения.
- Проверяйте здоровье сервисов через `/healthz` или `/openapi.json` — healthcheck
  примеры можно увидеть в `docker-compose.yml`.
- При необходимости пробросьте дополнительные переменные окружения через файл
  `.env` или блок `environment` в `docker-compose.yml`.

Такой набор позволяет быстро поднять и развивать экосистему CityGuide, сохраняя
единые зависимости и инструменты наблюдаемости.

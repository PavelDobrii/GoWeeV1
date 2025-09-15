# Сервис Story Service

## Назначение
Story Service генерирует заглушечные markdown-истории для точек интереса. Сервис сохраняет результаты в БД, выполняет простую проверку качества и публикует события о завершении пакетной генерации. Решение синхронное и предназначено для интеграционных сценариев.

## Основные возможности
- Формирует ~300 слов текста для каждой точки интереса (функция `_fake_llm`).
- Записывает истории и их статусы (`completed`, `rejected`) в таблицу `stories`.
- Отклоняет истории, содержащие запрещённые слова из конфигурации.
- Обрабатывает одиночные запросы и пакетную генерацию по маршруту.
- Публикует событие `story.generate.completed` после пакетной генерации.
- Предоставляет стандартные health-check'и и метрики Prometheus.

## HTTP API
| Метод | Путь | Назначение |
| --- | --- | --- |
| `POST` | `/story/generate` | Запускает background-задачу для `{poi_id, lang, tags}` и мгновенно возвращает `job_id`. |
| `POST` | `/story/generate_batch` | Генерирует истории для маршрута `{route_id, lang}` и при необходимости отправляет Kafka-событие. |
| `GET` | `/healthz` | Проверка живости. |
| `GET` | `/readyz` | Проверка готовности. |
| `GET` | `/metrics` | Метрики Prometheus. |

Сгенерированные истории можно изучить напрямую в базе данных, указанной в `DATABASE_URL`.

## Kafka-топики
| Направление | Топик | Пайлоад |
| --- | --- | --- |
| Produce | `story.generate.completed` | `{ "route_id": <str>, "stories": [{"poi_id": <int>, "story_id": <int>}, ...] }` — отправляется после `/story/generate_batch`. |

Если `KAFKA_BROKERS` не указан, истории всё равно создаются, но событие не публикуется.

## Хранилище
По умолчанию используется SQLite (`story_service.db`). Таблица создаётся автоматически при старте. Для подключения PostgreSQL задайте `DATABASE_URL=postgresql+psycopg://...`.

## Конфигурация
| Переменная | Обязательна | По умолчанию | Описание |
| --- | --- | --- | --- |
| `DATABASE_URL` | Нет | `sqlite:///./story_service.db` | SQLAlchemy URL для хранения историй. |
| `KAFKA_BROKERS` | Нет | – | Список брокеров Kafka/Redpanda. Включает отправку событий о завершении batch. |
| `FORBIDDEN_WORDS` | Нет | `forbidden,bad` | Список слов через запятую, наличие которых помечает историю как `rejected`. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Нет | – | Эндпоинт OTLP для экспорта трассировок. |

## Локальный запуск
1. Установите зависимости:
   ```bash
   cd services/story_service
   poetry install
   ```
2. (Опционально) настройте Kafka для событий batch:
   ```bash
   export KAFKA_BROKERS=localhost:9092
   ```
3. При необходимости измените настройки фильтрации слов:
   ```bash
   export FORBIDDEN_WORDS="badword1,badword2"
   ```
4. Запустите API:
   ```bash
   poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
5. Вызовите `/story/generate` или `/story/generate_batch` и проверьте содержимое таблицы `stories` в выбранной базе.

## Наблюдаемость
- `/metrics` публикует метрики обработки HTTP и Kafka.
- Для трассировок задайте `OTEL_EXPORTER_OTLP_ENDPOINT` и подключите общий модуль `src.common.telemetry` (уже используется сервисом).

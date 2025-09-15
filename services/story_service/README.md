# Сервис Story Service

## Назначение
Story Service генерирует markdown-истории о точках интереса, используя ChatGPT в
качестве LLM. Сервис сохраняет результаты в базе данных, запускает простую
проверку качества и публикует события о завершении пакетной генерации, чтобы
остальные компоненты пайплайна могли запрашивать озвучку и доставку.

## Основные возможности
- Интеграция с ChatGPT (OpenAI). При наличии `OPENAI_API_KEY` истории
  создаются реальной моделью, иначе используется заглушечный генератор для
  офлайн-сценариев.
- Сохраняет тексты и статусы (`completed`, `rejected`, `failed`) в таблицу
  `stories`.
- Проверяет текст на наличие запрещённых слов и отклоняет неподходящие истории.
- Обрабатывает одиночные запросы и пакетную генерацию по маршруту.
- Публикует событие `story.generate.completed` с готовыми текстами и метаданными
  для дальнейшего запуска TTS.
- Предоставляет стандартные health-check'и и метрики Prometheus.

## HTTP API
| Метод | Путь | Назначение |
| --- | --- | --- |
| `POST` | `/story/generate` | Запускает background-задачу для `{poi_id, lang, tags}` и мгновенно возвращает `job_id`. |
| `POST` | `/story/generate_batch` | Генерирует истории для маршрута `{route_id, lang}` и публикует Kafka-событие при наличии брокера. |
| `GET` | `/healthz` | Проверка живости. |
| `GET` | `/readyz` | Проверка готовности. |
| `GET` | `/metrics` | Метрики Prometheus. |

Сгенерированные истории доступны напрямую в БД, указанной в `DATABASE_URL`.

## Kafka-топики
| Направление | Топик | Пайлоад |
| --- | --- | --- |
| Produce | `story.generate.completed` | `{ "route_id": <str>, "lang": <str>, "stories": [{"poi_id": <int>, "story_id": <int>, "status": <str>, "markdown": <str>, "lang": <str>}, ...] }` — отправляется после `/story/generate_batch`. |

Если `KAFKA_BROKERS` не указан, истории продолжают сохраняться, но событие не
публикуется.

## Хранилище
По умолчанию используется SQLite (`story_service.db`). Таблица создаётся
автоматически при старте. Для подключения PostgreSQL задайте
`DATABASE_URL=postgresql+psycopg://...`.

## Конфигурация
| Переменная | Обязательна | По умолчанию | Описание |
| --- | --- | --- | --- |
| `DATABASE_URL` | Нет | `sqlite:///./story_service.db` | SQLAlchemy URL для хранения историй. |
| `KAFKA_BROKERS` | Нет | – | Список брокеров Kafka/Redpanda. Включает публикацию событий о завершении batch. |
| `FORBIDDEN_WORDS` | Нет | `forbidden,bad` | Запрещённые слова через запятую. |
| `OPENAI_API_KEY` | Нет | – | Ключ для доступа к ChatGPT. При отсутствии используется локальная заглушка. |
| `OPENAI_BASE_URL` | Нет | – | Альтернативный эндпоинт OpenAI (для прокси). |
| `OPENAI_MODEL` | Нет | `gpt-3.5-turbo` | Имя модели ChatGPT. |
| `OPENAI_TEMPERATURE` | Нет | `0.7` | Температура ответа. |
| `OPENAI_MAX_TOKENS` | Нет | `1200` | Максимальная длина отклика. |
| `OPENAI_RESPONSE_LANGUAGE` | Нет | `ru` | Язык ответа по умолчанию. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Нет | – | Эндпоинт OTLP для экспорта трассировок. |

## Локальный запуск
1. Установите зависимости:
   ```bash
   cd services/story_service
   poetry install
   ```
   Для реальной интеграции установите пакет `openai`:
   ```bash
   poetry run pip install openai
   ```
2. (Опционально) настройте Kafka для событий batch:
   ```bash
   export KAFKA_BROKERS=localhost:9092
   ```
3. Укажите ключ OpenAI, если требуется реальная генерация:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```
4. Запустите API:
   ```bash
   poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
5. Вызовите `/story/generate` или `/story/generate_batch` и проверьте содержимое таблицы `stories` в выбранной базе.

## Наблюдаемость
- `/metrics` публикует метрики обработки HTTP и Kafka.
- Для трассировок задайте `OTEL_EXPORTER_OTLP_ENDPOINT` и подключите общий модуль
  `src.common.telemetry` (уже используется сервисом).

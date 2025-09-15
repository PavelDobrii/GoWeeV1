# Сервис TTS

## Назначение
TTS Service синтезирует аудио-файлы из текстов историй, используя Google Cloud
Text-to-Speech. Сервис слушает Kafka-запросы, сохраняет метаданные и сообщает
оркестратору о результате (успех или ошибка), чтобы downstream-сервисы могли
подготовить доставку аудио.

## Основные возможности
- Интеграция с Google Cloud TTS. При наличии сервисного аккаунта создаются
  полноценные аудио-файлы, иначе формируется заглушка с пометкой `failed`.
- Сохраняет метаданные в таблице `audio_files`, включая формат и длительность.
- Публикует событие `tts.completed` с маршрутом, идентификатором аудио и
  статусом выполнения.
- Принимает HTTP-запросы `/tts/request` для ручного добавления заданий.
- Гарантирует существование каталога с аудио при старте и экспортирует
  Prometheus-метрики.

## HTTP API
| Метод | Путь | Назначение |
| --- | --- | --- |
| `POST` | `/tts/request` | Принимает `{story_id, route_id?, text?, voice?, format?, lang?}` и публикует задание в Kafka. |
| `GET` | `/healthz` | Проверка живости. |
| `GET` | `/readyz` | Проверка готовности. |
| `GET` | `/metrics` | Метрики Prometheus. |

## Kafka-топики
| Направление | Топик | Пайлоад |
| --- | --- | --- |
| Consume | `tts.requested` | `{ "route_id": <str>, "story_id": <int>, "text": <str>, "voice": <str?>, "format": <str?>, "lang": <str?> }` — задания на синтез. |
| Produce | `tts.completed` | `{ "route_id": <str>, "story_id": <int>, "audio_id": <int>, "duration_sec": <int>, "format": <str>, "status": <"completed"\|"failed"> }`. |

Повторные сообщения дедуплицируются по ключу Kafka, поэтому повторные публикации
безопасны.

## Хранилище и файлы
- При первом запуске создаётся таблица `audio_files` в базе `DATABASE_URL`
  (по умолчанию SQLite `tts_service.db`).
- Файлы размещаются в каталоге `AUDIO_DIR` (стандартно `data/audio`). Каталог
  создаётся автоматически.

## Конфигурация
| Переменная | Обязательна | По умолчанию | Описание |
| --- | --- | --- | --- |
| `DATABASE_URL` | Нет | `sqlite:///./tts_service.db` | SQLAlchemy URL для хранения метаданных. |
| `KAFKA_BROKERS` | Нет | – | Список брокеров Kafka/Redpanda. |
| `AUDIO_DIR` | Нет | `data/audio` | Каталог для сохранения файлов. |
| `GOOGLE_CREDENTIALS_PATH` | Нет | – | Путь к JSON с сервисным аккаунтом Google Cloud. |
| `GOOGLE_TTS_VOICE` | Нет | `ru-RU-Wavenet-D` | Имя голоса Google TTS. |
| `GOOGLE_TTS_LANGUAGE` | Нет | `ru-RU` | Язык синтеза. |
| `GOOGLE_TTS_AUDIO_ENCODING` | Нет | `mp3` | Формат аудио (`mp3`, `ogg_opus`, `linear16`). |
| `GOOGLE_TTS_SPEAKING_RATE` | Нет | `1.0` | Темп речи. |
| `GOOGLE_TTS_PITCH` | Нет | `0.0` | Высота тона. |
| `GOOGLE_TTS_EFFECTS_PROFILE_ID` | Нет | – | Дополнительный профиль эффектов. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Нет | – | Эндпоинт OTLP для трассировок. |

## Локальный запуск
1. Установите зависимости:
   ```bash
   cd services/tts_service
   poetry install
   ```
   Для синтеза через Google установите пакет `google-cloud-texttospeech`:
   ```bash
   poetry run pip install google-cloud-texttospeech
   ```
2. Настройте Kafka и укажите брокеров (опционально):
   ```bash
   export KAFKA_BROKERS=localhost:9092
   ```
3. Подключите Google Cloud (рекомендуется):
   ```bash
   export GOOGLE_CREDENTIALS_PATH=/path/to/account.json
   export GOOGLE_TTS_VOICE=ru-RU-Wavenet-D
   ```
4. Запустите API:
   ```bash
   poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
5. Отправьте сообщение в `tts.requested` или вызовите HTTP-эндпоинт и убедитесь,
   что в каталоге `AUDIO_DIR` появился файл.

## Наблюдаемость
- `/metrics` отдаёт метрики длительности обработки и лагов Kafka
  (`JOB_DURATION`, `KAFKA_CONSUMER_LAG`).
- При задании `OTEL_EXPORTER_OTLP_ENDPOINT` сервис экспортирует трассировки всех
  операций Kafka и HTTP.

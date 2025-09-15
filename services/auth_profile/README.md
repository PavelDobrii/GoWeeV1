# Сервис Auth Profile

## Назначение
Auth Profile обслуживает жизненный цикл учетных записей пользователей: регистрация, аутентификация по JWT, хранение профиля и согласий, а также рассылку событий об изменениях профиля. Сервис реализован на FastAPI и использует SQLAlchemy для работы с базой данных.

## Основные возможности
- Регистрация пользователей по email и паролю с созданием связанных записей профиля и согласий.
- Выдача access/refresh JWT с контролем версии токена (`token_version`) и последующим отзывом всех сессий.
- Получение и частичное обновление полей профиля (`first_name`, `last_name`).
- Управление маркетинговыми согласиями и согласием с условиями использования.
- Отправка события `user.profile.updated` в Kafka после успешного обновления профиля (если Kafka сконфигурирована).
- Экспорт метрик Prometheus и стандартные HTTP-пробы `/healthz`, `/readyz`.

## HTTP API
| Метод | Путь | Назначение |
| --- | --- | --- |
| `POST` | `/auth/register` | Регистрация пользователя и создание пустых записей профиля/согласий. Возвращает числовой `user_id`. |
| `POST` | `/auth/login` | Проверка учетных данных и выдача пары `{access_token, refresh_token}`. |
| `POST` | `/auth/refresh` | Обновление access/refresh токенов по действительному refresh-токену. |
| `POST` | `/auth/logout_all` | Инкрементирует `token_version`, делая недействительными все ранее выданные токены. |
| `GET` | `/profile` | Возвращает email и данные профиля аутентифицированного пользователя. |
| `PATCH` | `/profile` | Частичное обновление профиля. При наличии Kafka публикует событие `user.profile.updated`. |
| `PUT` | `/profile/consents` | Перезапись маркетинговых и юридических согласий. |
| `GET` | `/healthz` | Проверка живости. |
| `GET` | `/readyz` | Проверка готовности. |
| `GET` | `/metrics` | Метрики Prometheus (через `src.common.metrics`). |

> Все эндпоинты, кроме `/auth/register` и `/auth/login`, требуют Bearer access-токен.

## Kafka-топики
| Направление | Топик | Пайлоад |
| --- | --- | --- |
| Produce | `user.profile.updated` | `{ "user_id": <int> }` отправляется после успешного `PATCH /profile`. Используется, когда задан `KAFKA_BROKERS`. |

## Конфигурация
Переменные читаются через `pydantic-settings` (регистр не важен, можно использовать `.env`).

| Переменная | Обязательна | Значение по умолчанию | Описание |
| --- | --- | --- | --- |
| `DATABASE_URL` | Да | – | URL базы данных SQLAlchemy. Пример для PostgreSQL: `postgresql+psycopg://user:pass@host:5432/db`. Для локальной отладки можно задать `sqlite:///./auth.db`. |
| `JWT_SECRET` | Нет | `secret` | Секрет для подписи JWT. Обязательно переопределите в продакшене. |
| `JWT_ALGORITHM` | Нет | `HS256` | Алгоритм подписи токенов. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Нет | `15` | Время жизни access-токена (в минутах). |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Нет | `30` | Время жизни refresh-токена (в днях). |
| `KAFKA_BROKERS` | Нет | – | Список брокеров Kafka/Redpanda через запятую. Включает отправку событий. |

## Подготовка базы данных
1. Установите зависимости проекта и запустите виртуальное окружение Poetry.
2. Выполните миграции Alembic из корня репозитория, указывая тот же DSN, что и в `DATABASE_URL`:
   ```bash
   poetry install
   export POSTGRES_DSN="postgresql+psycopg://cg:cg@localhost:5432/cityguide"
   poetry run alembic upgrade head
   ```
3. Убедитесь, что таблицы `users`, `profiles`, `consents` появились в целевой базе.

## Локальный запуск
1. Установите зависимости сервиса:
   ```bash
   cd services/auth_profile
   poetry install
   ```
2. Экспортируйте необходимые переменные окружения (можно через `.env`):
   ```bash
   export DATABASE_URL=postgresql+psycopg://cg:cg@localhost:5432/cityguide
   export KAFKA_BROKERS=localhost:9092  # опционально
   export JWT_SECRET="local-dev-secret"
   ```
3. Запустите приложение:
   ```bash
   poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
4. Откройте Swagger UI `http://localhost:8000/docs` для проверки эндпоинтов или получите метрики по адресу `http://localhost:8000/metrics`.

### Полезные команды
- `poetry run pytest` — запуск тестов сервиса.
- Подключение к БД: используйте `psql` или любой клиент с DSN из `DATABASE_URL`.

## Наблюдаемость
- Метрики Prometheus доступны по `/metrics` (`JOB_DURATION`, `KAFKA_CONSUMER_LAG`).
- Трассировка OpenTelemetry по умолчанию не включена, но интеграция возможна через общие утилиты `src.common.telemetry` при необходимости.

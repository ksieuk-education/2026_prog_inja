# Сервис такси (учебный REST API)

FastAPI, PostgreSQL, asyncpg. Пользователи, водители, поездки.

Документация по БД: [`docs/db/README.md`](docs/db/README.md).  
SQL: `schema.sql`, `data.sql`, `queries.sql` в корне.

## Запуск

```bash
cp .env.example .env
cp .configs/config.yaml.example .configs/config.yaml
docker compose up -d --build
```

Postgres на 5432, API на порту из `API_PORT` (обычно 8000). При первом старте накатываются `schema.sql` и `data.sql`.

```bash
curl http://localhost:8000/api/taxi/v1/health
curl http://localhost:8000/api/taxi/v1/users/by-login/client1
```

Swagger: http://localhost:8000/api/taxi/v1/docs

## API

Префикс `/api/taxi/v1`.

| Что | Метод |
|-----|--------|
| Регистрация / вход | `POST /auth/register`, `POST /auth/login` |
| Пользователь | `POST /users`, `GET /users/by-login/{login}`, `GET /users/search` |
| Водитель | `POST /drivers` (нужен JWT) |
| Поездка | `POST /trips`, `GET /trips/active`, `POST /trips/{id}/accept`, `POST /trips/{id}/complete` |
| История | `GET /users/{user_id}/trips/history` (JWT) |

Тексты запросов в [`queries.sql`](queries.sql).

## Локально без Docker

```bash
cd src
poetry install --no-root --with dev
export SETTINGS_PATH_ENV_NAME=/path/to/.configs/config.yaml
poetry run python -m bin
```

Postgres должен быть доступен (`docker compose up -d taxi-postgres` достаточно).

## Тесты

```bash
cd src
poetry run pytest tests/ -v
```

## Структура кода

- `lib/app/domain` — сущности
- `lib/infra/repositories` — запросы в Postgres
- `lib/present/api/routes` — роуты
- C4 — [`docs/readme.md`](docs/readme.md)

Нужны Python 3.13+, Poetry, Docker для полного стека.

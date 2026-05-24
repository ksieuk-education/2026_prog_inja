# Сервис такси (учебный REST API)

Учебный backend на **FastAPI**: пользователи, водители и заказы поездок. Данные хранятся в **PostgreSQL**, доступ к БД и транзакциям — через **Dishka** (Unit of Work на запрос). Время в ответах по `created_at` приводится к часовому поясу из настроек приложения (по умолчанию **UTC+3**).

## Запуск в Docker

В репозитории есть `docker-compose.yaml`: **taxi-postgres** (схема из `docker/postgres/initdb/`) и **app-client** (сборка из `src/Dockerfile`). Порт API пробрасывается через переменную **`API_PORT`** в `.env`.

```bash
cp .env.example .env
```

```bash
cp .configs/config.yaml.example .configs/config.yaml
```

## Возможности API

| Операция | Метод и путь (префикс `/api/taxi/v1`) |
|----------|----------------------------------------|
| Создание пользователя | `POST /users` |
| Поиск по логину | `GET /users/by-login/{login}` |
| Поиск по маске имени и фамилии | `GET /users/search?name_mask=...` |
| Регистрация водителя | `POST /drivers` |
| Создание заказа | `POST /trips` |
| Активные заказы | `GET /trips/active` |
| Принять заказ водителем | `POST /trips/{id}/accept` |
| История поездок пользователя | `GET /users/{user_id}/trips/history` |
| Завершить поездку | `POST /trips/{id}/complete` |

Интерактивная документация (Swagger UI): [http://localhost:8000/api/taxi/v1/docs](http://localhost:8000/api/taxi/v1/docs)

OpenAPI JSON: [http://localhost:8000/api/taxi/v1/openapi.json](http://localhost:8000/api/taxi/v1/openapi.json)

## Требования

- Python **3.13+**
- [Poetry](https://python-poetry.org/) (зависимости описаны в `src/pyproject.toml`)

## Локальный запуск

Рабочая директория для импорта пакета `lib` — каталог **`src`**.

```bash
cd src
poetry install --no-root --with dev
```

При необходимости укажите путь к YAML-конфигу: переменная окружения **`SETTINGS_PATH_ENV_NAME`** (имя задано в коде) должна содержать путь к файлу, например:

```bash
export SETTINGS_PATH_ENV_NAME=/absolute/path/to/repo/.configs/config.yaml
```

Несколько файлов можно задать через `:` в значении переменной. Вложенные поля настроек также пробрасываются через переменные окружения с разделителем **`__`** (см. `pydantic-settings`).

Запуск HTTP-сервера (хост и порт задаются в настройках, по умолчанию `0.0.0.0:8000`):

```bash
cd src
poetry run python -m bin
```

PostgreSQL по умолчанию: `localhost:5432`, БД `taxidb` (см. `database_settings` в конфиге и `.env.example`). DDL применяется при первом старте контейнера из `docker/postgres/initdb/`.


## Примеры вызовов API

Ниже базовый URL: `http://localhost:8000/api/taxi/v1`. Подставьте свои `id`, возвращаемые из ответов.

**1. Создать клиента и водителя (оба — пользователи)**

```bash
curl -sS -X POST http://localhost:8000/api/taxi/v1/users \
  -H "Content-Type: application/json" \
  -d '{"login":"client1","first_name":"Иван","last_name":"Петров"}'

curl -sS -X POST http://localhost:8000/api/taxi/v1/users \
  -H "Content-Type: application/json" \
  -d '{"login":"driver_user","first_name":"Алексей","last_name":"Волков"}'
```

**2. Найти пользователя по логину**

```bash
curl -sS "http://localhost:8000/api/taxi/v1/users/by-login/client1"
```

**3. Поиск по маске (подстрока в «имя фамилия», без `%` подстрока оборачивается в `%…%` на стороне сервера)**

```bash
curl -sS "http://localhost:8000/api/taxi/v1/users/search?name_mask=%Иван%"
```

**4. Зарегистрировать водителя** (`user_id` — id пользователя `driver_user`)

```bash
curl -sS -X POST http://localhost:8000/api/taxi/v1/drivers \
  -H "Content-Type: application/json" \
  -d '{"user_id":2}'
```

**5. Создать заказ** (`user_id` — клиент)

```bash
curl -sS -X POST http://localhost:8000/api/taxi/v1/trips \
  -H "Content-Type: application/json" \
  -d '{"user_id":1}'
```

**6. Список активных заказов**

```bash
curl -sS "http://localhost:8000/api/taxi/v1/trips/active"
```

**7. Принять заказ** (`trip_id`, `driver_id` из предыдущих шагов)

```bash
curl -sS -X POST "http://localhost:8000/api/taxi/v1/trips/1/accept" \
  -H "Content-Type: application/json" \
  -d '{"driver_id":1}'
```

**8. История поездок пользователя**

```bash
curl -sS "http://localhost:8000/api/taxi/v1/users/1/trips/history"
```

**9. Завершить поездку**

```bash
curl -sS -X POST "http://localhost:8000/api/taxi/v1/trips/1/complete"
```

Проверка доступности сервиса: `GET http://localhost:8000/api/taxi/v1/health`.

## Тесты

```bash
cd src
poetry run pytest tests/ -v
```

## Архитектура (кратко)

- `lib/application/dto` — Pydantic-модели запросов/ответов  
- `lib/present/api/routes` — FastAPI-роуты  
- `lib/app` — доменные сущности и контракты (UoW, репозитории)  
- `lib/infra` — PostgreSQL (asyncpg), репозитории; DDL в `docker/postgres/initdb/`  
- `lib/main` — настройки, DI (Dishka), точка входа веб-приложения  

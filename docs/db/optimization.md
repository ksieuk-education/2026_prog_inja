# EXPLAIN по запросам

Индексы заданы в [`schema.sql`](../../schema.sql), запросы — в [`queries.sql`](../../queries.sql).

Проверял на PostgreSQL 16, тестовые данные из `data.sql`. Перед замером:

```sql
ANALYZE users;
ANALYZE drivers;
ANALYZE trips;
```

Запуск:

```bash
docker compose up -d taxi-postgres
docker compose exec taxi-postgres psql -U user -d taxidb
```

## Поиск по логину

`GET /users/by-login/{login}`, `POST /auth/login`

```sql
SELECT id, login, first_name, last_name, password_hash
FROM users
WHERE lower(login) = lower('client1');
```

Индекс `idx_users_login_lower` (unique на `lower(login)`).

```
 Index Scan using idx_users_login_lower on users
   Index Cond: (lower((login)::text) = 'client1'::text)
   Execution Time: 0.130 ms
```

Идёт по индексу, seq scan не нужен.

## Поиск по имени

`GET /users/search?name_mask=...`

```sql
SELECT id, login, first_name, last_name, password_hash
FROM users
WHERE (first_name || ' ' || last_name) ILIKE '%Иван%'
ORDER BY last_name, first_name;
```

Индекс `idx_users_full_name_trgm` (GIN + `pg_trgm`).

На шести строках planner всё равно берёт seq scan — так дешевле:

```
 Seq Scan on users
   Filter: ((first_name || ' ' || last_name) ~~* '%Иван%')
   Execution Time: 0.084 ms
```

На большой таблице после `ANALYZE` обычно появляется bitmap scan по GIN.

## Активные заказы

`GET /trips/active`

```sql
SELECT id, user_id, driver_id, status, created_at
FROM trips
WHERE status IN ('pending', 'active')
ORDER BY created_at DESC;
```

Индекс `idx_trips_status_created (status, created_at DESC)`.

```
 Sort  (Sort Key: created_at DESC)
   ->  Bitmap Heap Scan on trips
         ->  Bitmap Index Scan on idx_trips_status_created
 Execution Time: 0.222 ms
```

Фильтр по индексу есть, сортировка отдельным шагом из‑за `IN (...)`.

## История поездок

`GET /users/{user_id}/trips/history`

```sql
SELECT id, user_id, driver_id, status, created_at
FROM trips
WHERE user_id = 1 AND status = 'completed'
ORDER BY created_at DESC;
```

Индекс `idx_trips_user_status_created`.

```
 Index Scan using idx_trips_user_status_created on trips
   Index Cond: ((user_id = 1) AND (status = 'completed'))
   Execution Time: 0.020 ms
```

Один проход по индексу, без отдельного sort.

## Принять / завершить поездку

`POST /trips/{id}/accept` — update по `id` и `status = 'pending'`:

```
 Update on trips
   ->  Index Scan using trips_pkey on trips
         Index Cond: (id = 4)
         Filter: (status = 'pending')
 Execution Time: 1.650 ms
```

Статус проверяется уже после поиска по PK. `complete` устроен так же, только `active` → `completed`.

## JOIN для отчёта

Из `queries.sql` — активные поездки с логинами клиента и водителя. Join идёт по PK/FK, отдельные индексы на `trips.user_id` и `drivers.user_id` для этого хватает.

## Все индексы

| Индекс | Зачем |
|--------|--------|
| users_pkey | PK |
| idx_users_login_lower | логин, unique |
| idx_users_full_name_trgm | ILIKE по ФИО |
| drivers_pkey | PK |
| drivers_user_id_unique | 1 user = 1 driver |
| trips_pkey | PK |
| idx_trips_user_id | FK, история |
| idx_trips_driver_id | FK |
| idx_trips_status | фильтр по статусу |
| idx_trips_created_at | сортировка по времени |
| idx_trips_status_created | активные заказы |
| idx_trips_user_status_created | история клиента |

Если понадобится ещё ужать планы: partial index на `trips` только для `pending`/`active`, или `INCLUDE (driver_id)` на индекс истории.

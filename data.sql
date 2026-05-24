-- после schema.sql

BEGIN;

INSERT INTO users (id, login, first_name, last_name, password_hash, created_at) VALUES
    (1, 'client1',  'Иван',    'Петров',   '', '2026-01-01 10:00:00+03'),
    (2, 'driver1',  'Алексей', 'Волков',   '', '2026-01-05 11:00:00+03'),
    (3, 'client2',  'Мария',   'Сидорова', '', '2026-01-08 12:00:00+03'),
    (4, 'admin',    'Анна',    'Кузнецова','', '2026-01-09 13:00:00+03'),
    (5, 'driver2',  'Дмитрий', 'Орлов',    '', '2026-01-10 14:00:00+03');

-- authtest / secret123
INSERT INTO users (id, login, first_name, last_name, password_hash) VALUES
    (
        6,
        'authtest',
        'Тест',
        'Авторизация',
        'a1b2c3d4e5f6789012345678abcdef01$dc90e97f83a2ca41b87988b00f841a13534fdc1c54f2c68eb041d77906dcc669'
    );

SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));

INSERT INTO drivers (id, user_id, registered_at) VALUES
    (1, 2, '2026-01-10 09:00:00+03'),
    (2, 5, '2026-01-15 14:30:00+03');

SELECT setval('drivers_id_seq', (SELECT MAX(id) FROM drivers));

INSERT INTO trips (id, user_id, driver_id, status, created_at) VALUES
    (1, 1, 1, 'completed', '2026-01-20 08:00:00+03'),
    (2, 1, 1, 'completed', '2026-01-22 18:30:00+03'),
    (3, 1, 2, 'active',    '2026-05-20 10:00:00+03'),
    (4, 3, NULL, 'pending', '2026-05-24 09:15:00+03'),
    (5, 3, NULL, 'pending', '2026-05-24 09:20:00+03'),
    (6, 3, 2, 'completed', '2026-01-25 12:00:00+03');

SELECT setval('trips_id_seq', (SELECT MAX(id) FROM trips));

COMMIT;

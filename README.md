# Effective — система аутентификации и авторизации

Backend-приложение на FastAPI с собственной реализацией аутентификации (JWT + сессии в БД) и гибкой ролевой моделью разграничения прав доступа.

---

## Содержание

- [Технологии](#технологии)
- [Архитектура](#архитектура)
- [Схема базы данных](#схема-базы-данных)
- [Система прав доступа](#система-прав-доступа)
- [API](#api)
- [Быстрый старт](#быстрый-старт)
- [Локальная разработка](#локальная-разработка)
- [Тестирование](#тестирование)
- [Переменные окружения](#переменные-окружения)

---

## Технологии

- **Python 3.12**
- **FastAPI** — веб-фреймворк
- **SQLAlchemy 2.0** (async) — ORM
- **PostgreSQL 16** — база данных
- **Alembic** — миграции схемы БД
- **PyJWT + bcrypt** — токены и хеширование паролей
- **Pydantic v2** — валидация данных
- **pytest + pytest-asyncio** — тестирование
- **uv** — управление зависимостями
- **Docker + Docker Compose** — контейнеризация

---

## Архитектура

Проект разбит на слои. Каждый слой знает только о слое ниже:

```
HTTP запрос
    ↓
Роут (app/api/v1/)              — принимает запрос, валидирует Pydantic схемами, возвращает HTTP ответ
    ↓
Dependencies (app/dependencies.py)  — идентификация пользователя, проверка прав
    ↓
Сервис (app/services/)          — бизнес-логика, не знает про HTTP
    ↓
Репозиторий (app/repositories/) — CRUD операции с БД, не знает про бизнес-логику
    ↓
PostgreSQL
```

Такое разделение позволяет тестировать каждый слой изолированно: сервисы тестируются с моками репозиториев (без БД), репозитории — с реальной тестовой БД, эндпоинты — через `AsyncClient` с подменой зависимостей.

### Структура проекта

```
.
├── app/
│   ├── api/v1/
│   │   ├── auth.py                    # регистрация, логин, логаут, профиль
│   │   ├── admin.py                   # управление ролями, правилами и пользователями
│   │   └── mock_resources.py          # mock-эндпоинты для демонстрации авторизации
│   ├── models/                        # SQLAlchemy модели (таблицы БД)
│   ├── repositories/                  # CRUD операции с БД
│   ├── services/
│   │   ├── auth_service.py            # регистрация, логин, логаут, профиль
│   │   ├── access_service.py          # управление ролями и правилами доступа
│   │   └── user_management_service.py # административное управление пользователями
│   ├── schemas/                       # Pydantic схемы входящих и исходящих данных
│   ├── utils/
│   │   ├── jwt.py                     # создание и декодирование токенов
│   │   └── password.py                # хеширование и проверка паролей
│   ├── dependencies.py                # get_current_user, require_permission, require_admin
│   ├── config.py                      # настройки через pydantic-settings
│   ├── database.py                    # async движок и фабрика сессий
│   ├── main.py                        # точка входа FastAPI
│   └── seed.py                        # начальные данные (идемпотентный)
├── tests/
│   ├── unit/                          # юнит-тесты (сервисы, утилиты, зависимости)
│   └── integration/                   # интеграционные тесты (репозитории, эндпоинты)
├── Dockerfile
├── docker-compose.yml
├── run.sh                             # миграции → seed → uvicorn
└── pyproject.toml
```

---

## Схема базы данных

```
users
──────────────────────────────────────────
id               UUID         PK
first_name       VARCHAR(100)
last_name        VARCHAR(100)
middle_name      VARCHAR(100) nullable
email            VARCHAR(255) unique
hashed_password  VARCHAR(255)
is_active        BOOLEAN      default=true
role_id          UUID         FK → roles.id
created_at       TIMESTAMPTZ
updated_at       TIMESTAMPTZ

roles
──────────────────────────────────────────
id               UUID         PK
name             ENUM(admin, manager, user, guest)  unique
description      TEXT         nullable

sessions
──────────────────────────────────────────
id               UUID         PK
user_id          UUID         FK → users.id
token            VARCHAR(512) unique
expires_at       TIMESTAMPTZ
created_at       TIMESTAMPTZ

business_elements
──────────────────────────────────────────
id               UUID         PK
name             ENUM(products, orders, users, access_rule)  unique
description      TEXT

access_rules
──────────────────────────────────────────
id               UUID         PK
role_id          UUID         FK → roles.id
element_id       UUID         FK → business_elements.id
can_read         BOOLEAN
can_read_all     BOOLEAN
can_create       BOOLEAN
can_update       BOOLEAN
can_update_all   BOOLEAN
can_delete       BOOLEAN
can_delete_all   BOOLEAN
```

---

## Система прав доступа

Авторизация построена на трёх сущностях: **роли**, **бизнес-элементы** и **правила доступа**.

### Роли

| Роль | Описание |
|---|---|
| `admin` | Полный доступ, управление системой |
| `manager` | Читает всё, редактирует и удаляет только своё |
| `user` | Базовый доступ, работает только со своими объектами |
| `guest` | Только чтение |

### Бизнес-элементы

Ресурсы приложения к которым применяются права: `products`, `orders`, `users`, `access_rule`.

### Правила доступа

Связывают роль с элементом и набором разрешений:

| Поле | Смысл |
|---|---|
| `can_read` | Читать свои объекты |
| `can_read_all` | Читать все объекты |
| `can_create` | Создавать объекты |
| `can_update` | Редактировать свои объекты |
| `can_update_all` | Редактировать все объекты |
| `can_delete` | Удалять свои объекты |
| `can_delete_all` | Удалять все объекты |

### Как работает проверка при каждом запросе

1. `get_current_user` извлекает токен из заголовка `Authorization: Bearer <token>`
2. Проверяет подпись токена через PyJWT
3. Ищет сессию в БД — если не найдена, токен считается инвалидированным (пользователь вышел)
4. Загружает пользователя и проверяет `is_active`
5. `require_permission` находит правило для пары `(role_id, element_name)` и проверяет нужное поле

Коды ответов при нарушениях:
- **401 Unauthorized** — нет токена, токен истёк, недействителен или сессия закрыта
- **403 Forbidden** — пользователь известен, но прав недостаточно

### Защиты системы

- Права роли `admin` нельзя изменить или удалить через API — защита от случайной самоблокировки
- Нельзя изменить роль или удалить другого администратора
- Нельзя удалить собственный аккаунт через admin-эндпоинт (для этого есть `DELETE /auth/me`)

---

## API

### Аутентификация `/auth`

| Метод | Путь | Описание | Требует токен |
|---|---|---|---|
| `POST` | `/auth/register` | Регистрация | — |
| `POST` | `/auth/login` | Вход, получение JWT | — |
| `POST` | `/auth/logout` | Выход, инвалидация токена | ✓ |
| `GET` | `/auth/me` | Профиль текущего пользователя | ✓ |
| `PATCH` | `/auth/me` | Обновление профиля | ✓ |
| `DELETE` | `/auth/me` | Мягкое удаление аккаунта | ✓ |

**Регистрация** `POST /auth/register`
```json
{
  "first_name": "Иван",
  "last_name": "Петров",
  "middle_name": "Сергеевич",
  "email": "user@example.com",
  "password": "password123",
  "password_confirm": "password123"
}
```

**Логин** `POST /auth/login`
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```
Ответ:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

**Обновление профиля** `PATCH /auth/me` — все поля опциональны
```json
{
  "first_name": "Фёдор",
  "last_name": "Кузнецов",
  "middle_name": "Иванович"
}
```

---

### Администрирование `/admin`

Все эндпоинты требуют роль `admin`.

**Управление правами доступа:**

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/admin/roles` | Список всех ролей |
| `GET` | `/admin/roles/{role_id}/rules` | Правила доступа для роли |
| `POST` | `/admin/rules` | Создать правило доступа |
| `PATCH` | `/admin/rules/{rule_id}` | Обновить правило (частично) |
| `DELETE` | `/admin/rules/{rule_id}` | Удалить правило |

**Управление пользователями:**

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/admin/users` | Список всех пользователей с ролями |
| `GET` | `/admin/users/{user_id}` | Получить пользователя по id |
| `PATCH` | `/admin/users/{user_id}/role` | Назначить роль пользователю |
| `DELETE` | `/admin/users/{user_id}` | Мягкое удаление пользователя |

**Создание правила** `POST /admin/rules`
```json
{
  "role_id": "uuid роли",
  "element_id": "uuid бизнес-элемента",
  "can_read": true,
  "can_read_all": false,
  "can_create": false,
  "can_update": false,
  "can_update_all": false,
  "can_delete": false,
  "can_delete_all": false
}
```

**Назначение роли** `PATCH /admin/users/{user_id}/role`
```json
{
  "role_id": "uuid новой роли"
}
```

---

### Mock-ресурсы `/mock`

Заглушки бизнес-объектов для демонстрации работы авторизации. Таблиц в БД нет — данные захардкожены. Смысл этих эндпоинтов — показать что система корректно проверяет права и возвращает 401/403 при нарушениях.

| Метод | Путь | Требуемое право |
|---|---|---|
| `GET` | `/mock/products` | `products` → `can_read` |
| `POST` | `/mock/orders` | `orders` → `can_create` |

---

## Быстрый старт

### Через Docker Compose

```bash
# 1. Клонировать репозиторий
git clone <repo_url>
cd effective

# 2. Запустить
docker compose up --build
```

При старте контейнера `api` автоматически выполняется `run.sh`:
1. Применяются миграции Alembic (`alembic upgrade head`)
2. Запускается идемпотентный seed — роли, правила доступа, тестовые пользователи
3. Стартует uvicorn на порту 8000

Приложение: `http://localhost:8000`

Документация Swagger: `http://localhost:8000/docs`

### Тестовые пользователи

| Email | Пароль | Роль |
|---|---|---|
| `admin_test@mail.ru` | `admin111` | admin |
| `manager_test@mail.ru` | `manager111` | manager |
| `user_test@mail.ru` | `user111` | user |

---

## Локальная разработка

```bash
# Установить зависимости включая dev инструменты
uv sync --extra dev

# Поднять только БД
docker compose up db db_test -d

# Применить миграции
uv run alembic upgrade head

# Заполнить начальными данными
uv run python -m app.seed

# Запустить с hot-reload
uv run uvicorn app.main:app --reload
```

### Создание новой миграции после изменения моделей

```bash
uv run alembic revision --autogenerate -m "some migration"
uv run alembic upgrade head
```

---

## Тестирование

Для интеграционных тестов используется отдельная БД (`testdb` на порту 5433). Каждый тест работает в изолированной транзакции которая откатывается после завершения — тесты не влияют друг на друга и могут запускаться в любом порядке.

```bash
# Поднять тестовую БД
docker compose up db_test -d

# Запустить все тесты
uv run pytest

# Только юнит-тесты (не требуют БД, быстро)
uv run pytest tests/unit/

# Только интеграционные тесты
uv run pytest tests/integration/

# С покрытием кода
uv run pytest --cov=app --cov-report=term-missing

# С подробным выводом
uv run pytest -v
```

### Что и как тестируется

```
tests/
├── unit/                                  без БД, используют моки
│   ├── test_password_utils.py             хеширование, проверка паролей
│   ├── test_jwt_utils.py                  создание токенов, истечение, подделка
│   ├── test_auth_service.py               регистрация, логин, логаут, профиль
│   ├── test_access_service.py             создание/изменение правил, защита admin
│   ├── test_user_managment_service.py     управление пользователями, защиты
│   └── test_dependencies.py               get_current_user, require_permission, require_admin
└── integration/                           с реальной тестовой БД
    ├── test_user_repo.py                  CRUD пользователей
    ├── test_role_repo.py                  CRUD ролей
    ├── test_session_repo.py               сессии, проверка истёкших токенов
    ├── test_access_rule_repo.py           правила доступа, JOIN запросы
    ├── test_auth_endpoints.py             HTTP: /auth/* эндпоинты
    ├── test_admin_endpoints.py            HTTP: /admin/rules/* эндпоинты
    ├── test_user_managment_endpoints.py   HTTP: /admin/users/* эндпоинты
    └── test_access_control.py             HTTP: 401/403 сценарии
```

---

## Переменные окружения

Файл `.env` в корне проекта:

```env
# PostgreSQL (используется приложением и docker-compose для сервиса db)
POSTGRES_HOST=db
POSTGRES_USER=appuser
POSTGRES_PASSWORD=apppass
POSTGRES_DB=authdb
POSTGRES_PORT=5432

# Тестовая БД (только для pytest, указывает на db_test контейнер)
DATABASE_URL_TEST=postgresql+asyncpg://appuser:apppass@localhost:5433/testdb

# JWT
JWT_SECRET=your-secret-key-change-in-production
JWT_EXPIRES_SECONDS=3600
```

> **Важно:** файл `.env` добавлен в `.gitignore`. Никогда не коммитьте реальные секреты в репозиторий. Для продакшна используйте переменные окружения платформы или секрет-менеджер.
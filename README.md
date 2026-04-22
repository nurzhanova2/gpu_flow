# GPUFlow

Backend + frontend для управления GPU-очередью и JupyterHub.

## Что реализовано
- FastAPI backend c JWT auth и ролями `user` / `admin`
- PostgreSQL через `docker-compose`
- Полноценные модели: `User`, `LaunchProfile`, `QueueItem`, `Session`, `Node`, `Alert`, `AuditLog`
- Async workers для симуляции кластера и lifecycle сессий
- Mock adapters для Slurm/JupyterHub/Metrics (готово к замене на реальные)
- Агрегированные API для user/admin dashboard
- WebSocket realtime stream: `queue.updated`, `session.updated`, `node.updated`
- Seed данные: 1 admin, 5 users, 3 GPU-ноды, очередь, сессии, алерты

## Стек
- FastAPI
- SQLAlchemy (async)
- Pydantic
- PostgreSQL (dev через Docker)
- Uvicorn
- asyncio workers

## Структура
```text
app/
  main.py
  config.py
  api/
    deps.py
    routes/
      auth.py
      user.py
      admin.py
  core/
    security.py
    realtime.py
  models/
    user.py
    session.py
    queue.py
    node.py
    alert.py
  schemas/
    user.py
    session.py
    queue.py
    dashboard.py
  services/
    queue_service.py
    session_service.py
    dashboard_service.py
    scheduler_service.py
  repositories/
    user_repo.py
    queue_repo.py
    session_repo.py
    node_repo.py
  integrations/
    slurm/base.py
    slurm/mock.py
    jupyterhub/base.py
    jupyterhub/mock.py
    metrics/base.py
    metrics/mock.py
  workers/
    queue_worker.py
    session_worker.py
  db/
    base.py
    session.py
  seed/
    seed_data.py
```

## Запуск backend через Docker Compose
1. Убедитесь, что Docker daemon запущен.
2. Запустите:
```bash
docker compose up --build
```
3. Backend доступен на `http://localhost:8000`.
   Порты публикуются только на `127.0.0.1` (dev-safe), внешние подключения отсекаются.

Health check:
```bash
curl http://localhost:8000/health
```

## Учетные записи seed
- admin:
  - username: `admin`
  - password: `admin123`
- user:
  - username: `demo`
  - password: `user12345`

Если у вас уже была старая volume БД, seed-пароли могли сохраниться от прошлой версии.
Для чистого пересида:

```bash
docker compose down -v
docker compose up --build
```

## Auth flow
Получить JWT:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

Регистрация пользователя:
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"newuser","full_name":"New User","email":"newuser@gpuflow.local","team":"NLP","password":"StrongPass123"}'
```
Требования к паролю: 8..128 символов, обязательно буквы и цифры.

## Основные endpoint'ы
### User
- `GET /api/v1/dashboard/user`
- `POST /api/v1/sessions/launch`
- `POST /api/v1/queue/{id}/cancel`
- `POST /api/v1/sessions/{id}/relaunch`
- `GET /api/v1/sessions/{id}/access`

### Admin
- `GET /api/v1/dashboard/admin`
- `POST /api/v1/admin/queue/{id}/promote`
- `DELETE /api/v1/admin/queue/{id}`
- `POST /api/v1/admin/sessions/{id}/terminate`
- `POST /api/v1/admin/sessions/{id}/warn`
- `PATCH /api/v1/admin/users/{id}/limits`
- `POST /api/v1/admin/users/{id}/block`
- `POST /api/v1/admin/users/{id}/unblock`


### Realtime
- `WS /api/v1/stream`
  - браузерный клиент передает JWT через websocket subprotocol `bearer.<token>`
  - для non-browser клиентов поддерживается `Authorization: Bearer <JWT>`
  - heartbeat обязателен (`{"type":"ping"}`), сервер отвечает `{"type":"pong"}`
  - попытки подключения без токена отклоняются (`403/1008`) — это ожидаемо

## Dev-параметры
Все настройки задаются через `.env` и `docker-compose.yml`.
Ключевые параметры:
- `DATABASE_URL`
- `JWT_SECRET`
- `LOGIN_MAX_ATTEMPTS`
- `LOGIN_LOCKOUT_SECONDS`
- `ALLOW_USER_REGISTRATION`
- `STRICT_PRODUCTION_CHECKS`
- `SLURM_MODE=mock`
- `JUPYTERHUB_MODE=mock`
- `METRICS_MODE=mock`
- `QUEUE_TICK_SECONDS`
- `SESSION_TICK_SECONDS`
- `WORKERS_ENABLED`
- `WORKERS_USE_DB_LOCK`
- `SESSION_IDLE_TIMEOUT_SECONDS`
- `SESSION_MAX_RUNTIME_SECONDS`
- `QUEUE_START_TIMEOUT_SECONDS`
- `WS_HEARTBEAT_TIMEOUT_SECONDS`
- `WS_AUTH_RECHECK_SECONDS`
- `CORS_ALLOW_ORIGINS`
- `SEED_SYNC_EXISTING_USERS`

## Что остается для prod-интеграции
1. Реализовать production adapters вместо:
   - `app/integrations/slurm/mock.py`
   - `app/integrations/jupyterhub/mock.py`
   - `app/integrations/metrics/mock.py`
2. Выставить production env:
   - `APP_ENV=prod`
   - `JWT_SECRET=<strong-random-secret>`
   - `SEED_ON_STARTUP=false`
   - `ALLOW_USER_REGISTRATION=false` (или оставить true осознанно)
   - `SLURM_MODE`, `JUPYTERHUB_MODE`, `METRICS_MODE` не `mock`

3. Подставить реальные URL/токены в `.env`.
4. Не требуется переписывать API, модели или сервисный слой.

## Frontend
Запуск фронтенда:
```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

## Проверки перед продом
1. Регрессионные backend-тесты:
```bash
docker compose exec -e WORKERS_ENABLED=false -e SEED_ON_STARTUP=false api python -m unittest -v tests.test_regressions
```
2. Live readiness тесты (auth, dashboard, queue, admin actions, websocket, проверка отсутствия mock-данных на фронте):
```bash
docker compose exec api python -m unittest -v tests.test_prod_readiness

```

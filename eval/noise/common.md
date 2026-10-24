Ты разрабатываешь новый платформенный сервис `services/{SVC}/` в существующем проекте ERP коммерческой библиотеки (Python 3.14, FastAPI, async SQLAlchemy, PostgreSQL, события через transactional outbox). Работай полностью автономно, вопросов не задавай.

## Сначала изучи
- `libs/` целиком: `db.py`, `events/`, `clock.py`, `errors.py`, `web.py`, `settings.py`;
- `services/scheduling/` как образец стиля (models, service, consumers, jobs, api, app);
- `tests/conftest.py` и `tests/factories.py` (как поднимается БД, замораживается время `T0`, доставляются события).

## Границы
Создавать и менять можно ТОЛЬКО:
- `services/{SVC}/**`;
- `tests/test_{SVC}_*.py` и `tests/{SVC}_factories.py`;
- `migrations/noise/{SVC}.sql`.

Запрещено:
- импортировать `services.applications`, `services.billing`, `services.scheduling`, `services.notifications`, `services.chat`;
- подписываться на их топики и ссылаться на их таблицы;
- менять `libs/`, `bpm/`, `migrations/versions/`, `services/wiring.py`, `tests/conftest.py`, `tests/factories.py`, `pyproject.toml`;
- запускать docker и менять порты. БД уже доступна через переменную окружения `DATABASE_URL`.

## Что должно быть в сервисе
- `migrations/noise/{SVC}.sql`: `CREATE SCHEMA {SVC};`, таблицы, CHECK, UNIQUE и частичные уникальные индексы, минимум 2 триггера на plpgsql (тело функции между `$$`, каждая команда заканчивается `;` в конце строки). Файл применяется миграцией `0000` автоматически.
- ORM-модели на `libs.db.Base` со `__table_args__ = {"schema": "{SVC}"}`.
- `service.py` с бизнес-правилами (ошибки — `DomainError`, `AccessDenied`, `NotFound`, сообщения на русском).
- События: публикуй через `libs.events.publish` топики вида `{SVC}.<что-то>`. Подписчики — в `services/{SVC}/consumers.py` через `@subscribe`, только на топики своего сервиса. Минимум 4 топика и 4 подписчика, хотя бы одна цепочка «действие → событие → подписчик → новое событие → подписчик».
- `jobs.py` — минимум одна фоновая задача с параметром `now`.
- `settings.py` — константы сервиса (сроки, лимиты).
- `api.py` (APIRouter) и `app.py` по образцу ядра. `consumers.py` подключается автоматически.

## Тесты
`tests/test_{SVC}_*.py`, 20–30 тестов, фабрики — в `tests/{SVC}_factories.py`.
- Общий `conftest` уже поднимает БД, чистит все таблицы и замораживает время на `tests.factories.T0`.
- Данные своего сервиса создавай сам.
- События доставляет `libs.events.dispatch_pending()`.

## Объём и стиль
1800–2500 строк Python и SQL вместе с тестами. Код реалистичный, как у живой команды; комментарии умеренно. Обязательные элементы ниже реализуй как естественную часть домена, никак их особо не выделяя и не комментируя, зачем они.

## Готово, когда
- `uv run pytest tests/test_{SVC}_*.py -q -p no:cacheprovider` зелёный;
- `uv run ruff check services/{SVC} tests` чистый;
- полный `uv run pytest -q -p no:cacheprovider` зелёный.

В конце выведи одной строкой: число строк кода сервиса, тестов и SQL.

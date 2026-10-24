<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# subscriptions.subscriptions
Миграция: `subscriptions.subscriptions`

## Поля
- id: integer NOT NULL PK
- client_ref: character varying NOT NULL
- plan_id: integer NOT NULL
- status: character varying NOT NULL
- holder_name: character varying NOT NULL
- passport: character varying
- birth_date: date
- holder_check: character varying NOT NULL
- employer_ref: character varying
- paid_until: date
- reminded_for: date
- created_at: timestamp with time zone NOT NULL
- activated_at: timestamp with time zone
- closed_at: timestamp with time zone

## Связи (FK)
- plan_id → subscriptions.plans
- subscriptions.invoices.subscription_id → сюда
- subscriptions.notices.subscription_id → сюда
- subscriptions.refunds.subscription_id → сюда
- subscriptions.status_history.subscription_id → сюда

## Ограничения и триггеры
- ck_subscriptions_closed (check на subscriptions.subscriptions): CHECK ((((status)::text = ANY ((ARRAY['expired'::character varying, 'closed_duplicate'::character varying])::…
- ck_subscriptions_holder_check (check на subscriptions.subscriptions): CHECK (((holder_check)::text = ANY ((ARRAY['pending'::character varying, 'verified'::character varying, 'reje…
- ck_subscriptions_paid_until (check на subscriptions.subscriptions): CHECK ((((status)::text = ANY ((ARRAY['pending'::character varying, 'expired'::character varying, 'closed_dup…
- ck_subscriptions_status (check на subscriptions.subscriptions): CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'active'::character varying, 'grace'::char…
- ix_subscriptions_client (index на subscriptions.subscriptions): CREATE INDEX ix_subscriptions_client ON subscriptions.subscriptions USING btree (client_ref)
- uq_subscriptions_one_active (partial_unique_index на subscriptions.subscriptions): CREATE UNIQUE INDEX uq_subscriptions_one_active ON subscriptions.subscriptions USING btree (client_ref, plan_…
- trg_subscriptions_log_status: AFTER UPDATE OF status ON subscriptions.subscriptions FOR EACH ROW EXECUTE FUNCTION subscriptions.subscriptions_log_sta…
  - subscriptions_log_status(): BEGIN IF NEW.status IS DISTINCT FROM OLD.status THEN INSERT INTO subscriptions.status_history (subs…
- trg_subscriptions_terminal_guard: BEFORE UPDATE OF status ON subscriptions.subscriptions FOR EACH ROW EXECUTE FUNCTION subscriptions.subscriptions_termin…
  - subscriptions_terminal_guard(): 'subscription % is closed (%)'

## ORM
- services/subscriptions/models.py::Subscription:25 (orm_model)

## Пишут (код)
- services/subscriptions/jobs.py::expire_overdue [closed_at, status]
- services/subscriptions/jobs.py::expire_stale_pending [closed_at, status]
- services/subscriptions/service.py::apply_payment [activated_at, paid_until, status]
- services/subscriptions/service.py::create_subscription
- services/subscriptions/service.py::recheck_holder [holder_check]
- services/subscriptions/service.py::update_holder [holder_check]

## Правила
- R-SUBSCRIPTIONS-ACTIVATE-01 [draft] Абонемент активируется только после полной оплаты первого счёта
- R-SUBSCRIPTIONS-CREATE-01 [draft] Организация-работодатель указывается только для корпоративного тарифа и для него обязательна
- R-SUBSCRIPTIONS-CREATE-02 [draft] У клиента не может быть двух действующих абонементов на один тариф
- R-SUBSCRIPTIONS-CREATE-03 [draft] Клиент может держать не больше трёх неоплаченных абонементов
- R-SUBSCRIPTIONS-CREATE-04 [draft] Новый абонемент создаётся неоплаченным, и на него сразу выставляется счёт за первый месяц
- R-SUBSCRIPTIONS-DEDUP-01 [draft] При активации закрываются другие открытые абонементы клиента того же направления
- R-SUBSCRIPTIONS-GRACE-01 [draft] После окончания оплаченного месяца абонемент переходит в льготный период (grace)
- R-SUBSCRIPTIONS-GRACE-02 [draft] Через 30 дней после paid_until неоплаченный абонемент закрывается (срок задан литералом)
- R-SUBSCRIPTIONS-HOLDER-02 [draft] Сверка держателя отклоняет абонемент без паспорта или даты рождения при любом тарифе
- R-SUBSCRIPTIONS-HOLDER-03 [draft] При сверке социального абонемента возраст держателя проверяется заново на текущую дату
- R-SUBSCRIPTIONS-HOLDER-04 [draft] Данные держателя меняет только владелец незакрытого абонемента
- R-SUBSCRIPTIONS-HOLDER-05 [draft] Изменение данных держателя отправляет абонемент на повторную сверку
- R-SUBSCRIPTIONS-PENDING-01 [draft] Неоплаченный новый абонемент закрывается через 14 дней
- R-SUBSCRIPTIONS-PLAN-02 [draft] Архивный тариф не продаётся и не показывается, но действующие абонементы на нём продлеваются
- R-SUBSCRIPTIONS-REFUND-01 [draft] Оплата, пришедшая на закрытый абонемент, подлежит возврату
- R-SUBSCRIPTIONS-REMIND-01 [draft] Напоминание перед концом льготного периода не реализовано
- R-SUBSCRIPTIONS-RENEWAL-02 [draft] Оплата продления продлевает paid_until и возвращает абонемент из grace в active
- R-SUBSCRIPTIONS-SOCIAL-02 [draft] Социальный тариф доступен держателям не старше 23 лет или от 60 лет
- R-SUBSCRIPTIONS-STATUS-01 [draft] Закрытый абонемент нельзя открыть снова (триггер БД)
- R-SUBSCRIPTIONS-STATUS-02 [draft] У действующего абонемента всегда есть paid_until
- R-SUBSCRIPTIONS-STATUS-03 [draft] Журнал смены статусов абонемента пишет триггер БД

<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# partners.contracts
Миграция: `partners.contracts`

## Поля
- id: integer NOT NULL PK
- partner_id: integer NOT NULL
- number: text NOT NULL
- commission_pct: numeric NOT NULL
- credit_allowed: boolean NOT NULL
- credit_limit: numeric NOT NULL
- status: text NOT NULL
- suspend_reason: text
- valid_from: date NOT NULL
- valid_to: date NOT NULL
- activated_at: timestamp with time zone
- created_at: timestamp with time zone NOT NULL

## Связи (FK)
- partner_id → partners.partners
- partners.commissions.contract_id → сюда
- partners.contract_history.contract_id → сюда
- partners.deals.contract_id → сюда

## Ограничения и триггеры
- contracts_check (check на partners.contracts): CHECK ((valid_to >= valid_from))
- contracts_check1 (check на partners.contracts): CHECK ((credit_allowed OR (credit_limit = (0)::numeric)))
- contracts_check2 (check на partners.contracts): CHECK (((status <> 'suspended'::text) OR (suspend_reason IS NOT NULL)))
- contracts_commission_pct_check (check на partners.contracts): CHECK (((commission_pct >= (0)::numeric) AND (commission_pct <= (100)::numeric)))
- contracts_credit_limit_check (check на partners.contracts): CHECK ((credit_limit >= (0)::numeric))
- contracts_status_check (check на partners.contracts): CHECK ((status = ANY (ARRAY['draft'::text, 'active'::text, 'suspended'::text, 'expired'::text, 'terminated'::…
- ux_contracts_partner_current (partial_unique_index на partners.contracts): CREATE UNIQUE INDEX ux_contracts_partner_current ON partners.contracts USING btree (partner_id) WHERE (status…
- trg_contract_history: AFTER UPDATE ON partners.contracts FOR EACH ROW EXECUTE FUNCTION partners.log_contract_change()
  - log_contract_change(): BEGIN IF NEW.commission_pct IS DISTINCT FROM OLD.commission_pct THEN INSERT INTO partners.contract_…
- trg_contract_requisites: BEFORE UPDATE OF status ON partners.contracts FOR EACH ROW EXECUTE FUNCTION partners.check_partner_requisites()
  - check_partner_requisites(): 'partner % has incomplete requisites'
- contracts_number_key (unique на partners.contracts): UNIQUE (number)

## ORM
- services/partners/models.py::Contract:47 (orm_model)

## Пишут (код)
- services/partners/service.py::activate_contract [activated_at, status]
- services/partners/service.py::change_commission_rate [commission_pct]
- services/partners/service.py::expire_contract [status, suspend_reason]
- services/partners/service.py::onboard
- services/partners/service.py::renew_contract
- services/partners/service.py::resume_if_settled [status, suspend_reason]
- services/partners/service.py::set_credit_terms [credit_allowed, credit_limit]
- services/partners/service.py::suspend_contract [status, suspend_reason]
- services/partners/service.py::terminate_contract [status, suspend_reason]

## Правила
- R-PARTNERS-CONTRACT-01 [draft] У партнёра не больше одного текущего договора
- R-PARTNERS-CONTRACT-02 [draft] Договор активируется только из черновика при заполненных реквизитах и в сроке
- R-PARTNERS-CONTRACT-03 [draft] Ставка комиссии от 0 до MAX_COMMISSION_PCT, только на текущем договоре
- R-PARTNERS-CONTRACT-04 [draft] Кредитный лимит от 0 до MAX_CREDIT_LIMIT; без кредита лимит обнуляется
- R-PARTNERS-CONTRACT-05 [draft] Договор с истёкшим сроком переводится в expired
- R-PARTNERS-CONTRACT-06 [draft] Расторжение договора требует причины и отсутствия открытых сделок и долга
- R-PARTNERS-CONTRACT-07 [draft] Изменения условий договора журналируются триггером БД
- R-PARTNERS-CONTRACT-08 [draft] Приостановленный договор обязан иметь причину
- R-PARTNERS-CONTRACT-09 [draft] Новый договор создаётся на условиях последнего, если нет текущего
- R-PARTNERS-CREDIT-03 [draft] Просрочка оплаты кредитной сделки приостанавливает договор
- R-PARTNERS-CREDIT-04 [draft] Договор возобновляется после оплаты всех просроченных сделок
- R-PARTNERS-ONBOARD-01 [draft] Одобрение заявки заводит партнёра и черновик договора
- R-PARTNERS-ONBOARD-03 [draft] Номер договора формируется по ИНН, id партнёра и порядковому номеру

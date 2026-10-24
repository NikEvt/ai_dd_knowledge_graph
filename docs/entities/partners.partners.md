<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# partners.partners
Миграция: `partners.partners`

## Поля
- id: integer NOT NULL PK
- inn: text NOT NULL
- kpp: text
- legal_name: text
- contact_name: text
- contact_email: text
- contact_phone: text
- manager_id: integer NOT NULL
- created_at: timestamp with time zone NOT NULL
- updated_at: timestamp with time zone NOT NULL

## Связи (FK)
- partners.commissions.partner_id → сюда
- partners.contracts.partner_id → сюда
- partners.payouts.partner_id → сюда

## Ограничения и триггеры
- partners_contact_email_check (check на partners.partners): CHECK ((contact_email ~~ '%_@_%'::text))
- partners_inn_check (check на partners.partners): CHECK ((inn ~ '^[0-9]{10}$'::text))
- partners_kpp_check (check на partners.partners): CHECK ((kpp ~ '^[0-9]{9}$'::text))
- partners_legal_name_check (check на partners.partners): CHECK (((legal_name IS NULL) OR (length(btrim(legal_name)) > 0)))
- partners_inn_key (unique на partners.partners): UNIQUE (inn)

## ORM
- services/partners/models.py::Partner:31 (orm_model)

## Пишут (код)
- services/partners/service.py::onboard [updated_at]
- services/partners/service.py::update_requisites [updated_at]

## Правила
- R-PARTNERS-ONBOARD-01 [draft] Одобрение заявки заводит партнёра и черновик договора
- R-PARTNERS-REQUEST-01 [draft] Заявку на подключение принимают только с корректным ИНН
- R-PARTNERS-REQUEST-02 [draft] КПП, если указан, должен состоять из 9 цифр
- R-PARTNERS-REQUISITES-01 [draft] Менеджер правит только разрешённые реквизиты партнёра
- R-PARTNERS-REQUISITES-02 [draft] Нельзя очистить обязательные реквизиты при действующем договоре

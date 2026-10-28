<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# partners.onboarding_requests
Миграция: `partners.onboarding_requests`

## Поля
- id: integer NOT NULL PK
- inn: text NOT NULL
- kpp: text
- legal_name: text
- contact_name: text NOT NULL
- contact_email: text NOT NULL
- contact_phone: text
- status: text NOT NULL
- submitted_at: timestamp with time zone NOT NULL
- decided_at: timestamp with time zone
- decided_by: integer
- reject_reason: text
- partner_id: integer

## Ограничения и триггеры
- onboarding_requests_check (check на partners.onboarding_requests): CHECK (((status <> 'rejected'::text) OR (reject_reason IS NOT NULL)))
- onboarding_requests_check1 (check на partners.onboarding_requests): CHECK (((status = 'open'::text) OR (decided_at IS NOT NULL)))
- onboarding_requests_contact_email_check (check на partners.onboarding_requests): CHECK ((contact_email ~~ '%_@_%'::text))
- onboarding_requests_inn_check (check на partners.onboarding_requests): CHECK ((inn ~ '^[0-9]{10}$'::text))
- onboarding_requests_kpp_check (check на partners.onboarding_requests): CHECK ((kpp ~ '^[0-9]{9}$'::text))
- onboarding_requests_status_check (check на partners.onboarding_requests): CHECK ((status = ANY (ARRAY['open'::text, 'approved'::text, 'rejected'::text, 'duplicate'::text, 'expired'::t…
- ux_onboarding_requests_open_inn (partial_unique_index на partners.onboarding_requests): CREATE UNIQUE INDEX ux_onboarding_requests_open_inn ON partners.onboarding_requests USING btree (inn) WHERE (…

## ORM
- services/partners/models.py::OnboardingRequest:12 (orm_model)

## Пишут (код)
- services/partners/jobs.py::expire_requests [decided_at, status]
- services/partners/service.py::_decide [decided_at, decided_by]
- services/partners/service.py::approve_request [status]
- services/partners/service.py::link_request [partner_id]
- services/partners/service.py::reject_request [reject_reason, status]
- services/partners/service.py::submit_request

## Правила
- R-PARTNERS-ONBOARD-01 Одобрение заявки заводит партнёра и черновик договора (подкреплено кодом и тестами)
- R-PARTNERS-ONBOARD-02 Заявка связывается с партнёром после онбординга (⚠ без тестов)
- R-PARTNERS-REQUEST-01 Заявку на подключение принимают только с корректным ИНН (подкреплено кодом и тестами)
- R-PARTNERS-REQUEST-02 КПП, если указан, должен состоять из 9 цифр (⚠ без тестов)
- R-PARTNERS-REQUEST-03 Подключённый партнёр не может подать новую заявку (подкреплено кодом и тестами)
- R-PARTNERS-REQUEST-04 Новая заявка с тем же ИНН закрывает открытые как дубли (подкреплено кодом и тестами)
- R-PARTNERS-REQUEST-05 В БД не больше одной открытой заявки на ИНН (подкреплено кодом и тестами)
- R-PARTNERS-REQUEST-06 Решение по заявке принимается один раз (подкреплено кодом и тестами)
- R-PARTNERS-REQUEST-07 Отказ по заявке требует причины (подкреплено кодом и тестами)
- R-PARTNERS-REQUEST-08 Заявка без решения истекает через ONBOARDING_REQUEST_TTL_DAYS (подкреплено кодом и тестами)

<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# billing.fines
Миграция: [`migrations/versions/0001_initial.py:152`](../../migrations/versions/0001_initial.py#L152)

## Поля
- id: integer NOT NULL PK
- application_id: integer NOT NULL
- loan_id: integer
- kind: text NOT NULL
- amount: numeric NOT NULL
- status: text NOT NULL
- paid_outside: boolean NOT NULL
- created_at: timestamp with time zone NOT NULL

## Связи (FK)
- billing.invoices.fine_id → сюда

## Ограничения и триггеры
- fines_amount_check (check на billing.fines): CHECK ((amount >= (0)::numeric)) (migrations/versions/0001_initial.py:157)
- fines_kind_check (check на billing.fines): CHECK ((kind = ANY (ARRAY['overdue'::text, 'lost'::text, 'damaged'::text]))) (migrations/versions/0001_initial.py:156)
- fines_status_check (check на billing.fines): CHECK ((status = ANY (ARRAY['open'::text, 'paid'::text]))) (migrations/versions/0001_initial.py:158)

## ORM
- services/billing/models.py::Fine:21 (orm_model)

## Пишут (код)
- services/billing/service.py::create_fine
- services/billing/service.py::link_payment [status]
- services/billing/service.py::mark_fine_paid_outside [paid_outside, status]

## Правила
- R-BILL-FINE-01 Просрочка, утеря и порча книги автоматически создают штраф (⚠ без тестов)
- R-BILL-FINE-02 Размер штрафа берётся из ставки по представителю, площадке и виду (⚠ расхождение со схемой или открытый вопрос)
- R-BILL-FINE-03 Штраф бывает только «открыт» или «оплачен» (⚠ без тестов)
- R-BILL-FINE-OUTSIDE-01 Штраф по заявке в долг гасит закреплённый оператор вне системы (проверено человеком)
- R-BILL-FINE-PAY-01 Полная оплата счёта на штраф гасит штраф (⚠ расхождение со схемой или открытый вопрос)
- R-BILL-PAYMENT-01 Платёж нельзя привязать к аннулированному счёту (⚠ без тестов)
- R-BILL-PAYMENT-03 Привязка платежа фиксирует, кто привязал; переплата помечается флагом (⚠ расхождение со схемой или открытый вопрос)
- R-BILL-PAYMENT-04 Полная оплата публикуется один раз — когда сумма впервые достигает суммы счёта (подкреплено кодом и тестами)

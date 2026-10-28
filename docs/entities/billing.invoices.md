<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# billing.invoices
Миграция: [`migrations/versions/0001_initial.py:163`](../../migrations/versions/0001_initial.py#L163)

## Поля
- id: integer NOT NULL PK
- application_id: integer NOT NULL
- kind: text NOT NULL
- fine_id: integer
- amount: numeric NOT NULL
- status: text NOT NULL
- issued_at: timestamp with time zone NOT NULL
- payment_clock_started_at: timestamp with time zone NOT NULL
- venue_id: integer NOT NULL
- requisites: jsonb NOT NULL
- cancel_reason: text

## Связи (FK)
- fine_id → billing.fines
- billing.payments.invoice_id → сюда

## Ограничения и триггеры
- invoices_amount_check (check на billing.invoices): CHECK ((amount > (0)::numeric)) (migrations/versions/0001_initial.py:168)
- invoices_check (check на billing.invoices): CHECK (((kind = 'fine'::text) = (fine_id IS NOT NULL))) (migrations/versions/0001_initial.py:175)
- invoices_kind_check (check на billing.invoices): CHECK ((kind = ANY (ARRAY['books'::text, 'fine'::text]))) (migrations/versions/0001_initial.py:166)
- invoices_status_check (check на billing.invoices): CHECK ((status = ANY (ARRAY['active'::text, 'cancelled'::text]))) (migrations/versions/0001_initial.py:169)
- uq_invoices_one_active_books (partial_unique_index на billing.invoices): CREATE UNIQUE INDEX uq_invoices_one_active_books ON billing.invoices USING btree (application_id) WHERE ((kin… (migrations/versions/0001_initial.py:177)
- trg_invoices_cancel_guard: BEFORE UPDATE OF status ON billing.invoices FOR EACH ROW EXECUTE FUNCTION billing.forbid_cancel_paid_invoice() (migrations/versions/0001_initial.py:212)
  - forbid_cancel_paid_invoice(): 'invoice % has a linked payment'

## ORM
- services/billing/models.py::Invoice:35 (orm_model)

## Пишут (код)
- services/billing/consumers.py::on_unarchived [payment_clock_started_at]
- services/billing/service.py::cancel_invoice [cancel_reason, status]
- services/billing/service.py::issue_books_invoice
- services/billing/service.py::issue_fine_invoice

## Правила
- R-APP-ADMIN-02 Реквизиты площадки задаёт администратор; без них счёт не выставить (⚠ расхождение со схемой или открытый вопрос)
- R-APP-CALC-01 Стоимость книг заявки — сумма цен прайса текущей площадки, надбавку берёт billing у представителя (подкреплено кодом и тестами)
- R-APP-UNARCHIVE-03 После возврата из архива счёт аннулируется при изменении суммы, иначе срок оплаты отсчитывается заново
 (⚠ расхождение со схемой или открытый вопрос)
- R-BILL-ASSIGN-03 Счёт выставляет только бухгалтер, закреплённый за заявкой (подкреплено кодом и тестами)
- R-BILL-CANCEL-01 Счёт с привязанным платежом аннулировать нельзя (проверено человеком)
- R-BILL-CANCEL-02 Аннулирование уже аннулированного счёта ничего не делает (⚠ расхождение со схемой или открытый вопрос)
- R-BILL-CANCEL-03 Аннулирование счёта за книги возвращает заявку в «Ожидает счёта» (подкреплено кодом и тестами)
- R-BILL-DUPLICATE-01 Закрытие заявки как дубля аннулирует все её неоплаченные счета (⚠ расхождение со схемой или открытый вопрос)
- R-BILL-FINE-INVOICE-01 Счёт на штраф выставляет закреплённый бухгалтер на реквизиты площадки (⚠ расхождение со схемой или открытый вопрос)
- R-BILL-FINE-INVOICE-02 По заявке в долг счёт на штраф не выставляется (⚠ без тестов)
- R-BILL-INVOICE-01 Счёт за книги выставляется только по платной заявке (подкреплено кодом и тестами)
- R-BILL-INVOICE-02 Счёт за книги выставляется только на этапе «Ожидает счёта» (подкреплено кодом и тестами)
- R-BILL-INVOICE-03 Без реквизитов организации площадки счёт не выставить (подкреплено кодом и тестами)
- R-BILL-INVOICE-04 Сумма счёта за книги = цена по прайсу площадки + надбавка представителя (подкреплено кодом и тестами)
- R-BILL-INVOICE-05 Счёт сохраняет площадку и снимок её реквизитов (⚠ без тестов)
- R-BILL-INVOICE-06 У заявки не больше одного действующего счёта за книги (подкреплено кодом и тестами)
- R-BILL-INVOICE-07 Вид счёта — books или fine; счёт на штраф ссылается на штраф (⚠ без тестов)
- R-BILL-INVOICE-08 Выставление счёта за книги переводит заявку в «Ожидает оплаты» (проверено человеком)
- R-BILL-PAYMENT-02 Оплаченная сумма — сумма действующих платежей без отвязанных и возвращённых (подкреплено кодом и тестами)
- R-BILL-UNARCHIVE-01 При возврате из архива счёт аннулируется, только если сумма изменилась (⚠ расхождение со схемой или открытый вопрос)
- R-BILL-VENUE-CHANGE-01 Смена площадки аннулирует неоплаченный счёт за книги (⚠ расхождение со схемой или открытый вопрос)

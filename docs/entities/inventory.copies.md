<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# inventory.copies
Миграция: `inventory.copies`

## Поля
- id: integer NOT NULL PK
- inventory_no: text NOT NULL
- book_ref: integer NOT NULL
- venue_id: integer NOT NULL
- state: text NOT NULL
- acquired_at: timestamp with time zone NOT NULL
- updated_at: timestamp with time zone NOT NULL

## Связи (FK)
- inventory.ill_loans.copy_id → сюда
- inventory.transfers.copy_id → сюда
- inventory.write_offs.copy_id → сюда

## Ограничения и триггеры
- copies_state_check (check на inventory.copies): CHECK ((state = ANY (ARRAY['available'::text, 'on_loan'::text, 'in_transit'::text, 'lost'::text, 'damaged'::t…
- ix_copies_book_venue (index на inventory.copies): CREATE INDEX ix_copies_book_venue ON inventory.copies USING btree (book_ref, venue_id)
- trg_copies_transfer_lock: BEFORE UPDATE OF venue_id ON inventory.copies FOR EACH ROW EXECUTE FUNCTION inventory.forbid_transfer_of_loaned_copy()
  - forbid_transfer_of_loaned_copy(): 'copy % is on loan and cannot change venue'
- trg_copies_written_off_final: BEFORE UPDATE ON inventory.copies FOR EACH ROW EXECUTE FUNCTION inventory.forbid_written_off_change()
  - forbid_written_off_change(): 'copy % is written off'
- copies_inventory_no_key (unique на inventory.copies): UNIQUE (inventory_no)

## ORM
- services/inventory/models.py::Copy:38 (orm_model)

## Пишут (код)
- services/inventory/service.py::_set_state [state, updated_at]
- services/inventory/service.py::receive_transfer [venue_id]
- services/inventory/service.py::reconcile_venue [updated_at, venue_id]
- services/inventory/service.py::register_copy

## Правила
- R-INVENTORY-COPY-01 [draft] Инвентарный номер нормализуется и должен иметь вид «ШИФР-00000»
- R-INVENTORY-COPY-02 [draft] Инвентарный номер уникален во всём фонде
- R-INVENTORY-COPY-03 [draft] Новый экземпляр поступает в фонд доступным и пересчитывает остаток
- R-INVENTORY-COPY-04 [draft] Состояние экземпляра ограничено фиксированным набором
- R-INVENTORY-CUSTODIAN-01 [draft] Операции с фондом площадки выполняет только её хранитель
- R-INVENTORY-RECONCILE-01 [draft] Сверка переносит экземпляр на другую площадку без оформления перемещения
- R-INVENTORY-RECONCILE-02 [draft] Выданный по МБА экземпляр не может сменить площадку (триггер БД)
- R-INVENTORY-TRANSFER-05 [draft] Отправка переводит экземпляр в путь, приём переносит его на новую площадку
- R-INVENTORY-WRITEOFF-03 [draft] Списанный экземпляр нельзя изменить (триггер БД)

<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# inventory.transfers
Миграция: `inventory.transfers`

## Поля
- id: integer NOT NULL PK
- copy_id: integer NOT NULL
- from_venue_id: integer NOT NULL
- to_venue_id: integer NOT NULL
- status: text NOT NULL
- requested_by: integer NOT NULL
- requested_at: timestamp with time zone NOT NULL
- shipped_at: timestamp with time zone
- closed_at: timestamp with time zone
- cancel_reason: text

## Связи (FK)
- copy_id → inventory.copies

## Ограничения и триггеры
- transfers_check (check на inventory.transfers): CHECK ((from_venue_id <> to_venue_id))
- transfers_check1 (check на inventory.transfers): CHECK ((((status = 'requested'::text) = (shipped_at IS NULL)) OR (status = 'cancelled'::text)))
- transfers_check2 (check на inventory.transfers): CHECK (((status = ANY (ARRAY['received'::text, 'cancelled'::text])) = (closed_at IS NOT NULL)))
- transfers_status_check (check на inventory.transfers): CHECK ((status = ANY (ARRAY['requested'::text, 'in_transit'::text, 'received'::text, 'cancelled'::text])))
- uq_transfers_one_open (partial_unique_index на inventory.transfers): CREATE UNIQUE INDEX uq_transfers_one_open ON inventory.transfers USING btree (copy_id) WHERE (status = ANY (A…
- trg_transfers_origin: BEFORE INSERT ON inventory.transfers FOR EACH ROW EXECUTE FUNCTION inventory.check_transfer_origin()
  - check_transfer_origin(): 'copy % is not at venue %'

## ORM
- services/inventory/models.py::Transfer:51 (orm_model)

## Пишут (код)
- services/inventory/service.py::cancel_transfer [cancel_reason, closed_at, status]
- services/inventory/service.py::receive_transfer [closed_at, status]
- services/inventory/service.py::request_transfer
- services/inventory/service.py::ship_transfer [shipped_at, status]

## Правила
- R-INVENTORY-TRANSFER-01 [draft] Перемещение оформляет хранитель площадки, где лежит экземпляр, и только на другую площадку
- R-INVENTORY-TRANSFER-02 [draft] Перемещать можно только доступный экземпляр
- R-INVENTORY-TRANSFER-03 [draft] По экземпляру не больше одного незавершённого перемещения
- R-INVENTORY-TRANSFER-04 [draft] На площадке должен остаться минимум экземпляров издания
- R-INVENTORY-TRANSFER-05 [draft] Отправка переводит экземпляр в путь, приём переносит его на новую площадку
- R-INVENTORY-TRANSFER-06 [draft] Отменить перемещение может хранитель любой из двух площадок или система
- R-INVENTORY-TRANSFER-07 [draft] Отмена перемещения в пути возвращает экземпляр на полку отправителя

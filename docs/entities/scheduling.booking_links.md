<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# scheduling.booking_links
Миграция: [`migrations/versions/0001_initial.py:263`](../../migrations/versions/0001_initial.py#L263)

## Поля
- id: integer NOT NULL PK
- application_id: integer NOT NULL
- token: text NOT NULL
- purpose: text NOT NULL
- active: boolean NOT NULL

## Ограничения и триггеры
- booking_links_purpose_check (check на scheduling.booking_links): CHECK ((purpose = ANY (ARRAY['issue'::text, 'return'::text]))) (migrations/versions/0001_initial.py:267)
- uq_booking_links_one_active (partial_unique_index на scheduling.booking_links): CREATE UNIQUE INDEX uq_booking_links_one_active ON scheduling.booking_links USING btree (application_id) WHER… (migrations/versions/0001_initial.py:270)
- booking_links_token_key (unique на scheduling.booking_links): UNIQUE (token) (migrations/versions/0001_initial.py:266)

## ORM
- services/scheduling/models.py::BookingLink:33 (orm_model)

## Пишут (код)
- services/scheduling/service.py::issue_link
- services/scheduling/service.py::reset_bookings

## Правила
- R-SCHED-LINK-01 [draft] Ссылка на запись за книгами выдаётся при готовности к записи
- R-SCHED-LINK-02 [draft] У заявки только одна действующая ссылка
- R-SCHED-RESET-01 [draft] Архив и закрытие дублем сбрасывают записи, книги и ссылку
- R-SCHED-VENUE-CHANGE-01 [draft] Смена площадки отменяет запись и выдаёт новую ссылку

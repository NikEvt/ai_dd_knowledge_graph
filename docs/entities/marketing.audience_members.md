<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# marketing.audience_members
Миграция: `marketing.audience_members`

## Поля
- id: integer NOT NULL PK
- audience_id: integer NOT NULL
- email: text NOT NULL
- full_name: text NOT NULL
- segment: text NOT NULL
- opted_out: boolean NOT NULL
- added_at: timestamp with time zone NOT NULL

## Связи (FK)
- audience_id → marketing.audiences

## Ограничения и триггеры
- audience_members_email_check (check на marketing.audience_members): CHECK ((POSITION(('@'::text) IN (email)) > 1))
- audience_members_segment_check (check на marketing.audience_members): CHECK ((segment = ANY (ARRAY['paid'::text, 'debt'::text, 'social'::text, 'vip'::text, 'corporate'::text])))
- audience_members_email_idx (index на marketing.audience_members): CREATE INDEX audience_members_email_idx ON marketing.audience_members USING btree (email) WHERE (NOT opted_ou…
- audience_members_normalize_email: BEFORE INSERT OR UPDATE OF email ON marketing.audience_members FOR EACH ROW EXECUTE FUNCTION marketing.normalize_email()
  - normalize_email(): BEGIN NEW.email := lower(trim(NEW.email)); RETURN NEW; END;
- audience_members_email_uq (unique_index на marketing.audience_members): CREATE UNIQUE INDEX audience_members_email_uq ON marketing.audience_members USING btree (audience_id, email)

## ORM
- services/marketing/models.py::AudienceMember:36 (orm_model)

## Пишут (код)
- services/marketing/service.py::add_member
- services/marketing/service.py::exclude_address

## Правила
- R-MARKETING-AUDIENCE-03 Архивная аудитория закрыта для новых адресов, кампаний и запусков (подкреплено кодом и тестами)
- R-MARKETING-EMAIL-01 Адреса хранятся в нижнем регистре без пробелов и с «@» не в начале (подкреплено кодом и тестами)
- R-MARKETING-MEMBER-01 Сегмент читателя ограничен списком из настройки AUDIENCE_GROUP (подкреплено кодом и тестами)
- R-MARKETING-MEMBER-02 В аудитории не больше MAX_AUDIENCE_SIZE адресов (⚠ без тестов)
- R-MARKETING-MEMBER-03 Адрес встречается в аудитории один раз (подкреплено кодом и тестами)
- R-MARKETING-MEMBER-04 Отписанный адрес нельзя добавить в аудиторию (подкреплено кодом и тестами)
- R-MARKETING-UNSUBSCRIBE-02 Отписка исключает адрес из аудиторий и снимает ещё не ушедшие письма (подкреплено кодом и тестами)
- R-MARKETING-UNSUBSCRIBE-03 Отписка от площадки не влияет на рассылки других площадок (подкреплено кодом и тестами)

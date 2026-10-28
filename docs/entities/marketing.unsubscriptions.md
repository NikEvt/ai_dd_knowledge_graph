<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# marketing.unsubscriptions
Миграция: `marketing.unsubscriptions`

## Поля
- id: integer NOT NULL PK
- email: text NOT NULL
- venue_id: integer
- reason: text NOT NULL
- created_at: timestamp with time zone NOT NULL

## Ограничения и триггеры
- unsubscriptions_reason_check (check на marketing.unsubscriptions): CHECK ((reason = ANY (ARRAY['reader'::text, 'bounce'::text, 'complaint'::text, 'operator'::text])))
- unsubscriptions_network_uq (partial_unique_index на marketing.unsubscriptions): CREATE UNIQUE INDEX unsubscriptions_network_uq ON marketing.unsubscriptions USING btree (email) WHERE (venue_…
- unsubscriptions_venue_uq (partial_unique_index на marketing.unsubscriptions): CREATE UNIQUE INDEX unsubscriptions_venue_uq ON marketing.unsubscriptions USING btree (email, venue_id) WHERE…
- unsubscriptions_normalize_email: BEFORE INSERT OR UPDATE OF email ON marketing.unsubscriptions FOR EACH ROW EXECUTE FUNCTION marketing.normalize_email()
  - normalize_email(): BEGIN NEW.email := lower(trim(NEW.email)); RETURN NEW; END;

## ORM
- services/marketing/models.py::Unsubscription:98 (orm_model)

## Пишут (код)
- services/marketing/service.py::unsubscribe

## Правила
- R-MARKETING-EMAIL-01 Адреса хранятся в нижнем регистре без пробелов и с «@» не в начале (подкреплено кодом и тестами)
- R-MARKETING-UNSUBSCRIBE-01 Отписка от площадки или сети идемпотентна и требует известной причины (подкреплено кодом и тестами)
- R-MARKETING-UNSUBSCRIBE-03 Отписка от площадки не влияет на рассылки других площадок (подкреплено кодом и тестами)

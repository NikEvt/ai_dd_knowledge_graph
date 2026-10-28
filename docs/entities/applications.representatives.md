<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# applications.representatives
Миграция: [`migrations/versions/0001_initial.py:62`](../../migrations/versions/0001_initial.py#L62)

## Поля
- id: integer NOT NULL PK
- name: text NOT NULL
- email: text NOT NULL
- markup_pct: numeric NOT NULL
- debt_allowed: boolean NOT NULL

## Связи (FK)
- applications.applications.representative_id → сюда

## Ограничения и триггеры
- representatives_markup_pct_check (check на applications.representatives): CHECK ((markup_pct >= (0)::numeric)) (migrations/versions/0001_initial.py:66)

## ORM
- services/applications/models.py::Representative:59 (orm_model)

## Пишут (код)
- services/applications/admin.py::set_representative_terms [debt_allowed, markup_pct]

## Правила
- R-APP-ADMIN-01 Администратор задаёт надбавку и разрешение работать в долг для представителя (⚠ расхождение с требованием или открытый вопрос)
- R-APP-CALC-01 Стоимость книг заявки — сумма цен прайса текущей площадки, надбавку берёт billing у представителя (подкреплено кодом и тестами)

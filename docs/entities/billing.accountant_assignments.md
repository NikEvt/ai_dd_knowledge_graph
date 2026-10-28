<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# billing.accountant_assignments
Миграция: [`migrations/versions/0001_initial.py:147`](../../migrations/versions/0001_initial.py#L147)

## Поля
- application_id: integer NOT NULL PK
- accountant_id: integer NOT NULL

## ORM
- services/billing/models.py::AccountantAssignment:13 (orm_model)

## Пишут (код)
- services/billing/service.py::take_application [accountant_id]

## Правила
- R-BILL-ASSIGN-01 Бухгалтер сам закрепляет заявку за собой и может забрать её у коллеги (⚠ расхождение с требованием или открытый вопрос)
- R-BILL-ASSIGN-02 У заявки в долг нет бухгалтера (⚠ расхождение с требованием или открытый вопрос)

<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# applications.application_books
Миграция: [`migrations/versions/0001_initial.py:96`](../../migrations/versions/0001_initial.py#L96)

## Поля
- application_id: integer NOT NULL PK
- book_id: integer NOT NULL PK

## Связи (FK)
- application_id → applications.applications
- book_id → applications.books

## ORM
- services/applications/models.py::ApplicationBook:110 (orm_model)

## Пишут (код)
- services/applications/service.py::change_books
- services/applications/service.py::create_application
- services/applications/service.py::unarchive

## Правила
- R-APP-ACCESS-01 [draft] Оператор работает только со своими заявками
- R-APP-BOOKS-01 [draft] Книги меняют только в черновике или на доработке
- R-APP-CREATE-01 [draft] Вид заявки определяется при создании по флагу «социальная» и признаку долга представителя
- R-APP-CREATE-02 [draft] Сфера заявки должна быть активна на площадке
- R-APP-CREATE-04 [draft] При создании заявки закрепляется проверяющий оператор площадки и открывается первая попытка
- R-APP-UNARCHIVE-01 [draft] Возврат из архива начинает новую попытку и новую проверку
- R-APP-UNARCHIVE-02 [draft] При возврате из архива площадку и книги меняют, только если заявка не доходила до записи
- R-APP-UNARCHIVE-03 [draft] После возврата из архива счёт аннулируется при изменении суммы, иначе срок оплаты отсчитывается заново

- R-SCHEMA-APP-01 [draft] Оператора заявки переназначить нельзя

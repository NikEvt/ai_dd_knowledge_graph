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
- R-APP-ACCESS-01 Оператор работает только со своими заявками (подкреплено кодом и тестами)
- R-APP-BOOKS-01 Книги меняют только в черновике или на доработке (⚠ расхождение с требованием или открытый вопрос)
- R-APP-CREATE-01 Вид заявки определяется при создании по флагу «социальная» и признаку долга представителя (подкреплено кодом и тестами)
- R-APP-CREATE-02 Сфера заявки должна быть активна на площадке (подкреплено кодом и тестами)
- R-APP-CREATE-04 При создании заявки закрепляется проверяющий оператор площадки и открывается первая попытка (подкреплено кодом и тестами)
- R-APP-UNARCHIVE-01 Возврат из архива начинает новую попытку и новую проверку (подкреплено кодом и тестами)
- R-APP-UNARCHIVE-02 При возврате из архива площадку и книги меняют, только если заявка не доходила до записи (⚠ расхождение с требованием или открытый вопрос)
- R-APP-UNARCHIVE-03 После возврата из архива счёт аннулируется при изменении суммы, иначе срок оплаты отсчитывается заново
 (⚠ расхождение с требованием или открытый вопрос)
- R-SCHEMA-APP-01 Оператора заявки переназначить нельзя (⚠ расхождение с требованием или открытый вопрос)

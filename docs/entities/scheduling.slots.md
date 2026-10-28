<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# scheduling.slots
Миграция: [`migrations/versions/0001_initial.py:235`](../../migrations/versions/0001_initial.py#L235)

## Поля
- id: integer NOT NULL PK
- venue_id: integer NOT NULL
- sphere_id: integer NOT NULL
- starts_at: timestamp with time zone NOT NULL
- capacity: integer NOT NULL
- removed: boolean NOT NULL

## Связи (FK)
- scheduling.bookings.slot_id → сюда

## Ограничения и триггеры
- slots_capacity_check (check на scheduling.slots): CHECK ((capacity > 0)) (migrations/versions/0001_initial.py:240)
- trg_slot_capacity_limit: BEFORE INSERT OR UPDATE OF capacity ON scheduling.slots FOR EACH ROW EXECUTE FUNCTION scheduling.check_slot_capacity() (migrations/versions/0001_initial.py:259)
  - check_slot_capacity(): 'no capacity limit for venue %'; 'slot capacity % exceeds venue maximum %'

## ORM
- services/scheduling/models.py::Slot:21 (orm_model)

## Пишут (код)
- services/scheduling/service.py::create_slot
- services/scheduling/service.py::reduce_capacity [capacity]
- services/scheduling/service.py::remove_slot [removed]

## Правила
- R-SCHED-SITE-CHECKER-01 Проверяющий оператор работает только со своей площадкой (⚠ без тестов)
- R-SCHED-SLOT-01 Нельзя создать окно на прошедшее время (подкреплено кодом и тестами)
- R-SCHED-SLOT-02 По умолчанию в окне столько мест, сколько максимум площадки (подкреплено кодом и тестами)
- R-SCHED-SLOT-03 Число мест в окне не больше максимума площадки (контроль в БД) (⚠ расхождение со схемой или открытый вопрос)
- R-SCHED-SLOT-04 Проверяющий оператор может только уменьшить число мест в окне (подкреплено кодом и тестами)
- R-SCHED-SLOT-05 Удаление окна отменяет записи на него (⚠ без тестов)

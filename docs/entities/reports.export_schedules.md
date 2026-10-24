<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# reports.export_schedules
Миграция: `reports.export_schedules`

## Поля
- id: integer NOT NULL PK
- definition_id: integer NOT NULL
- every_hours: integer NOT NULL
- next_run_at: timestamp with time zone NOT NULL
- recipients: jsonb NOT NULL
- created_by: integer NOT NULL
- is_active: boolean NOT NULL
- last_enqueued_at: timestamp with time zone
- created_at: timestamp with time zone NOT NULL

## Связи (FK)
- definition_id → reports.report_definitions
- reports.report_runs.schedule_id → сюда

## Ограничения и триггеры
- export_schedules_interval (check на reports.export_schedules): CHECK (((every_hours >= 1) AND (every_hours <= 744)))
- export_schedules_recipients_array (check на reports.export_schedules): CHECK ((jsonb_typeof(recipients) = 'array'::text))
- export_schedules_one_active (partial_unique_index на reports.export_schedules): CREATE UNIQUE INDEX export_schedules_one_active ON reports.export_schedules USING btree (definition_id) WHERE…

## ORM
- services/reports/models.py::ExportSchedule:45 (orm_model)

## Пишут (код)
- services/reports/jobs.py::run_scheduled [is_active]
- services/reports/service.py::advance [last_enqueued_at, next_run_at]
- services/reports/service.py::create_schedule
- services/reports/service.py::deactivate_definition [is_active]
- services/reports/service.py::deactivate_schedule [is_active]

## Правила
- R-REPORTS-DEF-01 [draft] Настройки отчёта меняет только его владелец
- R-REPORTS-DEF-08 [draft] Отключённый отчёт нельзя изменить, запустить или поставить на расписание
- R-REPORTS-DEF-09 [draft] Отключение отчёта гасит его расписания и публикует reports.definition_deactivated
- R-REPORTS-SCHED-01 [draft] Расписание выгрузки ставит владелец действующего отчёта, у отчёта одно действующее расписание
- R-REPORTS-SCHED-02 [draft] Интервал выгрузки — от 1 до 744 часов, первая выгрузка не в прошлом
- R-REPORTS-SCHED-03 [draft] У выгрузки от 1 до 20 уникальных получателей
- R-REPORTS-SCHED-04 [draft] Отключить расписание может его автор или владелец отчёта
- R-REPORTS-SCHED-05 [draft] Фоновая задача ставит в очередь выгрузки, у которых подошёл срок
- R-REPORTS-SCHED-06 [draft] Расписание, по которому не удалось создать запуск, молча отключается
- R-REPORTS-SCHED-07 [draft] Пропущенные интервалы выгрузки не догоняются

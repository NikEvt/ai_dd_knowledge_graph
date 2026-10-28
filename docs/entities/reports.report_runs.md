<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# reports.report_runs
Миграция: `reports.report_runs`

## Поля
- id: bigint NOT NULL PK
- definition_id: integer NOT NULL
- schedule_id: integer
- scheduled_for: timestamp with time zone
- status: text NOT NULL
- params: jsonb NOT NULL
- body: jsonb
- error: text
- requested_by: integer NOT NULL
- requested_at: timestamp with time zone NOT NULL
- started_at: timestamp with time zone
- finished_at: timestamp with time zone

## Связи (FK)
- schedule_id → reports.export_schedules
- definition_id → reports.report_definitions
- reports.run_notifications.run_id → сюда

## Ограничения и триггеры
- report_runs_body_on_completion (check на reports.report_runs): CHECK (((status = 'completed'::text) = (body IS NOT NULL)))
- report_runs_error_on_failure (check на reports.report_runs): CHECK (((status <> 'failed'::text) OR (error IS NOT NULL)))
- report_runs_finished (check на reports.report_runs): CHECK (((status = ANY (ARRAY['completed'::text, 'failed'::text, 'cancelled'::text])) = (finished_at IS NOT NU…
- report_runs_schedule_slot (check на reports.report_runs): CHECK (((schedule_id IS NULL) = (scheduled_for IS NULL)))
- report_runs_status (check на reports.report_runs): CHECK ((status = ANY (ARRAY['requested'::text, 'running'::text, 'completed'::text, 'failed'::text, 'cancelled…
- report_runs_definition (index на reports.report_runs): CREATE INDEX report_runs_definition ON reports.report_runs USING btree (definition_id, requested_at DESC)
- report_runs_requested_at (index на reports.report_runs): CREATE INDEX report_runs_requested_at ON reports.report_runs USING btree (requested_at)
- report_runs_one_in_flight (partial_unique_index на reports.report_runs): CREATE UNIQUE INDEX report_runs_one_in_flight ON reports.report_runs USING btree (definition_id, requested_by…
- report_runs_schedule_once (partial_unique_index на reports.report_runs): CREATE UNIQUE INDEX report_runs_schedule_once ON reports.report_runs USING btree (schedule_id, scheduled_for)…
- trg_report_runs_immutable: BEFORE UPDATE ON reports.report_runs FOR EACH ROW EXECUTE FUNCTION reports.report_runs_immutable()
  - report_runs_immutable(): 'запуск % уже завершён (%), изменять его нельзя'
- trg_report_runs_transition: BEFORE UPDATE OF status ON reports.report_runs FOR EACH ROW EXECUTE FUNCTION reports.report_runs_transition()
  - report_runs_transition(): 'недопустимый переход запуска %: % -> %'

## ORM
- services/reports/models.py::ReportRun:60 (orm_model)

## Пишут (код)
- services/reports/jobs.py::fail_stuck_runs [error, finished_at, status]
- services/reports/jobs.py::purge_old_runs
- services/reports/service.py::_finish [body, error, finished_at, status]
- services/reports/service.py::build_run [started_at, status]
- services/reports/service.py::request_run

## Правила
- R-REPORTS-DEF-08 Отключённый отчёт нельзя изменить, запустить или поставить на расписание (подкреплено кодом и тестами)
- R-REPORTS-RUN-01 При запуске можно переопределить только период, дату и разрез (подкреплено кодом и тестами)
- R-REPORTS-RUN-02 Лимит незавершённых ручных запусков на сотрудника (подкреплено кодом и тестами)
- R-REPORTS-RUN-03 Отчёт строится асинхронно по событию reports.run_requested, повторная доставка безопасна (подкреплено кодом и тестами)
- R-REPORTS-RUN-04 Запуск отключённого к моменту построения отчёта отменяется (⚠ без тестов)
- R-REPORTS-RUN-05 Итог построения — completed с телом отчёта или failed с текстом ошибки (подкреплено кодом и тестами)
- R-REPORTS-RUN-07 Допустимые переходы статуса запуска задаёт триггер БД (подкреплено кодом и тестами)
- R-REPORTS-RUN-08 Завершённый запуск неизменяем, его можно только удалить (подкреплено кодом и тестами)
- R-REPORTS-SCHED-05 Фоновая задача ставит в очередь выгрузки, у которых подошёл срок (подкреплено кодом и тестами)
- R-REPORTS-TIMER-01 Запуск, который строится дольше 30 минут, помечается неуспешным (подкреплено кодом и тестами)
- R-REPORTS-TIMER-02 Завершённые запуски удаляются через 30 дней вместе с уведомлениями (подкреплено кодом и тестами)

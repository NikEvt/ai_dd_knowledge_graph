<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# reports.report_definitions
Миграция: `reports.report_definitions`

## Поля
- id: integer NOT NULL PK
- code: text NOT NULL
- title: text NOT NULL
- kind: text NOT NULL
- params: jsonb NOT NULL
- owner_id: integer NOT NULL
- is_active: boolean NOT NULL
- created_at: timestamp with time zone NOT NULL
- updated_at: timestamp with time zone NOT NULL

## Связи (FK)
- reports.export_schedules.definition_id → сюда
- reports.report_runs.definition_id → сюда

## Ограничения и триггеры
- report_definitions_code_format (check на reports.report_definitions): CHECK ((code ~ '^[a-z][a-z0-9_-]{2,63}$'::text))
- report_definitions_kind (check на reports.report_definitions): CHECK ((kind = ANY (ARRAY['metric_summary'::text, 'metric_trend'::text, 'run_audit'::text])))
- report_definitions_params_object (check на reports.report_definitions): CHECK ((jsonb_typeof(params) = 'object'::text))
- report_definitions_title_not_blank (check на reports.report_definitions): CHECK ((btrim(title) <> ''::text))
- report_definitions_owner_title_active (partial_unique_index на reports.report_definitions): CREATE UNIQUE INDEX report_definitions_owner_title_active ON reports.report_definitions USING btree (owner_id…
- trg_report_definitions_kind_locked: BEFORE UPDATE OF kind ON reports.report_definitions FOR EACH ROW WHEN ((old.kind IS DISTINCT FROM new.kind)) EXECUTE FU…
  - report_definitions_kind_locked(): 'у отчёта % уже есть запуски, тип менять нельзя'
- report_definitions_code_key (unique на reports.report_definitions): UNIQUE (code)

## ORM
- services/reports/models.py::ReportDefinition:30 (orm_model)

## Пишут (код)
- services/reports/service.py::create_definition
- services/reports/service.py::deactivate_definition [is_active, updated_at]
- services/reports/service.py::update_definition [kind, params, title, updated_at]

## Правила
- R-REPORTS-DEF-01 Настройки отчёта меняет только его владелец (подкреплено кодом и тестами)
- R-REPORTS-DEF-02 Название отчёта обязательно и уникально среди действующих отчётов владельца (подкреплено кодом и тестами)
- R-REPORTS-DEF-03 Код отчёта уникален навсегда, его формат проверяет только БД (подкреплено кодом и тестами)
- R-REPORTS-DEF-04 Тип отчёта — один из трёх, у каждого типа свой набор параметров (подкреплено кодом и тестами)
- R-REPORTS-DEF-05 Сводный отчёт — от 1 до 20 уникальных метрик, динамика — ровно одна метрика (подкреплено кодом и тестами)
- R-REPORTS-DEF-07 Тип отчёта нельзя менять, если у него уже есть запуски (подкреплено кодом и тестами)
- R-REPORTS-DEF-08 Отключённый отчёт нельзя изменить, запустить или поставить на расписание (подкреплено кодом и тестами)
- R-REPORTS-DEF-09 Отключение отчёта гасит его расписания и публикует reports.definition_deactivated (подкреплено кодом и тестами)

<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# reports.metric_snapshots
Миграция: `reports.metric_snapshots`

## Поля
- id: bigint NOT NULL PK
- metric: text NOT NULL
- dimension: text NOT NULL
- day: date NOT NULL
- value: numeric NOT NULL
- taken_at: timestamp with time zone NOT NULL

## Ограничения и триггеры
- metric_snapshots_dimension_len (check на reports.metric_snapshots): CHECK ((length(dimension) <= 64))
- metric_snapshots_metric_format (check на reports.metric_snapshots): CHECK ((metric ~ '^[a-z][a-z0-9_]*(\.[a-z0-9_]+)*$'::text))
- metric_snapshots_metric_day (index на reports.metric_snapshots): CREATE INDEX metric_snapshots_metric_day ON reports.metric_snapshots USING btree (metric, day)
- metric_snapshots_point (unique на reports.metric_snapshots): UNIQUE (metric, dimension, day)

## ORM
- services/reports/models.py::MetricSnapshot:16 (orm_model)

## Правила
- R-REPORTS-SNAP-01 Снимок метрики за день перезаписывается повторной записью (подкреплено кодом и тестами)
- R-REPORTS-SNAP-02 Имя метрики — латиница в нижнем регистре с точками-разделителями (подкреплено кодом и тестами)
- R-REPORTS-SNAP-03 Длину разреза снимка проверяет только БД (⚠ без тестов)
- R-REPORTS-SNAP-04 Каждый построенный отчёт прибавляет 1 к служебной метрике reports.runs_completed (⚠ без тестов)

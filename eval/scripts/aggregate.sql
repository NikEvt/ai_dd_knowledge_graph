-- duckdb < scripts/aggregate.sql   (cwd = library-eval)
CREATE TABLE m AS
SELECT * FROM read_json_auto('logs/runs/*/audit.jsonl', union_by_name = true, format = 'newline_delimited');

-- B2: полный контекст = слепой аудит
CREATE TABLE b2 AS
SELECT task, cost_usd, input_tokens FROM read_json_auto('logs/blind/*/auditor_blind_usage.json');

.print '== Сводка по вариантам (среднее ± sd по повторам и задачам)'
SELECT variant, metric,
       round(avg(TRY_CAST(value AS DOUBLE)), 3) AS mean,
       round(stddev_samp(TRY_CAST(value AS DOUBLE)), 3) AS sd,
       count(*) AS n
FROM m
WHERE metric IN ('hidden_link_recall', 'context_recall', 'pack_recall', 'change_recall', 'task_success',
                 'regressions', 'tokens_context', 'tokens_total', 'cost_usd', 'files_read_whole',
                 'mcp_calls_before_edit', 'pack_tokens', 'impact_precision', 'plan_recall')
GROUP BY ALL ORDER BY metric, variant;

.print '== По задачам: hidden_link_recall и task_success'
SELECT task_id, variant,
       round(avg(CASE WHEN metric = 'hidden_link_recall' THEN TRY_CAST(value AS DOUBLE) END), 2) AS hidden_recall,
       round(avg(CASE WHEN metric = 'task_success' THEN TRY_CAST(value AS DOUBLE) END), 2) AS success,
       round(avg(CASE WHEN metric = 'cost_usd' THEN TRY_CAST(value AS DOUBLE) END), 2) AS cost
FROM m GROUP BY ALL ORDER BY task_id, variant;

.print '== Скрытые связи по категориям'
SELECT variant, hidden_category, round(avg(TRY_CAST(value AS DOUBLE)), 2) AS recall, count(*) AS n
FROM m WHERE metric = 'hidden_link_recall_by_category'
GROUP BY ALL ORDER BY hidden_category, variant;

.print '== Пропущенные скрытые узлы (сколько раз)'
SELECT variant, node, count(*) AS times
FROM (SELECT variant, unnest(missed) AS node FROM m WHERE metric = 'hidden_link_recall')
GROUP BY ALL ORDER BY times DESC, variant LIMIT 30;

.print '== Причины пропусков (аудитор)'
SELECT variant, reason, count(*) AS n
FROM m WHERE metric = 'miss_reason' GROUP BY ALL ORDER BY n DESC;

.print '== B2 (полный контекст, слепой аудит)'
SELECT task, round(cost_usd, 2) AS cost_usd, input_tokens FROM b2 ORDER BY task;

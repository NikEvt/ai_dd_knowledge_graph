<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# Правила: reports

Источник: [`knowledge/rules/reports.yaml`](../../knowledge/rules/reports.yaml)

## R-REPORTS-DEF-01 — Настройки отчёта меняет только его владелец

`draft` · permission

Изменять определение отчёта, отключать его и ставить на расписание может только сотрудник, чей id совпадает с owner_id определения; иначе AccessDenied «настройки отчёта меняет только его владелец». Проверка в _owned_definition, её вызывают update_definition, deactivate_definition и create_schedule. Идентификатор действующего лица (`by`, `owner_id`) API берёт из параметров запроса без аутентификации.

- Реализация: [`services/reports/service.py::_owned_definition:84-88`](../../services/reports/service.py#L84), [`services/reports/service.py::update_definition:146-146`](../../services/reports/service.py#L146), [`services/reports/service.py::deactivate_definition:167-167`](../../services/reports/service.py#L167)
- Тесты: `tests/test_reports_definitions.py::test_only_owner_changes_definition`
- Связанные: R-REPORTS-DEF-08, R-REPORTS-SCHED-01

## R-REPORTS-DEF-02 — Название отчёта обязательно и уникально среди действующих отчётов владельца

`draft` · invariant

Название обрезается по краям и не может быть пустым. У одного владельца не может быть двух действующих (is_active) отчётов с одинаковым названием без учёта регистра; отключённые отчёты название не занимают. Код проверяет это при создании и при переименовании (кроме самого отчёта), БД дублирует проверку частичным уникальным индексом по (owner_id, lower(title)) WHERE is_active и CHECK на непустое название.

- Реализация: [`services/reports/service.py::create_definition:114-121`](../../services/reports/service.py#L114), [`services/reports/service.py::update_definition:149-154`](../../services/reports/service.py#L149), [`services/reports/service.py::_check_title_free:91-102`](../../services/reports/service.py#L91)
- БД: `report_definitions_owner_title_active`, `report_definitions_title_not_blank`
- Тесты: `tests/test_reports_definitions.py::test_code_unique_and_title_unique_per_owner`, `tests/test_reports_definitions.py::test_title_released_after_deactivation`
- Связанные: R-REPORTS-DEF-08

## R-REPORTS-DEF-03 — Код отчёта уникален навсегда, его формат проверяет только БД

`draft` · invariant

Код отчёта уникален среди всех определений, включая отключённые: занятый код нельзя использовать повторно («код отчёта … уже занят»). Формат кода (^[a-z][a-z0-9_-]{2,63}$) код не проверяет — неверный код отклоняет только CHECK в БД, и это приходит ошибкой БД, а не DomainError.

- Реализация: [`services/reports/service.py::create_definition:119-120`](../../services/reports/service.py#L119)
- БД: `report_definitions_code_key`, `report_definitions_code_format`
- Тесты: `tests/test_reports_definitions.py::test_code_unique_and_title_unique_per_owner`

## R-REPORTS-DEF-04 — Тип отчёта — один из трёх, у каждого типа свой набор параметров

`draft` · invariant

Допустимые типы — metric_summary, metric_trend, run_audit (константа KINDS и CHECK в БД). Для каждого типа задан набор допустимых параметров (_ALLOWED): сводка — metrics, days, dimension, as_of; динамика — metric, days, dimension, as_of; аудит запусков — только days и as_of. Неизвестный тип и лишние параметры отклоняются в normalize_params. params в БД обязан быть JSON-объектом.

- Реализация: [`services/reports/builders.py::normalize_params:57-61`](../../services/reports/builders.py#L57)
- БД: `report_definitions_kind`, `report_definitions_params_object`
- Настройки: `services/reports/builders.py::KINDS`, `services/reports/builders.py::_ALLOWED`
- Тесты: `tests/test_reports_definitions.py::test_definition_params_are_validated`
- Связанные: R-REPORTS-DEF-05, R-REPORTS-DEF-06, R-REPORTS-RUN-01

## R-REPORTS-DEF-05 — Сводный отчёт — от 1 до 20 уникальных метрик, динамика — ровно одна метрика

`draft` · invariant

В сводном отчёте metrics — непустой список не длиннее MAX_METRICS_PER_REPORT (20) корректных имён метрик; дубли убираются с сохранением порядка. Определение сводки без metrics и динамики без metric отклоняется (require_complete) при создании и изменении.

- Реализация: [`services/reports/builders.py::normalize_params:63-71`](../../services/reports/builders.py#L63), [`services/reports/builders.py::require_complete:83-87`](../../services/reports/builders.py#L83)
- Настройки: `services/reports/settings.py::MAX_METRICS_PER_REPORT`
- Тесты: `tests/test_reports_definitions.py::test_summary_definition_keeps_metrics_unique_and_ordered`, `tests/test_reports_definitions.py::test_definition_params_are_validated`
- Связанные: R-REPORTS-DEF-04, R-REPORTS-SNAP-02

## R-REPORTS-DEF-06 — Период отчёта — целое число от 1 до 90 дней; разрез до 64 символов; дата в формате ГГГГ-ММ-ДД

`draft` · invariant

Параметр days — целое (не bool) от 1 до MAX_PERIOD_DAYS (90). dimension — строка до 64 символов (литерал 64 в коде, совпадает с CHECK на metric_snapshots.dimension). as_of — дата ISO, приводится к каноническому виду. Проверки одинаково применяются к определению и к параметрам запуска.

- Реализация: [`services/reports/builders.py::_days:42-45`](../../services/reports/builders.py#L42), [`services/reports/builders.py::_as_of:48-52`](../../services/reports/builders.py#L48), [`services/reports/builders.py::normalize_params:72-79`](../../services/reports/builders.py#L72)
- Настройки: `services/reports/settings.py::MAX_PERIOD_DAYS`
- Тесты: `tests/test_reports_definitions.py::test_definition_params_are_validated`
- Связанные: R-REPORTS-CALC-01

## R-REPORTS-DEF-07 — Тип отчёта нельзя менять, если у него уже есть запуски

`draft` · invariant

Триггер БД trg_report_definitions_kind_locked запрещает менять kind, если в report_runs есть хоть один запуск этого определения. В update_definition такой проверки нет — смена типа падает ошибкой БД. update_definition не выведен в API. После того как purge_old_runs удалит все запуски отчёта, тип снова можно менять.

- Реализация: [`services/reports/service.py::update_definition:155-160`](../../services/reports/service.py#L155)
- БД: `trg_report_definitions_kind_locked`, `report_definitions_kind_locked`
- Тесты: `tests/test_reports_definitions.py::test_kind_locked_once_report_was_run`
- Связанные: R-REPORTS-TIMER-02

## R-REPORTS-DEF-08 — Отключённый отчёт нельзя изменить, запустить или поставить на расписание

`draft` · guard

Если у определения is_active = false, update_definition, request_run и create_schedule возвращают DomainError. Включить отчёт обратно в модуле нельзя.

- Реализация: [`services/reports/service.py::update_definition:147-148`](../../services/reports/service.py#L147), [`services/reports/service.py::request_run:232-233`](../../services/reports/service.py#L232), [`services/reports/service.py::create_schedule:385-386`](../../services/reports/service.py#L385)
- Тесты: `tests/test_reports_runs.py::test_deactivation_cancels_pending_runs_and_schedules`
- Связанные: R-REPORTS-DEF-09

## R-REPORTS-DEF-09 — Отключение отчёта гасит его расписания и публикует reports.definition_deactivated

`draft` · effect

DELETE /reports/definitions/{id} — мягкое удаление: владелец ставит is_active = false (повторный вызов ничего не делает), в той же транзакции отключаются все действующие расписания выгрузки отчёта и публикуется reports.definition_deactivated. Название освобождается для нового отчёта.

- Реализация: [`services/reports/service.py::deactivate_definition:166-182`](../../services/reports/service.py#L166)
- Тесты: `tests/test_reports_runs.py::test_deactivation_cancels_pending_runs_and_schedules`, `tests/test_reports_definitions.py::test_title_released_after_deactivation`
- Связанные: R-REPORTS-DEF-10, R-REPORTS-DEF-02

## R-REPORTS-DEF-10 — После отключения отчёта ожидающие запуски отменяются

`draft` · effect

Подписчик reports.definition_deactivated отменяет все запуски отчёта в статусе requested (строки, заблокированные другой транзакцией, пропускаются: skip_locked) и на каждый публикует reports.run_cancelled с reason=definition_deactivated. Запуски в статусе running достраиваются как обычно.

- Реализация: [`services/reports/consumers.py::on_definition_deactivated:44-45`](../../services/reports/consumers.py#L44), [`services/reports/service.py::cancel_pending_for_definition:331-342`](../../services/reports/service.py#L331)
- Тесты: `tests/test_reports_runs.py::test_deactivation_cancels_pending_runs_and_schedules`
- Роли: Система (события и фоновые задачи)
- Связанные: R-REPORTS-DEF-09, R-REPORTS-RUN-04, R-REPORTS-NOTIFY-03

## R-REPORTS-RUN-01 — При запуске можно переопределить только период, дату и разрез

`draft` · guard

Параметры ручного запуска ограничены RUN_OVERRIDABLE (days, as_of, dimension); остальные отклоняются («при запуске нельзя менять параметры»). Затем параметры проверяются по правилам типа отчёта, поэтому для run_audit dimension тоже отклоняется как лишний параметр. В запуске сохраняются только переопределения: параметры определения подмешиваются при построении, так что правка определения до начала построения меняет результат уже запрошенного запуска.

- Реализация: [`services/reports/service.py::request_run:234-238`](../../services/reports/service.py#L234), [`services/reports/builders.py::build:170-170`](../../services/reports/builders.py#L170)
- Настройки: `services/reports/builders.py::RUN_OVERRIDABLE`
- Тесты: `tests/test_reports_definitions.py::test_run_may_override_only_period_and_dimension`
- Связанные: R-REPORTS-DEF-04, R-REPORTS-CALC-01

## R-REPORTS-RUN-02 — Лимит незавершённых ручных запусков на сотрудника

`draft` · guard

У сотрудника может быть не больше одного незавершённого (requested/running) ручного запуска одного отчёта и не больше MAX_PENDING_RUNS_PER_USER (3) таких запусков всего. Запуски по расписанию в лимит не входят и не проверяются. Первое ограничение дублирует частичный уникальный индекс report_runs_one_in_flight (definition_id, requested_by) WHERE schedule_id IS NULL AND status IN (requested, running).

- Реализация: [`services/reports/service.py::_check_run_quota:206-219`](../../services/reports/service.py#L206), [`services/reports/service.py::request_run:239-240`](../../services/reports/service.py#L239)
- БД: `report_runs_one_in_flight`
- Настройки: `services/reports/settings.py::MAX_PENDING_RUNS_PER_USER`, `services/reports/models.py::IN_FLIGHT`
- Тесты: `tests/test_reports_runs.py::test_pending_runs_limited_per_employee`
- Связанные: R-REPORTS-SCHED-06

## R-REPORTS-RUN-03 — Отчёт строится асинхронно по событию reports.run_requested, повторная доставка безопасна

`draft` · effect

request_run создаёт запуск в статусе requested и публикует reports.run_requested (API отвечает 202). Подписчик вызывает build_run: он блокирует строку запуска (FOR UPDATE) и ничего не делает, если запуск уже не в requested, поэтому повторная доставка события отчёт не перестраивает. Иначе статус меняется на running и фиксируется started_at.

- Реализация: [`services/reports/service.py::request_run:242-257`](../../services/reports/service.py#L242), [`services/reports/consumers.py::on_run_requested:11-12`](../../services/reports/consumers.py#L11), [`services/reports/service.py::build_run:280-291`](../../services/reports/service.py#L280)
- Тесты: `tests/test_reports_runs.py::test_redelivered_request_does_not_rebuild`, `tests/test_reports_runs.py::test_summary_run_is_built_and_requester_notified`
- Роли: Система (события и фоновые задачи)
- Связанные: R-REPORTS-RUN-04, R-REPORTS-RUN-05

## R-REPORTS-RUN-04 — Запуск отключённого к моменту построения отчёта отменяется

`draft` · guard

Если на момент построения определение уже отключено, build_run переводит запуск requested → cancelled и публикует reports.run_cancelled с reason=definition_deactivated. Это закрывает гонку с cancel_pending_for_definition, который пропускает заблокированные строки.

- Реализация: [`services/reports/service.py::build_run:283-287`](../../services/reports/service.py#L283)
- Роли: Система (события и фоновые задачи)
- Связанные: R-REPORTS-DEF-10

## R-REPORTS-RUN-05 — Итог построения — completed с телом отчёта или failed с текстом ошибки

`draft` · effect

Если построитель бросает DomainError (например, за период нет данных), запуск становится failed, ошибка сохраняется в error и публикуется reports.run_failed. При успехе тело отчёта сохраняется в body, запуск становится completed и публикуется reports.run_completed с code отчёта, schedule_id и датой finished_on.

- Реализация: [`services/reports/service.py::build_run:292-317`](../../services/reports/service.py#L292), [`services/reports/service.py::_finish:261-267`](../../services/reports/service.py#L261)
- БД: `report_runs_body_on_completion`, `report_runs_error_on_failure`
- Тесты: `tests/test_reports_runs.py::test_run_without_data_fails_and_owner_is_told`, `tests/test_reports_runs.py::test_summary_run_is_built_and_requester_notified`
- Роли: Система (события и фоновые задачи)
- Связанные: R-REPORTS-NOTIFY-01, R-REPORTS-NOTIFY-02, R-REPORTS-SNAP-04

## R-REPORTS-RUN-06 — Отменить запуск может только запросивший и только до начала построения

`draft` · permission

POST /reports/runs/{id}/cancel: при requested_by ≠ by — AccessDenied, при статусе не requested — DomainError. Запуск переходит в cancelled и публикуется reports.run_cancelled с reason=by_user. У запусков по расписанию requested_by — автор расписания, поэтому их может отменить только он.

- Реализация: [`services/reports/service.py::cancel_run:320-328`](../../services/reports/service.py#L320)
- Тесты: `tests/test_reports_runs.py::test_pending_run_cancelled_only_by_requester`
- Связанные: R-REPORTS-NOTIFY-03

## R-REPORTS-RUN-07 — Допустимые переходы статуса запуска задаёт триггер БД

`draft` · invariant

Статусы запуска — requested, running, completed, failed, cancelled. Триггер trg_report_runs_transition разрешает только requested → running/failed/cancelled и running → completed/failed. Код использует requested → running/cancelled (build_run, cancel_run, отмена по отключению) и running → completed/failed (build_run, fail_stuck_runs). Переход requested → failed БД разрешает, но код его не выполняет.

- Реализация: [`services/reports/service.py::build_run:289-304`](../../services/reports/service.py#L289), [`services/reports/service.py::cancel_run:324-326`](../../services/reports/service.py#L324)
- БД: `trg_report_runs_transition`, `report_runs_transition`, `report_runs_status`
- Настройки: `services/reports/models.py::IN_FLIGHT`, `services/reports/models.py::FINISHED`
- Тесты: `tests/test_reports_db.py::test_run_status_rules_enforced_in_db`
- Связанные: R-REPORTS-RUN-08

## R-REPORTS-RUN-08 — Завершённый запуск неизменяем, его можно только удалить

`draft` · invariant

Триггер trg_report_runs_immutable запрещает любое UPDATE строки запуска в статусе completed, failed или cancelled. Удалять такие строки можно — это делает purge_old_runs по сроку хранения. CHECK требуют, чтобы finished_at был заполнен ровно у завершённых запусков; _finish ставит status, body, error и finished_at одновременно.

- Реализация: [`services/reports/service.py::_finish:261-267`](../../services/reports/service.py#L261)
- БД: `trg_report_runs_immutable`, `report_runs_immutable`, `report_runs_finished`
- Тесты: `tests/test_reports_db.py::test_finished_run_cannot_be_rewritten`
- Связанные: R-REPORTS-RUN-07, R-REPORTS-TIMER-02

## R-REPORTS-CALC-01 — Период отчёта заканчивается датой as_of или датой запуска и длится days дней включительно

`draft` · calculation

Параметры определения и запуска объединяются, запуск важнее. Конец периода — as_of, а если её нет — дата scheduled_for (для запуска по расписанию) или requested_at (для ручного). Начало = конец − (days − 1), days по умолчанию DEFAULT_PERIOD_DAYS (7). Комментарий в settings называет DEFAULT_PERIOD_DAYS «максимальной глубиной», но фактический максимум — MAX_PERIOD_DAYS (90).

- Реализация: [`services/reports/builders.py::build:170-172`](../../services/reports/builders.py#L170), [`services/reports/builders.py::_period:90-93`](../../services/reports/builders.py#L90)
- Настройки: `services/reports/settings.py::DEFAULT_PERIOD_DAYS`
- Тесты: `tests/test_reports_runs.py::test_trend_respects_dimension_and_as_of`
- Роли: Система (события и фоновые задачи)
- Связанные: R-REPORTS-DEF-06, R-REPORTS-RUN-01

## R-REPORTS-CALC-02 — Сводный отчёт считает число точек, сумму, среднее, минимум и максимум по каждой метрике

`draft` · calculation

По каждой метрике берутся снимки за период в заданном разрезе: points, total, avg, min, max с округлением до 0.01 (CENT). Метрика без данных попадает в отчёт с points = 0. Если данных нет ни по одной метрике — DomainError, и запуск завершается со статусом failed.

- Реализация: [`services/reports/builders.py::_summary:111-129`](../../services/reports/builders.py#L111), [`services/reports/builders.py::_money:32-33`](../../services/reports/builders.py#L32)
- Настройки: `services/reports/builders.py::CENT`
- Тесты: `tests/test_reports_runs.py::test_summary_run_is_built_and_requester_notified`
- Роли: Система (события и фоновые задачи)
- Связанные: R-REPORTS-CALC-04, R-REPORTS-RUN-05

## R-REPORTS-CALC-03 — Отчёт-динамика — ряд значений по дням и изменение «последнее минус первое»

`draft` · calculation

Для metric_trend строится ряд снимков метрики по дням периода (значения округлены до 0.01) и change = последнее значение − первое. Если за период нет ни одного снимка — DomainError, запуск failed.

- Реализация: [`services/reports/builders.py::_trend:132-142`](../../services/reports/builders.py#L132)
- Тесты: `tests/test_reports_runs.py::test_trend_respects_dimension_and_as_of`
- Роли: Система (события и фоновые задачи)
- Связанные: R-REPORTS-CALC-04

## R-REPORTS-CALC-04 — Разрез выбирается точным совпадением, пустой разрез — отдельный ряд, а не итог

`draft` · calculation

Снимки отбираются по точному совпадению dimension. По умолчанию это пустая строка, то есть ряд «без разреза»: значения по разным разрезам не суммируются в итог.

- Реализация: [`services/reports/builders.py::_points:96-108`](../../services/reports/builders.py#L96), [`services/reports/builders.py::_summary:112-112`](../../services/reports/builders.py#L112)
- Тесты: `tests/test_reports_runs.py::test_trend_respects_dimension_and_as_of`
- Роли: Система (события и фоновые задачи)
- Связанные: R-REPORTS-CALC-02, R-REPORTS-CALC-03

## R-REPORTS-CALC-05 — Аудит запусков считает запуски периода по статусам и кодам отчётов, кроме текущего

`draft` · calculation

run_audit группирует запуски, у которых дата requested_at (UTC) попадает в период, по статусу и по коду отчёта; текущий запуск не учитывается. Завершённые запуски старше RETENTION_DAYS (30) удаляются, поэтому аудит за период до 90 дней фактически видит только последние 30 дней завершённых запусков.

- Реализация: [`services/reports/builders.py::_audit:145-166`](../../services/reports/builders.py#L145)
- Настройки: `services/reports/settings.py::RETENTION_DAYS`
- Тесты: `tests/test_reports_runs.py::test_completed_runs_feed_audit_report`
- Роли: Система (события и фоновые задачи)
- Связанные: R-REPORTS-TIMER-02

## R-REPORTS-SNAP-01 — Снимок метрики за день перезаписывается повторной записью

`draft` · effect

POST /reports/snapshots записывает значение метрики за день (по умолчанию сегодня) в разрезе dimension. Повторная запись по тому же (metric, dimension, day) заменяет значение и taken_at (upsert по metric_snapshots_point). Значение должно быть конечным числом (_decimal). Проверки прав на запись снимков нет.

- Реализация: [`services/reports/service.py::record_snapshot:44-57`](../../services/reports/service.py#L44), [`services/reports/service.py::_decimal:26-33`](../../services/reports/service.py#L26)
- БД: `metric_snapshots_point`
- Тесты: `tests/test_reports_db.py::test_snapshot_rewrite_and_single_active_schedule`
- Связанные: R-REPORTS-SNAP-02, R-REPORTS-SNAP-04

## R-REPORTS-SNAP-02 — Имя метрики — латиница в нижнем регистре с точками-разделителями

`draft` · invariant

Имя метрики должно соответствовать ^[a-z][a-z0-9_]*(\.[a-z0-9_]+)*$. Код проверяет его при записи снимка и в параметрах отчёта (metric_name), БД дублирует проверку CHECK. add_to_snapshot имя не проверяет и полагается на CHECK.

- Реализация: [`services/reports/builders.py::metric_name:36-39`](../../services/reports/builders.py#L36), [`services/reports/service.py::record_snapshot:47-47`](../../services/reports/service.py#L47)
- БД: `metric_snapshots_metric_format`
- Настройки: `services/reports/builders.py::METRIC_RE`
- Тесты: `tests/test_reports_definitions.py::test_definition_params_are_validated`
- Связанные: R-REPORTS-DEF-05

## R-REPORTS-SNAP-03 — Длину разреза снимка проверяет только БД

`draft` · invariant

record_snapshot не проверяет dimension: разрез длиннее 64 символов отклоняет только CHECK metric_snapshots_dimension_len, и это приходит ошибкой БД. В параметрах отчёта то же ограничение проверяет код (литерал 64 в normalize_params).

- Реализация: [`services/reports/service.py::record_snapshot:46-52`](../../services/reports/service.py#L46)
- БД: `metric_snapshots_dimension_len`
- Связанные: R-REPORTS-DEF-06

## R-REPORTS-SNAP-04 — Каждый построенный отчёт прибавляет 1 к служебной метрике reports.runs_completed

`draft` · effect

Подписчик reports.run_completed прибавляет 1 к снимку метрики RUNS_COMPLETED_METRIC за день finished_on в разрезе кода отчёта (upsert с прибавлением). Обработчик не идемпотентен: при повторной доставке события счётчик увеличится повторно.

- Реализация: [`services/reports/consumers.py::count_completed_run:21-28`](../../services/reports/consumers.py#L21), [`services/reports/service.py::add_to_snapshot:60-71`](../../services/reports/service.py#L60)
- БД: `metric_snapshots_point`
- Настройки: `services/reports/settings.py::RUNS_COMPLETED_METRIC`
- Роли: Система (события и фоновые задачи)
- Связанные: R-REPORTS-RUN-05

## R-REPORTS-SCHED-01 — Расписание выгрузки ставит владелец действующего отчёта, у отчёта одно действующее расписание

`draft` · guard

create_schedule доступен только владельцу (_owned_definition) и только для действующего отчёта. Если у отчёта уже есть активное расписание — DomainError; БД дублирует это частичным уникальным индексом export_schedules_one_active (definition_id) WHERE is_active.

- Реализация: [`services/reports/service.py::create_schedule:384-401`](../../services/reports/service.py#L384)
- БД: `export_schedules_one_active`
- Тесты: `tests/test_reports_db.py::test_snapshot_rewrite_and_single_active_schedule`, `tests/test_reports_jobs.py::test_schedule_validation`
- Связанные: R-REPORTS-DEF-01, R-REPORTS-DEF-08

## R-REPORTS-SCHED-02 — Интервал выгрузки — от 1 до 744 часов, первая выгрузка не в прошлом

`draft` · guard

every_hours должен быть в диапазоне MIN_SCHEDULE_INTERVAL_HOURS..MAX_SCHEDULE_INTERVAL_HOURS (1..24*31). БД дублирует диапазон CHECK с литералом 744, который не связан с настройкой. first_run_at не может быть раньше текущего момента; если её не указать, первая выгрузка ставится на «сейчас».

- Реализация: [`services/reports/service.py::create_schedule:387-405`](../../services/reports/service.py#L387)
- БД: `export_schedules_interval`
- Настройки: `services/reports/settings.py::MIN_SCHEDULE_INTERVAL_HOURS`, `services/reports/settings.py::MAX_SCHEDULE_INTERVAL_HOURS`
- Тесты: `tests/test_reports_jobs.py::test_schedule_validation`
- Связанные: R-REPORTS-SCHED-01

## R-REPORTS-SCHED-03 — У выгрузки от 1 до 20 уникальных получателей

`draft` · guard

Список получателей очищается от дублей с сохранением порядка, должен быть непустым и не длиннее MAX_RECIPIENTS (20). Существование получателей не проверяется. В БД recipients обязан быть JSON-массивом.

- Реализация: [`services/reports/service.py::_recipients:366-372`](../../services/reports/service.py#L366)
- БД: `export_schedules_recipients_array`
- Настройки: `services/reports/settings.py::MAX_RECIPIENTS`
- Тесты: `tests/test_reports_jobs.py::test_schedule_validation`
- Связанные: R-REPORTS-NOTIFY-01

## R-REPORTS-SCHED-04 — Отключить расписание может его автор или владелец отчёта

`draft` · permission

deactivate_schedule разрешён, если by равен created_by расписания или owner_id отчёта, иначе AccessDenied. Маршрута в API нет; расписания также отключаются вместе с отчётом и фоновой задачей при ошибке запуска.

- Реализация: [`services/reports/service.py::deactivate_schedule:415-423`](../../services/reports/service.py#L415)
- Связанные: R-REPORTS-DEF-09, R-REPORTS-SCHED-06

## R-REPORTS-SCHED-05 — Фоновая задача ставит в очередь выгрузки, у которых подошёл срок

`draft` · timer

run_scheduled берёт активные расписания действующих отчётов с next_run_at ≤ now (FOR UPDATE SKIP LOCKED) и для каждого создаёт запуск: requested_by — автор расписания, scheduled_for — next_run_at, лимит ручных запусков не применяется. Индекс report_runs_schedule_once не даёт создать второй запуск на тот же слот, CHECK report_runs_schedule_slot требует, чтобы schedule_id и scheduled_for были заданы вместе. Как часто вызывается задача, в модуле не задано.

- Реализация: [`services/reports/jobs.py::run_scheduled:14-37`](../../services/reports/jobs.py#L14), [`services/reports/service.py::request_run:239-245`](../../services/reports/service.py#L239)
- БД: `report_runs_schedule_once`, `report_runs_schedule_slot`
- Тесты: `tests/test_reports_jobs.py::test_due_schedule_runs_and_notifies_recipients`, `tests/test_reports_jobs.py::test_schedule_not_due_and_not_repeated`
- Роли: Система (события и фоновые задачи)
- Связанные: R-REPORTS-RUN-02, R-REPORTS-SCHED-06, R-REPORTS-SCHED-07

## R-REPORTS-SCHED-06 — Расписание, по которому не удалось создать запуск, молча отключается

`draft` · effect

Если request_run для расписания бросает DomainError (например, определение испорчено), run_scheduled ставит расписанию is_active = false и переходит к следующему. Ни автор, ни получатели об этом не уведомляются.

- Реализация: [`services/reports/jobs.py::run_scheduled:29-36`](../../services/reports/jobs.py#L29)
- Роли: Система (события и фоновые задачи)
- Связанные: R-REPORTS-SCHED-05

## R-REPORTS-SCHED-07 — Пропущенные интервалы выгрузки не догоняются

`draft` · timer

После постановки запуска advance сдвигает next_run_at на every_hours, пока он не станет позже now, и записывает last_enqueued_at. Если задача долго не работала, создаётся один запуск, а не по одному на каждый пропущенный интервал.

- Реализация: [`services/reports/service.py::advance:426-431`](../../services/reports/service.py#L426), [`services/reports/jobs.py::run_scheduled:38-38`](../../services/reports/jobs.py#L38)
- Тесты: `tests/test_reports_jobs.py::test_missed_intervals_are_not_caught_up`
- Роли: Система (события и фоновые задачи)
- Связанные: R-REPORTS-SCHED-05

## R-REPORTS-NOTIFY-01 — О готовом отчёте уведомляются запросивший и получатели выгрузки

`draft` · effect

По reports.run_completed создаются уведомления kind=completed запросившему, а для запуска по расписанию — ещё и всем получателям выгрузки (без дублей). Текст: «Отчёт «…» готов (запуск №…)».

- Реализация: [`services/reports/consumers.py::on_run_completed:16-17`](../../services/reports/consumers.py#L16), [`services/reports/service.py::_notification_targets:440-443`](../../services/reports/service.py#L440), [`services/reports/service.py::notify_run_finished:459-474`](../../services/reports/service.py#L459)
- Тесты: `tests/test_reports_runs.py::test_summary_run_is_built_and_requester_notified`, `tests/test_reports_jobs.py::test_due_schedule_runs_and_notifies_recipients`
- Роли: Система (события и фоновые задачи)
- Связанные: R-REPORTS-RUN-05, R-REPORTS-NOTIFY-04

## R-REPORTS-NOTIFY-02 — О неуспешном запуске уведомляются запросивший и владелец отчёта

`draft` · effect

По reports.run_failed (ошибка построения или зависание) уведомления kind=failed с текстом ошибки получают запросивший и владелец отчёта. Получатели выгрузки о сбое не узнают.

- Реализация: [`services/reports/consumers.py::on_run_failed:32-33`](../../services/reports/consumers.py#L32), [`services/reports/service.py::_notification_targets:444-446`](../../services/reports/service.py#L444)
- Тесты: `tests/test_reports_runs.py::test_run_without_data_fails_and_owner_is_told`, `tests/test_reports_jobs.py::test_stuck_run_marked_failed_and_owner_told`
- Роли: Система (события и фоновые задачи)
- Связанные: R-REPORTS-RUN-05, R-REPORTS-TIMER-01

## R-REPORTS-NOTIFY-03 — Об отмене уведомляется только запросивший и только если отменил не он сам

`draft` · effect

Подписчик reports.run_cancelled не создаёт уведомление при reason=by_user. В остальных случаях уведомление kind=cancelled получает только запросивший. Текст всегда «… отменён: отчёт отключён», какой бы ни была причина.

- Реализация: [`services/reports/consumers.py::on_run_cancelled:37-40`](../../services/reports/consumers.py#L37), [`services/reports/service.py::_notification_text:449-456`](../../services/reports/service.py#L449)
- Тесты: `tests/test_reports_runs.py::test_deactivation_cancels_pending_runs_and_schedules`, `tests/test_reports_runs.py::test_pending_run_cancelled_only_by_requester`
- Роли: Система (события и фоновые задачи)
- Связанные: R-REPORTS-DEF-10, R-REPORTS-RUN-06

## R-REPORTS-NOTIFY-04 — Не больше одного уведомления на запуск и получателя

`draft` · invariant

Уведомления вставляются с ON CONFLICT DO NOTHING по ограничению run_notifications_once (run_id, recipient_id), поэтому повторная доставка события уведомление не дублирует. kind уведомления — completed, failed или cancelled.

- Реализация: [`services/reports/service.py::notify_run_finished:467-473`](../../services/reports/service.py#L467)
- БД: `run_notifications_once`, `run_notifications_kind`
- Тесты: `tests/test_reports_runs.py::test_redelivered_request_does_not_rebuild`
- Роли: Система (события и фоновые задачи)
- Связанные: R-REPORTS-NOTIFY-01

## R-REPORTS-NOTIFY-05 — Отметить уведомление прочитанным может только его адресат

`draft` · permission

mark_read возвращает AccessDenied, если recipient_id не совпадает с адресатом. Повторная отметка не меняет read_at. recipient_id API берёт из параметра запроса без аутентификации.

- Реализация: [`services/reports/service.py::mark_read:490-498`](../../services/reports/service.py#L490)

## R-REPORTS-TIMER-01 — Запуск, который строится дольше 30 минут, помечается неуспешным

`draft` · timer

fail_stuck_runs переводит запуски running со started_at раньше now − RUN_TIMEOUT_MINUTES (30) в failed с ошибкой-литералом «превышено время построения отчёта» и публикует reports.run_failed. Запуски, застрявшие в requested (событие так и не обработано), эта задача не трогает.

- Реализация: [`services/reports/jobs.py::fail_stuck_runs:42-62`](../../services/reports/jobs.py#L42)
- Настройки: `services/reports/settings.py::RUN_TIMEOUT_MINUTES`
- Тесты: `tests/test_reports_jobs.py::test_stuck_run_marked_failed_and_owner_told`
- Роли: Система (события и фоновые задачи)
- Связанные: R-REPORTS-NOTIFY-02, R-REPORTS-RUN-07

## R-REPORTS-TIMER-02 — Завершённые запуски удаляются через 30 дней вместе с уведомлениями

`draft` · timer

purge_old_runs удаляет запуски в статусах FINISHED с finished_at раньше now − RETENTION_DAYS (30); незавершённые запуски остаются. Уведомления удаляются каскадом по внешнему ключу ON DELETE CASCADE. Побочные эффекты: аудит запусков теряет историю, а после удаления всех запусков отчёта снова можно менять его тип.

- Реализация: [`services/reports/jobs.py::purge_old_runs:65-75`](../../services/reports/jobs.py#L65)
- Настройки: `services/reports/settings.py::RETENTION_DAYS`, `services/reports/models.py::FINISHED`
- Тесты: `tests/test_reports_jobs.py::test_purge_removes_only_finished_runs_past_retention`
- Роли: Система (события и фоновые задачи)
- Связанные: R-REPORTS-CALC-05, R-REPORTS-DEF-07, R-REPORTS-RUN-08

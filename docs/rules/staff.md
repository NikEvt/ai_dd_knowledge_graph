<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# Правила: staff

Источник: [`knowledge/rules/staff.yaml`](../../knowledge/rules/staff.yaml)

## R-STAFF-HR-01 — Кадровые операции выполняет только действующий сотрудник отдела кадров

`draft` · permission

Приём, изменение карточки, увольнение, закрепление сотрудника за площадкой, назначение ответственного, создание площадки, изменение максимума смены, выдача и ручной отзыв допуска проверяют автора через `_require_hr`. Автор должен существовать, не быть уволенным и иметь должность из HR_ROLES (["hr"]). Иначе AccessDenied «кадровые операции выполняет только отдел кадров», через API это HTTP 403.

- Реализация: [`services/staff/service.py::_require_hr:51-55`](../../services/staff/service.py#L51), [`services/staff/service.py::hire_employee:108-108`](../../services/staff/service.py#L108), [`services/staff/service.py::dismiss_employee:141-141`](../../services/staff/service.py#L141), [`services/staff/service.py::grant_clearance:497-497`](../../services/staff/service.py#L497)
- Настройки: `services/staff/settings.py::HR_ROLES`
- Тесты: `tests/test_staff_employees.py::test_only_hr_hires`, `tests/test_staff_events.py::test_api_errors_map_to_statuses`
- Связанные: R-STAFF-SITE-RESP-01

## R-STAFF-SITE-RESP-01 — Сменами и инструктажами площадки управляет только её ответственный

`draft` · permission

Создать, отменить смену, поставить или снять сотрудника со смены и провести инструктаж может только сотрудник, указанный как ответственный площадки (`sites.responsible_id`). Иначе AccessDenied «сменами площадки управляет только ответственный за площадку». У площадки без ответственного эти операции недоступны никому. Должность и активность ответственного при этом заново не проверяются.

- Реализация: [`services/staff/service.py::_require_responsible:58-62`](../../services/staff/service.py#L58), [`services/staff/service.py::create_shift:252-252`](../../services/staff/service.py#L252), [`services/staff/service.py::assign_to_shift:328-328`](../../services/staff/service.py#L328), [`services/staff/service.py::remove_from_shift:377-377`](../../services/staff/service.py#L377), [`services/staff/service.py::cancel_shift:392-392`](../../services/staff/service.py#L392), [`services/staff/service.py::hold_briefing:469-469`](../../services/staff/service.py#L469)
- Тесты: `tests/test_staff_shifts.py::test_only_site_responsible_plans_shifts`, `tests/test_staff_events.py::test_transferred_responsible_leaves_site_without_one`
- Связанные: R-STAFF-SITE-RESP-02, R-STAFF-SITE-RESP-03

## R-STAFF-SITE-RESP-02 — Ответственным за площадку назначается руководитель, работающий на этой площадке

`draft` · guard

Отдел кадров назначает ответственного (`appoint_responsible`). Сотрудник должен иметь должность из RESPONSIBLE_ROLES (["manager"]) и быть закреплён за этой площадкой. Иначе DomainError. Если позже должность ответственного сменят, он останется ответственным: код это не перепроверяет.

- Реализация: [`services/staff/service.py::appoint_responsible:229-233`](../../services/staff/service.py#L229)
- Настройки: `services/staff/settings.py::RESPONSIBLE_ROLES`
- Тесты: `tests/test_staff_events.py::test_transferred_responsible_leaves_site_without_one`
- Связанные: R-STAFF-HR-01, R-STAFF-SITE-RESP-01

## R-STAFF-SITE-RESP-03 — Перевод или увольнение ответственного оставляет площадку без ответственного

`draft` · effect

Когда закрывается текущее закрепление сотрудника (при переводе или увольнении), `_close_assignment` обнуляет `sites.responsible_id`, если сотрудник был ответственным старой площадки. Пока отдел кадров не назначит нового ответственного, сменами этой площадки никто управлять не может.

- Реализация: [`services/staff/service.py::_close_assignment:183-194`](../../services/staff/service.py#L183), [`services/staff/service.py::transfer_employee:207-207`](../../services/staff/service.py#L207), [`services/staff/service.py::dismiss_employee:147-148`](../../services/staff/service.py#L147)
- Тесты: `tests/test_staff_events.py::test_transferred_responsible_leaves_site_without_one`
- Связанные: R-STAFF-SITE-RESP-04, R-STAFF-TRANSFER-01, R-STAFF-DISMISS-01

## R-STAFF-SITE-RESP-04 — При переводе ответственного создаётся уведомление «нет ответственного» без адресата

`draft` · effect

Подписчик staff.employee_transferred при was_responsible=true создаёт на старой площадке уведомление вида no_responsible. Адресатом берётся текущий responsible_id площадки, а он уже обнулён, поэтому `recipient_id` = NULL. Уведомление привязано к площадке, а не к смене (shift_id NULL), поэтому защиты от дублей нет ни в коде, ни в alerts_unread_uq. При увольнении ответственного такое уведомление не создаётся.

- Реализация: [`services/staff/consumers.py::on_employee_transferred:34-40`](../../services/staff/consumers.py#L34), [`services/staff/service.py::raise_alert:599-616`](../../services/staff/service.py#L599)
- БД: `alerts_kind_check`
- Тесты: `tests/test_staff_events.py::test_transferred_responsible_leaves_site_without_one`
- Роли: Система (события и фоновые задачи)
- Связанные: R-STAFF-SITE-RESP-03, R-STAFF-ALERT-01

## R-STAFF-CARD-01 — Должность сотрудника выбирается из закрытого списка

`draft` · invariant

При приёме и изменении карточки должность проверяется по ROLES (librarian, cashier, guard, manager, hr), иначе DomainError «неизвестная должность». Тот же список литералом повторён в CHECK employees_role_check, и при изменении настройки его нужно менять в двух местах.

- Реализация: [`services/staff/service.py::_validate_card:81-83`](../../services/staff/service.py#L81)
- БД: `employees_role_check`
- Настройки: `services/staff/settings.py::ROLES`
- Тесты: `tests/test_staff_employees.py::test_card_is_validated_on_hire`
- Связанные: R-STAFF-CARD-02, R-STAFF-CARD-03

## R-STAFF-CARD-02 — СНИЛС проверяется по контрольному числу в коде и по формату в БД

`draft` · invariant

Если СНИЛС указан, код проверяет его контрольное число (`snils_valid`, взвешенная сумма по модулю 101), иначе DomainError. Формат «XXX-XXX-XXX YY» проверяет только CHECK employees_snils_format. `snils_valid` сначала удаляет дефисы и пробелы, поэтому СНИЛС без разделителей проходит проверку в коде и отклоняется БД (IntegrityError).

- Реализация: [`services/staff/service.py::snils_valid:69-77`](../../services/staff/service.py#L69), [`services/staff/service.py::_validate_card:84-86`](../../services/staff/service.py#L84)
- БД: `employees_snils_format`
- Тесты: `tests/test_staff_employees.py::test_card_is_validated_on_hire`
- Связанные: R-STAFF-CARD-05

## R-STAFF-CARD-03 — Сотрудник должен быть не моложе 18 лет

`draft` · guard

При приёме и изменении карточки с указанной датой рождения возраст на текущую дату должен быть не меньше MIN_EMPLOYEE_AGE (18), иначе DomainError. Независимо от этого CHECK employees_birth_date_check требует дату рождения позже 1900-01-01.

- Реализация: [`services/staff/service.py::_validate_card:87-92`](../../services/staff/service.py#L87)
- БД: `employees_birth_date_check`
- Настройки: `services/staff/settings.py::MIN_EMPLOYEE_AGE`
- Тесты: `tests/test_staff_employees.py::test_card_is_validated_on_hire`
- Связанные: R-STAFF-CARD-01

## R-STAFF-CARD-04 — Формат паспорта проверяется только в БД

`draft` · invariant

Паспорт должен соответствовать формату «NNNN NNNNNN» (CHECK employees_passport_format). Код формат не проверяет. Неверное значение отклоняется при flush с IntegrityError, через API это HTTP 409.

- Реализация: [`services/staff/service.py::hire_employee:117-120`](../../services/staff/service.py#L117)
- БД: `employees_passport_format`
- Тесты: `tests/test_staff_employees.py::test_card_is_validated_on_hire`
- Связанные: R-STAFF-CARD-05

## R-STAFF-CARD-05 — Паспорт уникален среди работающих, СНИЛС уникален навсегда

`draft` · invariant

Частичный уникальный индекс employees_passport_active_uq запрещает двух неуволенных сотрудников с одним паспортом. После увольнения паспорт можно использовать снова. СНИЛС уникален по всей таблице (employees_snils_key), включая уволенных, поэтому повторно принять уволенного сотрудника отдельной карточкой с тем же СНИЛС нельзя. В коде этих проверок нет: ошибку выдаёт БД.

- Реализация: [`services/staff/service.py::hire_employee:117-120`](../../services/staff/service.py#L117)
- БД: `employees_passport_active_uq`, `employees_snils_key`
- Тесты: `tests/test_staff_employees.py::test_passport_reused_only_after_dismissal`
- Связанные: R-STAFF-CARD-02, R-STAFF-CARD-04, R-STAFF-DISMISS-01

## R-STAFF-HIRE-01 — Неполную карточку принимают, но такой сотрудник не допускается к сменам и допускам

`draft` · config

`hire_employee` требует только должность. ФИО, паспорт, СНИЛС и дата рождения могут быть пустыми. Карточка сохраняется, и публикуется staff.employee_hired, на которое никто не подписан. Незаполненные поля из REQUIRED_EMPLOYEE_FIELDS возвращает `missing_fields`, API показывает их в missing_fields. Приём не закрепляет сотрудника за площадкой, это отдельная операция.

- Реализация: [`services/staff/service.py::hire_employee:108-121`](../../services/staff/service.py#L108), [`services/staff/service.py::missing_fields:65-66`](../../services/staff/service.py#L65)
- Настройки: `services/staff/settings.py::REQUIRED_EMPLOYEE_FIELDS`
- Тесты: `tests/test_staff_employees.py::test_incomplete_card_is_saved_but_lists_missing_fields`, `tests/test_staff_events.py::test_api_hire_and_plan_shift`
- Связанные: R-STAFF-MEMBER-01, R-STAFF-CLEARANCE-01

## R-STAFF-CARD-06 — В карточке меняются только поля из белого списка, карточка уволенного закрыта

`draft` · guard

`update_employee` меняет только поля из EDITABLE_FIELDS (full_name, passport, snils, birth_date, role), на остальные отвечает DomainError «поля нельзя изменить». Карточку уволенного сотрудника изменить нельзя. Новые значения проходят ту же проверку, что и при приёме.

- Реализация: [`services/staff/service.py::update_employee:127-136`](../../services/staff/service.py#L127)
- Настройки: `services/staff/service.py::EDITABLE_FIELDS`
- Тесты: `tests/test_staff_employees.py::test_dismissal_closes_card_and_releases_everything`
- Связанные: R-STAFF-RECHECK-01

## R-STAFF-RECHECK-01 — Изменение отслеживаемых полей карточки неявно публикует staff.employee_updated

`draft` · effect

Слушатель ORM `before_flush` проверяет каждую изменённую карточку Employee в сессии. Если значение какого-либо поля из TRACKED_FIELDS действительно изменилось, он обновляет updated_at и публикует staff.employee_updated со списком изменённых полей. Запись того же значения изменением не считается. Слушатель срабатывает при любом flush, не только в `update_employee`. TRACKED_FIELDS дублирует EDITABLE_FIELDS из service.py.

- Реализация: [`services/staff/listeners.py::_employee_changes:14-22`](../../services/staff/listeners.py#L14)
- Настройки: `services/staff/listeners.py::TRACKED_FIELDS`
- Тесты: `tests/test_staff_employees.py::test_tracked_change_publishes_employee_updated`, `tests/test_staff_employees.py::test_same_value_is_not_a_change`
- Роли: Система (события и фоновые задачи)
- Связанные: R-STAFF-RECHECK-02, R-STAFF-CARD-06

## R-STAFF-RECHECK-02 — Изменение карточки отзывает допуски, требующие перепроверки этих полей

`draft` · effect

Подписчик staff.employee_updated отзывает действующие допуски сотрудника, если recheck_fields их вида пересекаются с изменёнными полями. Причина отзыва — recheck. Отзыв публикует staff.clearance_revoked, и дальше по цепочке сотрудник снимается со смен, требующих этого допуска, а ответственный может получить уведомление о недоукомплектованности.

- Реализация: [`services/staff/consumers.py::on_employee_updated:11-12`](../../services/staff/consumers.py#L11), [`services/staff/service.py::revoke_for_recheck:576-590`](../../services/staff/service.py#L576), [`services/staff/service.py::_revoke:537-549`](../../services/staff/service.py#L537)
- Тесты: `tests/test_staff_employees.py::test_card_change_revokes_clearances_needing_recheck`, `tests/test_staff_employees.py::test_same_value_is_not_a_change`, `tests/test_staff_events.py::test_passport_change_chain_reaches_responsible`
- Роли: Система (события и фоновые задачи)
- Связанные: R-STAFF-RECHECK-01, R-STAFF-CLEARANCE-06, R-STAFF-CLEARANCE-02

## R-STAFF-DISMISS-01 — Увольнение закрывает карточку и закрепление за площадкой

`draft` · effect

`dismiss_employee` проставляет dismissed_at, закрывает текущее закрепление за площадкой (сняв сотрудника с роли ответственного, если он им был) и публикует staff.employee_dismissed. Повторное увольнение даёт DomainError «сотрудник уже уволен». CHECK employees_dismissal_check требует dismissed_at >= hired_at.

- Реализация: [`services/staff/service.py::dismiss_employee:143-149`](../../services/staff/service.py#L143)
- БД: `employees_dismissal_check`
- Тесты: `tests/test_staff_employees.py::test_dismissal_closes_card_and_releases_everything`, `tests/test_staff_employees.py::test_passport_reused_only_after_dismissal`
- Связанные: R-STAFF-DISMISS-02, R-STAFF-SITE-RESP-03

## R-STAFF-DISMISS-02 — Уволенного снимают со всех будущих смен и отзывают все его допуски

`draft` · effect

Подписчик staff.employee_dismissed снимает сотрудника со всех запланированных смен, которые ещё не начались (причина dismissed), и отзывает все действующие допуски с той же причиной. Начавшиеся смены не затрагиваются. Каждое снятие публикует staff.shift_member_removed, что запускает проверку укомплектованности.

- Реализация: [`services/staff/consumers.py::on_employee_dismissed:16-18`](../../services/staff/consumers.py#L16), [`services/staff/service.py::drop_from_future_shifts:415-434`](../../services/staff/service.py#L415), [`services/staff/service.py::revoke_all_clearances:564-571`](../../services/staff/service.py#L564)
- Тесты: `tests/test_staff_employees.py::test_dismissal_closes_card_and_releases_everything`
- Роли: Система (события и фоновые задачи)
- Связанные: R-STAFF-DISMISS-01, R-STAFF-STAFFING-01

## R-STAFF-TRANSFER-01 — Сотрудник одновременно закреплён только за одной площадкой

`draft` · invariant

`transfer_employee` закрепляет сотрудника за площадкой. Если он уже работал на другой, старое закрепление закрывается (ended_at) и открывается новое. Уволенного закрепить нельзя, повторно закрепить за той же площадкой тоже нельзя (DomainError). Событие staff.employee_transferred публикуется, только если было предыдущее закрепление. Индекс assignments_current_uq допускает одно открытое закрепление на сотрудника.

- Реализация: [`services/staff/service.py::transfer_employee:201-221`](../../services/staff/service.py#L201), [`services/staff/service.py::_close_assignment:183-194`](../../services/staff/service.py#L183)
- БД: `assignments_current_uq`, `assignments_period_check`
- Тесты: `tests/test_staff_events.py::test_transfer_drops_future_shifts_at_old_site_only`, `tests/test_staff_events.py::test_api_hire_and_plan_shift`
- Связанные: R-STAFF-TRANSFER-02, R-STAFF-SITE-RESP-03

## R-STAFF-TRANSFER-02 — Перевод снимает сотрудника только с будущих смен старой площадки

`draft` · effect

Подписчик staff.employee_transferred снимает сотрудника с запланированных и ещё не начавшихся смен старой площадки (причина transferred). На уже идущей смене сотрудник остаётся. Снятие может сделать смену недоукомплектованной и вызвать уведомление ответственному.

- Реализация: [`services/staff/consumers.py::on_employee_transferred:30-33`](../../services/staff/consumers.py#L30), [`services/staff/service.py::drop_from_future_shifts:415-434`](../../services/staff/service.py#L415)
- Тесты: `tests/test_staff_events.py::test_transfer_drops_future_shifts_at_old_site_only`, `tests/test_staff_events.py::test_transfer_leaves_shift_understaffed_and_alerts_responsible`
- Роли: Система (события и фоновые задачи)
- Связанные: R-STAFF-TRANSFER-01, R-STAFF-STAFFING-01

## R-STAFF-SITE-01 — Максимум сотрудников на смене для новой площадки — 6

`draft` · config

Если при создании площадки максимум не указан, `create_site` берёт MAX_SHIFT_STAFF (6). Этот максимум служит вместимостью по умолчанию для новых смен площадки.

- Реализация: [`services/staff/service.py::create_site:157-157`](../../services/staff/service.py#L157)
- БД: `sites_max_shift_staff_check`
- Настройки: `services/staff/settings.py::MAX_SHIFT_STAFF`
- Связанные: R-STAFF-SITE-02, R-STAFF-SHIFT-02

## R-STAFF-SITE-02 — Максимум смены площадки — от 1 до 20

`draft` · invariant

`set_site_max_staff` принимает значение от 1 до SHIFT_STAFF_CEILING (20), иначе DomainError. CHECK sites_max_shift_staff_check задаёт те же границы литералом 20, а не настройкой. `create_site` границы в коде не проверяет, там действует только CHECK.

- Реализация: [`services/staff/service.py::set_site_max_staff:165-168`](../../services/staff/service.py#L165)
- БД: `sites_max_shift_staff_check`
- Настройки: `services/staff/settings.py::SHIFT_STAFF_CEILING`
- Тесты: `tests/test_staff_shifts.py::test_site_maximum_cannot_drop_below_planned_shifts`
- Связанные: R-STAFF-SITE-03, R-STAFF-SITE-01

## R-STAFF-SITE-03 — Максимум площадки нельзя опустить ниже вместимости её запланированных смен

`draft` · invariant

Триггер trg_site_max_shift_staff (функция check_site_max_staff) отклоняет уменьшение max_shift_staff, если у площадки есть смена со статусом planned и вместимостью больше нового значения. В коде такой проверки нет. Завершённые (done) и отменённые смены не мешают.

- Реализация: [`services/staff/service.py::set_site_max_staff:168-169`](../../services/staff/service.py#L168)
- БД: `trg_site_max_shift_staff`, `check_site_max_staff`
- Тесты: `tests/test_staff_shifts.py::test_site_maximum_cannot_drop_below_planned_shifts`, `tests/test_staff_events.py::test_close_finished_shifts_job`
- Связанные: R-STAFF-SITE-02, R-STAFF-SHIFT-CLOSE-01

## R-STAFF-SHIFT-01 — Смена планируется в будущем, не дальше 60 дней и длится не больше 12 часов

`draft` · guard

`create_shift` требует, чтобы смена начиналась позже текущего момента и не позже PLANNING_HORIZON_DAYS (60) дней вперёд. Конец должен быть позже начала, длительность — не больше MAX_SHIFT_HOURS (12) часов. Указанный обязательный вид допуска должен существовать. CHECK shifts_period_check дублирует условие ends_at > starts_at.

- Реализация: [`services/staff/service.py::create_shift:253-261`](../../services/staff/service.py#L253)
- БД: `shifts_period_check`
- Настройки: `services/staff/settings.py::PLANNING_HORIZON_DAYS`, `services/staff/settings.py::MAX_SHIFT_HOURS`
- Тесты: `tests/test_staff_shifts.py::test_shift_time_rules`
- Связанные: R-STAFF-SHIFT-02, R-STAFF-SITE-RESP-01

## R-STAFF-SHIFT-02 — Вместимость смены ограничена максимумом площадки, минимальный состав — вместимостью

`draft` · invariant

Если вместимость не указана, берётся max_shift_staff площадки. Минимальный состав не может превышать вместимость (DomainError в коде и CHECK shifts_min_staff_check). Что вместимость не больше максимума площадки, код не проверяет: это делает триггер trg_shift_capacity (check_shift_capacity), через API ошибка возвращается как 409 «exceeds site maximum». CHECK shifts_capacity_check ограничивает вместимость 1–20 литералом.

- Реализация: [`services/staff/service.py::create_shift:262-264`](../../services/staff/service.py#L262)
- БД: `trg_shift_capacity`, `check_shift_capacity`, `shifts_capacity_check`, `shifts_min_staff_check`
- Тесты: `tests/test_staff_shifts.py::test_capacity_bounded_by_site_maximum`, `tests/test_staff_events.py::test_api_errors_map_to_statuses`
- Связанные: R-STAFF-SHIFT-03, R-STAFF-SITE-01, R-STAFF-SITE-02

## R-STAFF-SHIFT-03 — Вместимость смены нельзя уменьшить ниже числа назначенных сотрудников

`draft` · invariant

При UPDATE вместимости или площадки смены триггер trg_shift_capacity отклоняет изменение, если назначенных (assigned) сотрудников больше новой вместимости. Операции изменения вместимости в сервисе нет, правило действует только на уровне БД.

- БД: `trg_shift_capacity`, `check_shift_capacity`
- Тесты: `tests/test_staff_shifts.py::test_capacity_cannot_shrink_below_roster`
- Связанные: R-STAFF-SHIFT-02, R-STAFF-MEMBER-03

## R-STAFF-SHIFT-04 — Нет двух запланированных смен площадки с одним началом и одним видом допуска

`draft` · invariant

Частичный уникальный индекс shifts_planned_uq на (site_id, starts_at, coalesce(required_clearance, '')) при status = 'planned' запрещает дубли запланированных смен. В коде проверки нет: дубль отклоняет БД. После отмены или завершения смены слот можно занять снова.

- Реализация: [`services/staff/service.py::create_shift:265-276`](../../services/staff/service.py#L265)
- БД: `shifts_planned_uq`
- Связанные: R-STAFF-SHIFT-01

## R-STAFF-SHIFT-05 — Новая смена с ненулевым минимумом сразу помечена недоукомплектованной, без уведомления

`draft` · effect

`create_shift` выставляет understaffed = (min_staff > 0). Событие staff.shift_understaffed при этом не публикуется, и ответственный уведомления не получает. Флаг снимается, когда число назначенных достигнет min_staff.

- Реализация: [`services/staff/service.py::create_shift:265-276`](../../services/staff/service.py#L265)
- Тесты: `tests/test_staff_events.py::test_transfer_leaves_shift_understaffed_and_alerts_responsible`
- Связанные: R-STAFF-MEMBER-05, R-STAFF-STAFFING-01

## R-STAFF-MEMBER-01 — На смену ставят действующего сотрудника своей площадки с полной карточкой

`draft` · guard

`assign_to_shift` разрешён только для запланированной и ещё не начавшейся смены. Сотрудник должен быть не уволен, иметь заполненные поля REQUIRED_EMPLOYEE_FIELDS и быть закреплён за площадкой смены. Иначе DomainError.

- Реализация: [`services/staff/service.py::assign_to_shift:329-338`](../../services/staff/service.py#L329)
- Настройки: `services/staff/settings.py::REQUIRED_EMPLOYEE_FIELDS`
- Тесты: `tests/test_staff_shifts.py::test_shift_admission_needs_full_card_and_own_site`, `tests/test_staff_shifts.py::test_cancel_shift_releases_staff`
- Связанные: R-STAFF-HIRE-01, R-STAFF-MEMBER-02, R-STAFF-MEMBER-03, R-STAFF-MEMBER-04

## R-STAFF-MEMBER-02 — На смену с обязательным допуском ставят только при действующем допуске

`draft` · guard

Если у смены задан required_clearance, у сотрудника должен быть допуск этого вида со статусом active. Иначе DomainError «у сотрудника нет действующего допуска для этой смены». Код не проверяет, что допуск действует на дату смены: истечение до начала смены обрабатывает только фоновая задача expire_clearances.

- Реализация: [`services/staff/service.py::assign_to_shift:339-342`](../../services/staff/service.py#L339), [`services/staff/service.py::active_clearance:295-300`](../../services/staff/service.py#L295)
- Тесты: `tests/test_staff_shifts.py::test_shift_with_clearance_requires_active_one`
- Связанные: R-STAFF-CLEARANCE-05, R-STAFF-CLEARANCE-06

## R-STAFF-MEMBER-03 — Смену нельзя переукомплектовать, сотрудника нельзя назначить дважды

`draft` · invariant

Код отклоняет повторное назначение того же сотрудника и назначение на смену, где назначенных уже столько, сколько её вместимость. БД дублирует это: триггер trg_shift_members_limit (check_shift_members) при INSERT или переводе в assigned блокирует строку на смене (FOR UPDATE) и отклоняет переполнение, а индекс shift_members_assigned_uq запрещает две активные записи одного сотрудника на смене.

- Реализация: [`services/staff/service.py::assign_to_shift:343-346`](../../services/staff/service.py#L343)
- БД: `trg_shift_members_limit`, `check_shift_members`, `shift_members_assigned_uq`
- Тесты: `tests/test_staff_shifts.py::test_full_shift_refuses_more_staff`, `tests/test_staff_shifts.py::test_member_limit_trigger_guards_direct_inserts`
- Связанные: R-STAFF-SHIFT-03

## R-STAFF-MEMBER-04 — Между сменами сотрудника не меньше 8 часов отдыха

`draft` · guard

`_check_rest` отклоняет назначение, если у сотрудника есть другая назначенная смена, которая пересекается с новой, расширенной на MIN_REST_HOURS (8 ч) с каждой стороны. Учитываются только смены со статусом planned. Смена, которую задача close_finished_shifts уже перевела в done, в расчёт не попадает.

- Реализация: [`services/staff/service.py::_check_rest:303-321`](../../services/staff/service.py#L303), [`services/staff/service.py::assign_to_shift:347-347`](../../services/staff/service.py#L347)
- Настройки: `services/staff/settings.py::MIN_REST_HOURS`
- Тесты: `tests/test_staff_shifts.py::test_rest_between_shifts`
- Связанные: R-STAFF-SHIFT-CLOSE-01

## R-STAFF-MEMBER-05 — Назначение до минимального состава снимает пометку недоукомплектованности

`draft` · effect

После добавления сотрудника `assign_to_shift` снимает флаг understaffed, если число назначенных достигло min_staff. После этого новое снятие сотрудника может снова поставить флаг и создать уведомление.

- Реализация: [`services/staff/service.py::assign_to_shift:352-353`](../../services/staff/service.py#L352)
- Тесты: `tests/test_staff_events.py::test_transfer_leaves_shift_understaffed_and_alerts_responsible`, `tests/test_staff_events.py::test_api_hire_and_plan_shift`
- Связанные: R-STAFF-SHIFT-05, R-STAFF-STAFFING-01

## R-STAFF-MEMBER-06 — Снятие со смены сохраняет запись с причиной и публикует staff.shift_member_removed

`draft` · effect

Ответственный снимает сотрудника вручную (причина manual). Система снимает его при отмене смены (shift_cancelled), увольнении (dismissed), переводе (transferred) или потере допуска (clearance_lost). Запись не удаляется: она получает status removed, removed_at и removed_reason. Каждое снятие публикует staff.shift_member_removed. CHECK shift_members_removal_check связывает status removed с заполненным removed_at.

- Реализация: [`services/staff/service.py::_remove_member:357-370`](../../services/staff/service.py#L357), [`services/staff/service.py::remove_from_shift:378-387`](../../services/staff/service.py#L378)
- БД: `shift_members_removal_check`, `shift_members_status_check`
- Тесты: `tests/test_staff_events.py::test_understaffed_alert_is_not_duplicated_until_read`
- Связанные: R-STAFF-STAFFING-01, R-STAFF-CANCEL-01

## R-STAFF-CANCEL-01 — Отменить можно только запланированную смену, её состав снимается без уведомлений

`draft` · guard

`cancel_shift` разрешена только при status planned. Смена переводится в cancelled, все назначенные сотрудники снимаются с причиной shift_cancelled. Уведомление о недоукомплектованности не создаётся: `check_staffing` игнорирует смены не в статусе planned.

- Реализация: [`services/staff/service.py::cancel_shift:393-402`](../../services/staff/service.py#L393)
- БД: `shifts_status_check`
- Тесты: `tests/test_staff_shifts.py::test_cancel_shift_releases_staff`
- Связанные: R-STAFF-MEMBER-06, R-STAFF-STAFFING-01

## R-STAFF-STAFFING-01 — Снятие сотрудника ниже минимума помечает смену недоукомплектованной

`draft` · effect

Подписчик staff.shift_member_removed вызывает `check_staffing`. Если смена запланирована, ещё не началась, ещё не помечена и назначенных меньше min_staff, она получает understaffed = true и публикуется staff.shift_understaffed. Если пометка уже стоит, событие повторно не публикуется.

- Реализация: [`services/staff/consumers.py::on_shift_member_removed:44-45`](../../services/staff/consumers.py#L44), [`services/staff/service.py::check_staffing:440-451`](../../services/staff/service.py#L440)
- Тесты: `tests/test_staff_events.py::test_transfer_leaves_shift_understaffed_and_alerts_responsible`, `tests/test_staff_events.py::test_expire_job_drops_employee_from_shifts_needing_clearance`, `tests/test_staff_shifts.py::test_cancel_shift_releases_staff`
- Роли: Система (события и фоновые задачи)
- Связанные: R-STAFF-ALERT-01, R-STAFF-MEMBER-05, R-STAFF-SHIFT-05

## R-STAFF-ALERT-01 — Ответственный получает одно непрочитанное уведомление о недоукомплектованной смене

`draft` · effect

Подписчик staff.shift_understaffed создаёт уведомление вида understaffed текущему ответственному площадки с текстом «На смене N из минимум M сотрудников». Если по этой смене уже есть непрочитанное уведомление того же вида, новое не создаётся. Это проверяет и код, и частичный уникальный индекс alerts_unread_uq (shift_id, kind) WHERE read_at IS NULL.

- Реализация: [`services/staff/consumers.py::on_shift_understaffed:49-56`](../../services/staff/consumers.py#L49), [`services/staff/service.py::raise_alert:599-616`](../../services/staff/service.py#L599)
- БД: `alerts_unread_uq`, `alerts_kind_check`
- Тесты: `tests/test_staff_events.py::test_transfer_leaves_shift_understaffed_and_alerts_responsible`, `tests/test_staff_events.py::test_understaffed_alert_is_not_duplicated_until_read`, `tests/test_staff_events.py::test_passport_change_chain_reaches_responsible`
- Роли: Система (события и фоновые задачи)
- Связанные: R-STAFF-STAFFING-01, R-STAFF-ALERT-02

## R-STAFF-ALERT-02 — Уведомление отмечает прочитанным адресат или текущий ответственный площадки

`draft` · permission

`mark_alert_read` разрешена адресату уведомления или текущему ответственному площадки, иначе AccessDenied. Поэтому уведомление no_responsible без адресата может прочитать новый ответственный. Повторная отметка не меняет read_at. HTTP-маршрута для этой операции нет.

- Реализация: [`services/staff/service.py::mark_alert_read:630-633`](../../services/staff/service.py#L630)
- Тесты: `tests/test_staff_events.py::test_understaffed_alert_is_not_duplicated_until_read`
- Связанные: R-STAFF-ALERT-01, R-STAFF-SITE-RESP-04

## R-STAFF-BRIEFING-01 — Инструктаж проводит ответственный площадки другому сотруднику этой площадки

`draft` · guard

`hold_briefing` проводит только ответственный площадки, и только для другого сотрудника (CHECK briefings_instructor_check дублирует запрет на инструктаж самому себе), закреплённого за этой площадкой. Временем инструктажа становится текущий момент. Уникальный ключ briefings_once_key запрещает дубль (сотрудник, тема, время).

- Реализация: [`services/staff/service.py::hold_briefing:469-483`](../../services/staff/service.py#L469)
- БД: `briefings_instructor_check`, `briefings_once_key`
- Связанные: R-STAFF-CLEARANCE-02, R-STAFF-SITE-RESP-01

## R-STAFF-CLEARANCE-01 — Допуск выдаётся действующему сотруднику с полной карточкой, один активный на вид

`draft` · guard

`grant_clearance` (только отдел кадров) требует, чтобы сотрудник не был уволен и имел заполненные REQUIRED_EMPLOYEE_FIELDS, а вид допуска существовал. Если у сотрудника уже есть активный допуск этого вида, выдаётся DomainError «уже есть действующий допуск». БД дублирует запрет частичным индексом clearances_active_uq.

- Реализация: [`services/staff/service.py::grant_clearance:499-508`](../../services/staff/service.py#L499)
- БД: `clearances_active_uq`
- Настройки: `services/staff/settings.py::REQUIRED_EMPLOYEE_FIELDS`
- Тесты: `tests/test_staff_employees.py::test_incomplete_card_is_saved_but_lists_missing_fields`, `tests/test_staff_employees.py::test_regrant_after_recheck_needs_fresh_briefing`
- Связанные: R-STAFF-CLEARANCE-02, R-STAFF-CLEARANCE-03, R-STAFF-HIRE-01

## R-STAFF-CLEARANCE-02 — Для допуска с инструктажем нужен инструктаж по теме не старше 30 дней

`draft` · guard

Если у вида допуска задан briefing_topic, нужен инструктаж сотрудника по этой теме, проведённый не раньше чем BRIEFING_VALID_DAYS (30) дней назад. Площадка инструктажа значения не имеет. Найденный инструктаж записывается в briefing_id допуска. При повторной выдаче после отзыва «на перепроверку» действует то же требование.

- Реализация: [`services/staff/service.py::grant_clearance:509-516`](../../services/staff/service.py#L509), [`services/staff/service.py::_fresh_briefing:486-493`](../../services/staff/service.py#L486)
- Настройки: `services/staff/settings.py::BRIEFING_VALID_DAYS`
- Тесты: `tests/test_staff_employees.py::test_regrant_after_recheck_needs_fresh_briefing`
- Связанные: R-STAFF-BRIEFING-01, R-STAFF-RECHECK-02

## R-STAFF-CLEARANCE-03 — Срок допуска — valid_days его вида от момента выдачи

`draft` · calculation

expires_at = момент выдачи + clearance_kinds.valid_days. CHECK clearance_kinds_valid_days_check ограничивает valid_days от 1 до 1095, CHECK clearances_period_check требует expires_at > granted_at. После выдачи публикуется staff.clearance_granted, на которое никто не подписан.

- Реализация: [`services/staff/service.py::grant_clearance:517-532`](../../services/staff/service.py#L517)
- БД: `clearance_kinds_valid_days_check`, `clearances_period_check`
- Тесты: `tests/test_staff_events.py::test_expire_job_drops_employee_from_shifts_needing_clearance`
- Связанные: R-STAFF-CLEARANCE-05

## R-STAFF-CLEARANCE-04 — Отдел кадров вручную отзывает только действующий допуск

`draft` · guard

`revoke_clearance` (только отдел кадров) отзывает допуск со статусом active. Для уже недействующего выдаётся DomainError «допуск уже не действует». Отзыв ставит status revoked, revoked_at и причину, затем публикует staff.clearance_revoked. CHECK clearances_revoked_check требует revoked_at у отозванного допуска. Для этой операции нет HTTP-маршрута и тестов.

- Реализация: [`services/staff/service.py::revoke_clearance:555-559`](../../services/staff/service.py#L555), [`services/staff/service.py::_revoke:536-549`](../../services/staff/service.py#L536)
- БД: `clearances_revoked_check`, `clearances_status_check`
- Связанные: R-STAFF-CLEARANCE-06

## R-STAFF-CLEARANCE-05 — Фоновая задача переводит допуски с наступившим сроком в expired

`draft` · timer

`expire_clearances(now)` переводит все активные допуски с expires_at <= now в статус expired и для каждого публикует staff.clearance_expired. Расписание запуска в модуле не задано. До запуска задачи истёкший допуск формально считается действующим, в том числе при назначении на смену.

- Реализация: [`services/staff/jobs.py::expire_clearances:11-23`](../../services/staff/jobs.py#L11)
- Тесты: `tests/test_staff_events.py::test_expire_job_drops_employee_from_shifts_needing_clearance`
- Роли: Система (события и фоновые задачи)
- Связанные: R-STAFF-CLEARANCE-06, R-STAFF-MEMBER-02, R-STAFF-CLEARANCE-03

## R-STAFF-CLEARANCE-06 — Потеря допуска снимает сотрудника с будущих смен, требующих этого допуска

`draft` · effect

Подписчик staff.clearance_revoked и staff.clearance_expired снимает сотрудника со всех запланированных и ещё не начавшихся смен, у которых required_clearance совпадает с видом потерянного допуска (причина clearance_lost). Остальные смены, в том числе уже начавшиеся, не затрагиваются. Снятие может вызвать пометку недоукомплектованности и уведомление ответственному.

- Реализация: [`services/staff/consumers.py::on_clearance_lost:23-26`](../../services/staff/consumers.py#L23), [`services/staff/service.py::drop_from_future_shifts:415-434`](../../services/staff/service.py#L415)
- Тесты: `tests/test_staff_events.py::test_expire_job_drops_employee_from_shifts_needing_clearance`, `tests/test_staff_events.py::test_passport_change_chain_reaches_responsible`
- Роли: Система (события и фоновые задачи)
- Связанные: R-STAFF-CLEARANCE-05, R-STAFF-RECHECK-02, R-STAFF-STAFFING-01

## R-STAFF-SHIFT-CLOSE-01 — Фоновая задача закрывает завершившиеся смены

`draft` · timer

`close_finished_shifts(now)` переводит смены со статусом planned и ends_at <= now в статус done. Записи о назначенных сотрудниках не меняются. Расписание запуска в модуле не задано. После закрытия такие смены не мешают уменьшить максимум площадки и не учитываются в проверке отдыха между сменами.

- Реализация: [`services/staff/jobs.py::close_finished_shifts:27-32`](../../services/staff/jobs.py#L27)
- БД: `shifts_status_check`
- Тесты: `tests/test_staff_events.py::test_close_finished_shifts_job`
- Роли: Система (события и фоновые задачи)
- Связанные: R-STAFF-SITE-03, R-STAFF-MEMBER-04

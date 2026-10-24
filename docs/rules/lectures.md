<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# Правила: lectures

Источник: [`knowledge/rules/lectures.yaml`](../../knowledge/rules/lectures.yaml)

## R-LECTURES-EVENT-01 — Мероприятие объявляют не позднее чем за MIN_LEAD_TIME до начала

`draft` · guard

create_event отклоняет мероприятие, если до начала осталось меньше settings.MIN_LEAD_TIME (24 часа): «мероприятие нужно объявить хотя бы за сутки до начала». При переносе на другую площадку (move_event) этот срок не проверяется.

- Реализация: [`services/lectures/service.py::create_event:135-137`](../../services/lectures/service.py#L135)
- Настройки: `services/lectures/settings.py::MIN_LEAD_TIME`
- Тесты: `tests/test_lectures_events.py::test_event_announced_at_least_a_day_ahead`
- Связанные: R-LECTURES-MOVE-01
- ⚠ Расхождение со схемой: В тексте ошибки срок записан литералом («за сутки»), а проверка берёт его из настройки MIN_LEAD_TIME. Если настройку поменять, сообщение станет неверным.

## R-LECTURES-EVENT-02 — Тема мероприятия обязательна

`draft` · invariant

create_event отклоняет пустую тему или тему из одних пробелов («укажите тему мероприятия»), а перед сохранением обрезает пробелы по краям. В БД то же самое требует CHECK events_title_check (length(btrim(title)) > 0).

- Реализация: [`services/lectures/service.py::create_event:138-151`](../../services/lectures/service.py#L138)
- БД: `events_title_check`

## R-LECTURES-EVENT-03 — Мероприятие возможно только на площадке с заданным лимитом мест

`draft` · guard

Мероприятие нельзя создать или перенести на площадку без записи в реплике lectures.venue_capacity_limits: _venue_limit выдаёт ошибку «для площадки не задан лимит мест». Триггер trg_lecture_capacity_limit (функция check_capacity) делает ту же проверку на INSERT и на UPDATE полей capacity и venue_id.

- Реализация: [`services/lectures/service.py::_venue_limit:37-41`](../../services/lectures/service.py#L37), [`services/lectures/service.py::create_event:140-140`](../../services/lectures/service.py#L140), [`services/lectures/service.py::move_event:206-206`](../../services/lectures/service.py#L206)
- БД: `trg_lecture_capacity_limit`, `check_capacity`
- Тесты: `tests/test_lectures_events.py::test_event_on_venue_without_limit_rejected`
- Связанные: R-LECTURES-EVENT-05, R-LECTURES-LIMIT-02

## R-LECTURES-EVENT-04 — По умолчанию мест столько, сколько позволяет лимит площадки

`draft` · calculation

Если организатор не указал число мест, create_event берёт лимит площадки. Флаг capacity_manual ставится только когда мест меньше лимита. Флаг решает, будет ли число мест следовать за последующими изменениями лимита.

- Реализация: [`services/lectures/service.py::create_event:140-161`](../../services/lectures/service.py#L140)
- Тесты: `tests/test_lectures_events.py::test_event_takes_venue_limit_by_default`
- Связанные: R-LECTURES-LIMIT-03, R-LECTURES-CAPACITY-02

## R-LECTURES-EVENT-05 — Мест на мероприятии не больше лимита площадки — проверяет только БД

`draft` · invariant

Ни create_event, ни change_capacity, ни move_event не сравнивают заданное число мест с лимитом площадки. Превышение отклоняет только триггер trg_lecture_capacity_limit («event capacity … exceeds venue … limit …»), и клиент получает ошибку БД, а не DomainError. Если перенос отклонён, его транзакция откатывается, и регистрации на старой площадке остаются.

- БД: `trg_lecture_capacity_limit`, `check_capacity`
- Тесты: `tests/test_lectures_events.py::test_capacity_above_venue_limit_rejected_by_db`, `tests/test_lectures_registrations.py::test_move_capacity_above_new_limit_rejected`
- Связанные: R-LECTURES-EVENT-03, R-LECTURES-LIMIT-05

## R-LECTURES-EVENT-06 — Число мест и лимит площадки положительны

`draft` · invariant

Число мест мероприятия и лимит площадки должны быть больше нуля. API проверяет это через Field(gt=0) в EventIn, CapacityIn, MoveIn и VenueLimitIn. set_venue_capacity_limit отклоняет лимит <= 0. В БД это обеспечивают CHECK events_capacity_check и venue_capacity_limits_max_capacity_check.

- Реализация: [`services/lectures/api.py::EventIn:24-24`](../../services/lectures/api.py#L24), [`services/lectures/api.py::CapacityIn:38-38`](../../services/lectures/api.py#L38), [`services/lectures/api.py::MoveIn:44-44`](../../services/lectures/api.py#L44), [`services/lectures/api.py::VenueLimitIn:16-16`](../../services/lectures/api.py#L16), [`services/lectures/service.py::set_venue_capacity_limit:76-77`](../../services/lectures/service.py#L76)
- БД: `events_capacity_check`, `venue_capacity_limits_max_capacity_check`
- Связанные: R-LECTURES-LIMIT-01

## R-LECTURES-EVENT-07 — Площадка не принимает два мероприятия с одним временем начала

`draft` · guard

create_event и move_event отклоняют мероприятие, если на площадке уже есть запланированное (scheduled) мероприятие с тем же starts_at. Сравнивается только точное время начала: мероприятия с перекрывающимися интервалами допускаются, потому что длительность не хранится. В БД то же правило задаёт частичный уникальный индекс events_venue_slot_uq (venue_id, starts_at) WHERE status = 'scheduled'.

- Реализация: [`services/lectures/service.py::create_event:143-149`](../../services/lectures/service.py#L143), [`services/lectures/service.py::move_event:207-215`](../../services/lectures/service.py#L207)
- БД: `events_venue_slot_uq`
- Тесты: `tests/test_lectures_events.py::test_venue_cannot_host_two_events_at_once`
- Связанные: R-LECTURES-MOVE-01

## R-LECTURES-EVENT-08 — Жизненный цикл мероприятия — scheduled, cancelled, finished

`draft` · invariant

Мероприятие создаётся в статусе scheduled. Отмена организатором (cancel_event) переводит его в cancelled, фоновая задача finish_past_events — в finished. Других статусов нет: это закреплено CHECK events_status_check. Триггер trg_lecture_touch (touch_updated_at) обновляет updated_at при любом UPDATE, если код не задал его сам.

- Реализация: [`services/lectures/service.py::cancel_event:240-241`](../../services/lectures/service.py#L240), [`services/lectures/jobs.py::finish_past_events:70-72`](../../services/lectures/jobs.py#L70)
- БД: `events_status_check`, `trg_lecture_touch`, `touch_updated_at`
- Тесты: `tests/test_lectures_registrations.py::test_cancel_event_notifies_registered_and_waitlisted`, `tests/test_lectures_jobs.py::test_past_events_finished`
- Связанные: R-LECTURES-CANCEL-01, R-LECTURES-FINISH-01

## R-LECTURES-MANAGE-01 — Мероприятием управляет только организатор и только пока оно запланировано

`draft` · permission

Изменить число мест, перенести, отменить мероприятие или снять слушателя может только организатор этого мероприятия. Для остальных _own_lecture выдаёт AccessDenied «мероприятием управляет только его организатор». Если мероприятие не в статусе scheduled, возвращается DomainError «мероприятие уже отменено или прошло». Время начала не проверяется: мероприятие, которое уже началось, но ещё не стало finished (FINISH_AFTER), можно отменить, перенести или изменить. organizer_id приходит в теле запроса, аутентификации нет.

- Реализация: [`services/lectures/service.py::_own_lecture:28-34`](../../services/lectures/service.py#L28)
- Тесты: `tests/test_lectures_events.py::test_only_organizer_changes_capacity`, `tests/test_lectures_registrations.py::test_only_listener_cancels_own_registration`
- Связанные: R-LECTURES-CANCEL-REG-02

## R-LECTURES-CAPACITY-01 — Нельзя сократить места ниже числа подтверждённых регистраций

`draft` · guard

change_capacity отклоняет новое число мест, если оно меньше числа регистраций в статусе confirmed: «на мероприятие уже зарегистрировано больше слушателей».

- Реализация: [`services/lectures/service.py::change_capacity:167-168`](../../services/lectures/service.py#L167)
- Тесты: `tests/test_lectures_events.py::test_capacity_cannot_drop_below_registered`
- Связанные: R-LECTURES-LIMIT-05

## R-LECTURES-CAPACITY-02 — Число мест, равное лимиту, снова следует за лимитом площадки

`draft` · calculation

При изменении числа мест флаг capacity_manual пересчитывается как «мест меньше текущего лимита». Если организатор вернул число мест к лимиту, флаг снимается, и мероприятие снова подтягивается к будущим изменениям лимита (R-LECTURES-LIMIT-03).

- Реализация: [`services/lectures/service.py::change_capacity:169-174`](../../services/lectures/service.py#L169)
- Тесты: `tests/test_lectures_events.py::test_restoring_full_capacity_follows_limit_again`, `tests/test_lectures_events.py::test_manual_capacity_kept_even_when_it_matches_old_limit`, `tests/test_lectures_events.py::test_capacity_cannot_drop_below_registered`
- Связанные: R-LECTURES-EVENT-04, R-LECTURES-LIMIT-03

## R-LECTURES-CAPACITY-03 — Новые места отдаются листу ожидания

`draft` · effect

Если change_capacity увеличил число мест, публикуется lectures.capacity_increased. Подписчик on_capacity_increased вызывает fill_from_waitlist, и свободные места получают первые в листе ожидания.

- Реализация: [`services/lectures/service.py::change_capacity:170-176`](../../services/lectures/service.py#L170), [`services/lectures/consumers.py::on_capacity_increased:21-22`](../../services/lectures/consumers.py#L21)
- Тесты: `tests/test_lectures_registrations.py::test_organizer_adds_seats_for_waitlist`
- Связанные: R-LECTURES-WAITLIST-06, R-LECTURES-LIMIT-04

## R-LECTURES-LIMIT-01 — Лимит мест площадки меняется асинхронно через событие, права не проверяются

`draft` · effect

PUT /venues/{venue_id}/capacity-limit (set_venue_capacity_limit) только проверяет, что лимит положительный, и публикует lectures.venue_limit_changed (ответ 202). Сама реплика пишется подписчиком. Роль вызывающего и существование площадки не проверяются.

- Реализация: [`services/lectures/service.py::set_venue_capacity_limit:75-80`](../../services/lectures/service.py#L75), [`services/lectures/api.py::set_limit:63-64`](../../services/lectures/api.py#L63)
- БД: `venue_capacity_limits_max_capacity_check`
- Тесты: `tests/test_lectures_events.py::test_limit_change_updates_replica_and_untouched_events`
- Связанные: R-LECTURES-LIMIT-02

## R-LECTURES-LIMIT-02 — Реплика лимита пишется подписчиком lectures.venue_limit_changed

`draft` · effect

on_venue_limit_changed вызывает apply_venue_limit. Если реплики для площадки нет, она создаётся, и мероприятия не трогаются. Если лимит не изменился, ничего не происходит. Иначе обновляются max_capacity и updated_at. Строка реплики блокируется FOR UPDATE.

- Реализация: [`services/lectures/consumers.py::on_venue_limit_changed:16-17`](../../services/lectures/consumers.py#L16), [`services/lectures/service.py::apply_venue_limit:89-99`](../../services/lectures/service.py#L89)
- БД: `venue_capacity_limits_max_capacity_check`
- Тесты: `tests/test_lectures_events.py::test_limit_change_updates_replica_and_untouched_events`
- Роли: Система (события и фоновые задачи)
- Связанные: R-LECTURES-LIMIT-01, R-LECTURES-LIMIT-03

## R-LECTURES-LIMIT-03 — Число мест будущих мероприятий без ручной настройки следует за лимитом

`draft` · effect

При смене лимита apply_venue_limit приравнивает число мест к новому лимиту только у мероприятий этой площадки, которые запланированы (scheduled), ещё не начались, у которых число мест равнялось старому лимиту и capacity_manual = false. Прошедшие, отменённые и настроенные вручную мероприятия не меняются, даже если их число мест совпадало со старым лимитом.

- Реализация: [`services/lectures/service.py::apply_venue_limit:101-116`](../../services/lectures/service.py#L101)
- Тесты: `tests/test_lectures_events.py::test_limit_change_updates_replica_and_untouched_events`, `tests/test_lectures_events.py::test_limit_change_skips_past_and_cancelled_events`, `tests/test_lectures_events.py::test_manual_capacity_kept_even_when_it_matches_old_limit`, `tests/test_lectures_events.py::test_restoring_full_capacity_follows_limit_again`
- Роли: Система (события и фоновые задачи)
- Связанные: R-LECTURES-EVENT-04, R-LECTURES-CAPACITY-02, R-LECTURES-LIMIT-05

## R-LECTURES-LIMIT-04 — Рост лимита площадки отдаёт новые места листу ожидания

`draft` · effect

Если новый лимит больше старого, apply_venue_limit публикует lectures.capacity_increased для каждого мероприятия, где число мест подтянулось к лимиту. Подписчик on_capacity_increased продвигает слушателей из листа ожидания.

- Реализация: [`services/lectures/service.py::apply_venue_limit:114-118`](../../services/lectures/service.py#L114), [`services/lectures/consumers.py::on_capacity_increased:21-22`](../../services/lectures/consumers.py#L21)
- Тесты: `tests/test_lectures_events.py::test_limit_increase_gives_new_seats_to_waitlist`
- Роли: Система (события и фоновые задачи)
- Связанные: R-LECTURES-CAPACITY-03, R-LECTURES-WAITLIST-06

## R-LECTURES-LIMIT-05 — Снижение лимита не проверяет регистрации и ручные мероприятия

`draft` · effect

Когда лимит снижается, мероприятия, которые следуют за лимитом, получают меньше мест без сверки с числом подтверждённых регистраций и без отмены лишних, то есть может возникнуть перебор. Мероприятия с ручным числом мест, превышающим новый лимит, не меняются и остаются выше лимита: триггер trg_lecture_capacity_limit срабатывает только при UPDATE полей capacity и venue_id. В списке будущих мероприятий (upcoming) число свободных мест при переборе показывается как 0.

- Реализация: [`services/lectures/service.py::apply_venue_limit:101-116`](../../services/lectures/service.py#L101), [`services/lectures/service.py::upcoming:254-262`](../../services/lectures/service.py#L254)
- БД: `trg_lecture_capacity_limit`
- Роли: Система (события и фоновые задачи)
- Связанные: R-LECTURES-LIMIT-03, R-LECTURES-CAPACITY-01, R-LECTURES-EVENT-05

## R-LECTURES-MOVE-01 — Переносят только на другую свободную площадку

`draft` · guard

move_event отклоняет перенос на ту же площадку («мероприятие уже проходит на этой площадке»), на площадку без лимита и на площадку, где в это же время уже запланировано другое мероприятие. Время начала при переносе не меняется, срок MIN_LEAD_TIME не проверяется.

- Реализация: [`services/lectures/service.py::move_event:203-215`](../../services/lectures/service.py#L203)
- БД: `events_venue_slot_uq`
- Тесты: `tests/test_lectures_registrations.py::test_move_to_other_venue_cancels_registrations_and_notifies`
- Связанные: R-LECTURES-EVENT-07, R-LECTURES-MANAGE-01, R-LECTURES-MOVE-02

## R-LECTURES-MOVE-02 — Перенос аннулирует все регистрации и лист ожидания

`draft` · effect

При переносе _drop_audience отменяет все подтверждённые регистрации (cancel_reason = venue_changed, на каждую публикуется lectures.registration_cancelled) и переводит записи листа ожидания в cancelled. После этого мероприятие получает новую площадку, число мест (указанное или лимит новой площадки) и пересчитанный capacity_manual. Публикуется lectures.event_moved со списком слушателей из листа ожидания. Освобождённые места листу ожидания не отдаются: venue_changed не входит в SEAT_RELEASING_REASONS, и площадка в событии старая.

- Реализация: [`services/lectures/service.py::move_event:217-233`](../../services/lectures/service.py#L217), [`services/lectures/service.py::_drop_audience:180-196`](../../services/lectures/service.py#L180), [`services/lectures/consumers.py::on_registration_cancelled:56-62`](../../services/lectures/consumers.py#L56)
- Настройки: `services/lectures/service.py::SEAT_RELEASING_REASONS`
- Тесты: `tests/test_lectures_registrations.py::test_move_to_other_venue_cancels_registrations_and_notifies`, `tests/test_lectures_registrations.py::test_new_registrations_after_move_go_to_new_venue`, `tests/test_lectures_registrations.py::test_move_capacity_above_new_limit_rejected`
- Связанные: R-LECTURES-SEAT-01, R-LECTURES-NOTIFY-02, R-LECTURES-NOTIFY-03

## R-LECTURES-CANCEL-01 — Отмена мероприятия аннулирует регистрации и лист ожидания

`draft` · effect

cancel_event переводит мероприятие в cancelled, отменяет все подтверждённые регистрации (cancel_reason = event_cancelled), закрывает лист ожидания (cancelled) и публикует lectures.event_cancelled со списком слушателей из листа. После этого регистрация закрыта, а места листу ожидания не отдаются.

- Реализация: [`services/lectures/service.py::cancel_event:237-243`](../../services/lectures/service.py#L237), [`services/lectures/service.py::_drop_audience:180-196`](../../services/lectures/service.py#L180)
- Тесты: `tests/test_lectures_registrations.py::test_cancel_event_notifies_registered_and_waitlisted`, `tests/test_lectures_events.py::test_limit_change_skips_past_and_cancelled_events`
- Связанные: R-LECTURES-MANAGE-01, R-LECTURES-NOTIFY-02, R-LECTURES-NOTIFY-03

## R-LECTURES-REG-01 — Регистрация и лист ожидания закрываются за REGISTRATION_CLOSES_BEFORE до начала

`draft` · guard

Записаться или встать в лист ожидания можно, только пока мероприятие в статусе scheduled и до начала больше settings.REGISTRATION_CLOSES_BEFORE (1 час). Иначе возвращается «регистрация на мероприятие закрыта». По тому же условию fill_from_waitlist перестаёт продвигать лист ожидания.

- Реализация: [`services/lectures/service.py::_registration_open:50-51`](../../services/lectures/service.py#L50), [`services/lectures/service.py::register:294-295`](../../services/lectures/service.py#L294), [`services/lectures/service.py::join_waitlist:389-390`](../../services/lectures/service.py#L389)
- Настройки: `services/lectures/settings.py::REGISTRATION_CLOSES_BEFORE`
- Тесты: `tests/test_lectures_registrations.py::test_registration_closes_an_hour_before_start`, `tests/test_lectures_registrations.py::test_cancel_event_notifies_registered_and_waitlisted`
- Связанные: R-LECTURES-WAITLIST-06, R-LECTURES-WAITLIST-07

## R-LECTURES-REG-02 — Одна действующая регистрация слушателя на мероприятие

`draft` · invariant

Если у слушателя уже есть подтверждённая регистрация на это мероприятие, register и join_waitlist отклоняют запрос: «слушатель уже зарегистрирован на это мероприятие». В БД то же правило задаёт частичный уникальный индекс registrations_active_uq (event_id, listener_id) WHERE status = 'confirmed'. Повторная регистрация после отмены разрешена.

- Реализация: [`services/lectures/service.py::register:296-297`](../../services/lectures/service.py#L296), [`services/lectures/service.py::join_waitlist:391-392`](../../services/lectures/service.py#L391), [`services/lectures/service.py::_registered:282-289`](../../services/lectures/service.py#L282)
- БД: `registrations_active_uq`
- Тесты: `tests/test_lectures_registrations.py::test_new_registrations_after_move_go_to_new_venue`

## R-LECTURES-REG-03 — У слушателя не больше MAX_ACTIVE_REGISTRATIONS регистраций на будущие мероприятия

`draft` · guard

register отклоняет запись, если у слушателя уже settings.MAX_ACTIVE_REGISTRATIONS (3) подтверждённых регистраций на запланированные мероприятия, которые ещё не начались. Продвижение из листа ожидания (fill_from_waitlist) этот лимит не проверяет, поэтому через лист ожидания его можно превысить.

- Реализация: [`services/lectures/service.py::register:298-299`](../../services/lectures/service.py#L298), [`services/lectures/service.py::_active_registrations:268-279`](../../services/lectures/service.py#L268)
- Настройки: `services/lectures/settings.py::MAX_ACTIVE_REGISTRATIONS`
- Тесты: `tests/test_lectures_registrations.py::test_listener_limit_on_active_registrations`
- Связанные: R-LECTURES-WAITLIST-06

## R-LECTURES-REG-04 — Без свободных мест регистрация отклоняется с предложением листа ожидания

`draft` · guard

Если подтверждённых регистраций столько же, сколько мест, или больше, register отклоняет запись: «свободных мест нет, можно встать в лист ожидания». Строка мероприятия при этом блокируется FOR UPDATE.

- Реализация: [`services/lectures/service.py::register:293-301`](../../services/lectures/service.py#L293)
- БД: `trg_registration_seat`
- Тесты: `tests/test_lectures_registrations.py::test_full_event_sends_to_waitlist`
- Связанные: R-LECTURES-REG-05, R-LECTURES-WAITLIST-01

## R-LECTURES-REG-05 — БД не допускает перебора мест и регистраций на незапланированное мероприятие

`draft` · invariant

Триггер trg_registration_seat (функция check_seat_available) срабатывает на INSERT и на UPDATE статуса регистрации в confirmed. Он блокирует строку мероприятия, отклоняет регистрацию, если мероприятие не в статусе scheduled, и если подтверждённых регистраций уже не меньше числа мест. Это страхует любые пути записи, включая продвижение из листа ожидания.

- БД: `trg_registration_seat`, `check_seat_available`
- Тесты: `tests/test_lectures_registrations.py::test_database_refuses_overbooking`
- Связанные: R-LECTURES-REG-04

## R-LECTURES-REG-06 — Прямая регистрация закрывает свою запись в листе ожидания

`draft` · effect

Если слушатель записался напрямую, его запись waiting в листе ожидания этого мероприятия переводится в left. Очередь при прямой записи не проверяется: пока событие seat_released не обработано, освободившееся место может занять любой слушатель, а не первый в листе ожидания.

- Реализация: [`services/lectures/service.py::register:303-316`](../../services/lectures/service.py#L303)
- Связанные: R-LECTURES-SEAT-01, R-LECTURES-WAITLIST-06

## R-LECTURES-REG-07 — Согласованность статуса регистрации и меток времени

`draft` · invariant

CHECK-ограничения lectures.registrations: статус cancelled тогда и только тогда, когда заполнено cancelled_at (registrations_check), attended — тогда и только тогда, когда заполнено attended_at (registrations_check1). Статус только confirmed, attended или cancelled, источник — direct или waitlist. Код никогда не ставит attended: после завершения мероприятия регистрации остаются confirmed.

- Реализация: [`services/lectures/service.py::_cancel:321-323`](../../services/lectures/service.py#L321)
- БД: `registrations_check`, `registrations_check1`, `registrations_status_check`, `registrations_source_check`
- Связанные: R-LECTURES-FINISH-01

## R-LECTURES-CANCEL-REG-01 — Регистрацию отменяет только сам слушатель и только до начала

`draft` · permission

cancel_registration разрешён только владельцу регистрации. Для остальных — AccessDenied «отменить регистрацию может только сам слушатель». Регистрация должна быть confirmed, а мероприятие ещё не начаться. Отменить можно и в последний час, когда регистрация уже закрыта, но тогда освободившееся место листу ожидания не отдаётся. cancel_reason = listener.

- Реализация: [`services/lectures/service.py::cancel_registration:341-349`](../../services/lectures/service.py#L341), [`services/lectures/service.py::_cancel:320-334`](../../services/lectures/service.py#L320)
- Тесты: `tests/test_lectures_registrations.py::test_only_listener_cancels_own_registration`, `tests/test_lectures_registrations.py::test_cancellation_gives_seat_to_first_in_waitlist`
- Связанные: R-LECTURES-SEAT-01, R-LECTURES-REG-01

## R-LECTURES-CANCEL-REG-02 — Организатор может снять слушателя с мероприятия (API нет)

`draft` · permission

remove_listener отменяет подтверждённую регистрацию (cancel_reason = organizer), если вызывающий — организатор запланированного мероприятия. Для недействующей регистрации возвращается «регистрация не действует». Освободившееся место уходит листу ожидания. HTTP-маршрута у функции нет, она вызывается только из кода и тестов.

- Реализация: [`services/lectures/service.py::remove_listener:353-359`](../../services/lectures/service.py#L353)
- Тесты: `tests/test_lectures_registrations.py::test_left_waitlist_entry_is_skipped`, `tests/test_lectures_registrations.py::test_only_listener_cancels_own_registration`
- Связанные: R-LECTURES-MANAGE-01, R-LECTURES-SEAT-01

## R-LECTURES-SEAT-01 — Место освобождается только при отмене слушателем или организатором

`draft` · effect

on_registration_cancelled публикует lectures.seat_released, только если причина отмены входит в SEAT_RELEASING_REASONS (listener, organizer), мероприятие всё ещё scheduled и его площадка совпадает с площадкой из события. on_seat_released вызывает fill_from_waitlist. При переносе и отмене мероприятия места не освобождаются.

- Реализация: [`services/lectures/consumers.py::on_registration_cancelled:56-62`](../../services/lectures/consumers.py#L56), [`services/lectures/consumers.py::on_seat_released:66-67`](../../services/lectures/consumers.py#L66)
- Настройки: `services/lectures/service.py::SEAT_RELEASING_REASONS`
- Тесты: `tests/test_lectures_registrations.py::test_cancellation_gives_seat_to_first_in_waitlist`, `tests/test_lectures_registrations.py::test_left_waitlist_entry_is_skipped`
- Роли: Система (события и фоновые задачи)
- Связанные: R-LECTURES-WAITLIST-06, R-LECTURES-MOVE-02

## R-LECTURES-WAITLIST-01 — В лист ожидания встают только когда мест нет

`draft` · guard

join_waitlist отклоняет запрос, если на мероприятии ещё есть свободные места: «на мероприятии есть свободные места, регистрируйтесь напрямую». Кроме того, регистрация должна быть открыта, а слушатель — не зарегистрирован.

- Реализация: [`services/lectures/service.py::join_waitlist:393-394`](../../services/lectures/service.py#L393)
- Тесты: `tests/test_lectures_registrations.py::test_full_event_sends_to_waitlist`
- Связанные: R-LECTURES-REG-04, R-LECTURES-REG-01

## R-LECTURES-WAITLIST-02 — Одна ожидающая запись слушателя на мероприятие

`draft` · invariant

Если слушатель уже в листе ожидания этого мероприятия, join_waitlist отклоняет повторную запись: «слушатель уже в листе ожидания». В БД то же правило задаёт частичный уникальный индекс waitlist_waiting_uq (event_id, listener_id) WHERE status = 'waiting'.

- Реализация: [`services/lectures/service.py::join_waitlist:395-396`](../../services/lectures/service.py#L395)
- БД: `waitlist_waiting_uq`

## R-LECTURES-WAITLIST-03 — Длина листа ожидания ограничена WAITLIST_MAX_SIZE

`draft` · guard

Если в листе ожидания мероприятия уже settings.WAITLIST_MAX_SIZE (20) записей в статусе waiting, join_waitlist отклоняет новую: «лист ожидания заполнен». В БД такого ограничения нет.

- Реализация: [`services/lectures/service.py::join_waitlist:397-401`](../../services/lectures/service.py#L397)
- Настройки: `services/lectures/settings.py::WAITLIST_MAX_SIZE`

## R-LECTURES-WAITLIST-04 — Лист ожидания — очередь по времени записи

`draft` · calculation

Позиция в листе ожидания считается как число записей waiting, созданных раньше (при одинаковом времени — с меньшим id), плюс один. В том же порядке (created_at, id) fill_from_waitlist выдаёт места. Позицию можно узнать только у записи в статусе waiting.

- Реализация: [`services/lectures/service.py::waitlist_position:421-433`](../../services/lectures/service.py#L421), [`services/lectures/service.py::_waiting:365-374`](../../services/lectures/service.py#L365)
- БД: `waitlist_queue_idx`
- Тесты: `tests/test_lectures_registrations.py::test_full_event_sends_to_waitlist`, `tests/test_lectures_registrations.py::test_cancellation_gives_seat_to_first_in_waitlist`
- Связанные: R-LECTURES-WAITLIST-06

## R-LECTURES-WAITLIST-05 — Покинуть лист ожидания может только сам слушатель

`draft` · permission

leave_waitlist разрешён только владельцу записи. Для остальных — AccessDenied «покинуть лист ожидания может только сам слушатель». Запись должна быть в статусе waiting. Она переводится в left и при выдаче мест пропускается.

- Реализация: [`services/lectures/service.py::leave_waitlist:412-418`](../../services/lectures/service.py#L412)
- Тесты: `tests/test_lectures_registrations.py::test_left_waitlist_entry_is_skipped`
- Связанные: R-LECTURES-WAITLIST-06

## R-LECTURES-WAITLIST-06 — Свободные места автоматически получают первые в листе ожидания

`draft` · effect

fill_from_waitlist (вызывается по lectures.seat_released и lectures.capacity_increased) работает, только пока регистрация открыта. Каждой из первых N записей waiting (N — число свободных мест) ставится статус promoted, создаётся подтверждённая регистрация с source = waitlist и публикуется lectures.waitlist_promoted. Лимит MAX_ACTIVE_REGISTRATIONS для продвигаемого слушателя не проверяется. Записи, заблокированные другой транзакцией, пропускаются (skip_locked).

- Реализация: [`services/lectures/service.py::fill_from_waitlist:436-469`](../../services/lectures/service.py#L436), [`services/lectures/consumers.py::on_seat_released:66-67`](../../services/lectures/consumers.py#L66), [`services/lectures/consumers.py::on_capacity_increased:21-22`](../../services/lectures/consumers.py#L21)
- БД: `trg_registration_seat`
- Настройки: `services/lectures/settings.py::REGISTRATION_CLOSES_BEFORE`
- Тесты: `tests/test_lectures_registrations.py::test_cancellation_gives_seat_to_first_in_waitlist`, `tests/test_lectures_registrations.py::test_organizer_adds_seats_for_waitlist`, `tests/test_lectures_registrations.py::test_left_waitlist_entry_is_skipped`, `tests/test_lectures_events.py::test_limit_increase_gives_new_seats_to_waitlist`
- Роли: Система (события и фоновые задачи)
- Связанные: R-LECTURES-SEAT-01, R-LECTURES-CAPACITY-03, R-LECTURES-LIMIT-04, R-LECTURES-REG-03

## R-LECTURES-WAITLIST-07 — Лист ожидания истекает, когда закрывается регистрация

`draft` · timer

Фоновая задача close_waitlists переводит в expired все записи waiting у мероприятий, до начала которых осталось не больше REGISTRATION_CLOSES_BEFORE (1 час), и публикует lectures.waitlist_expired. on_waitlist_expired ставит уведомление waitlist_expired. Статус мероприятия задача не проверяет. Регистрация задачи в планировщике в репозитории не найдена: задачу вызывают только тесты.

- Реализация: [`services/lectures/jobs.py::close_waitlists:11-33`](../../services/lectures/jobs.py#L11), [`services/lectures/consumers.py::on_waitlist_expired:113-122`](../../services/lectures/consumers.py#L113)
- Настройки: `services/lectures/settings.py::REGISTRATION_CLOSES_BEFORE`
- Тесты: `tests/test_lectures_jobs.py::test_waitlist_expires_when_registration_closes`
- Роли: Система (события и фоновые задачи)
- Связанные: R-LECTURES-REG-01

## R-LECTURES-WAITLIST-08 — Закрытая запись листа ожидания всегда имеет closed_at

`draft` · invariant

CHECK waitlist_check: статус waiting тогда и только тогда, когда closed_at пуст. Допустимые статусы (waitlist_status_check): waiting, promoted, left, cancelled, expired. Код ставит closed_at при каждом закрытии записи: продвижение, уход, прямая регистрация, перенос или отмена мероприятия, истечение.

- Реализация: [`services/lectures/service.py::_drop_audience:193-195`](../../services/lectures/service.py#L193), [`services/lectures/service.py::leave_waitlist:416-417`](../../services/lectures/service.py#L416)
- БД: `waitlist_check`, `waitlist_status_check`

## R-LECTURES-REMIND-01 — Напоминание о мероприятии — один раз за REMINDER_AHEAD до начала

`draft` · timer

Фоновая задача send_reminders ставит уведомление reminder каждой подтверждённой регистрации на запланированное мероприятие, которое начнётся в течение settings.REMINDER_AHEAD (24 часа). Ключ дедупликации reminder:<registration_id> гарантирует одно напоминание на регистрацию при любом числе запусков. Регистрация задачи в планировщике в репозитории не найдена.

- Реализация: [`services/lectures/jobs.py::send_reminders:36-59`](../../services/lectures/jobs.py#L36)
- БД: `notifications_dedup_key_key`
- Настройки: `services/lectures/settings.py::REMINDER_AHEAD`
- Тесты: `tests/test_lectures_jobs.py::test_reminder_sent_once_a_day_ahead`
- Роли: Система (события и фоновые задачи)
- Связанные: R-LECTURES-NOTIFY-01

## R-LECTURES-FINISH-01 — Мероприятие становится прошедшим через FINISH_AFTER после начала

`draft` · timer

Фоновая задача finish_past_events переводит в finished мероприятия scheduled, начавшиеся settings.FINISH_AFTER (3 часа) назад или раньше. До этого мероприятие остаётся scheduled, и организатор может им управлять. Регистрации не переводятся в attended. Регистрация задачи в планировщике в репозитории не найдена.

- Реализация: [`services/lectures/jobs.py::finish_past_events:62-73`](../../services/lectures/jobs.py#L62)
- БД: `events_status_check`
- Настройки: `services/lectures/settings.py::FINISH_AFTER`
- Тесты: `tests/test_lectures_jobs.py::test_past_events_finished`
- Роли: Система (события и фоновые задачи)
- Связанные: R-LECTURES-EVENT-08, R-LECTURES-MANAGE-01, R-LECTURES-REG-07

## R-LECTURES-NOTIFY-01 — Повторная доставка события не дублирует уведомление

`draft` · invariant

notify вставляет уведомление с ON CONFLICT (dedup_key) DO NOTHING, опираясь на уникальное ограничение notifications_dedup_key_key. Ключ строится из типа и id регистрации или записи листа ожидания. Уведомления только записываются в lectures.notifications и отдаются через GET /listeners/{id}/notifications: sent_at код никогда не заполняет, отправки нет. Допустимые типы задаёт notifications_kind_check.

- Реализация: [`services/lectures/service.py::notify:54-69`](../../services/lectures/service.py#L54), [`services/lectures/consumers.py::on_registration_created:26-35`](../../services/lectures/consumers.py#L26)
- БД: `notifications_dedup_key_key`, `notifications_kind_check`
- Тесты: `tests/test_lectures_registrations.py::test_redelivered_event_does_not_duplicate_notice`, `tests/test_lectures_registrations.py::test_registration_confirmed_with_notice`
- Роли: Система (события и фоновые задачи)

## R-LECTURES-NOTIFY-02 — Тип уведомления об отмене регистрации зависит от причины

`draft` · effect

on_registration_cancelled выбирает тип уведомления по причине: venue_changed — event_moved («перенесено на другую площадку, регистрация отменена»), event_cancelled — event_cancelled, остальные причины (listener, organizer) — registration_cancelled. Ключ дедупликации — cancelled:<registration_id>.

- Реализация: [`services/lectures/consumers.py::on_registration_cancelled:39-55`](../../services/lectures/consumers.py#L39)
- БД: `notifications_kind_check`
- Тесты: `tests/test_lectures_registrations.py::test_cancellation_gives_seat_to_first_in_waitlist`, `tests/test_lectures_registrations.py::test_move_to_other_venue_cancels_registrations_and_notifies`, `tests/test_lectures_registrations.py::test_cancel_event_notifies_registered_and_waitlisted`
- Роли: Система (события и фоновые задачи)
- Связанные: R-LECTURES-MOVE-02, R-LECTURES-CANCEL-01

## R-LECTURES-NOTIFY-03 — Слушатели из листа ожидания получают уведомление о переносе или отмене

`draft` · effect

on_event_moved и on_event_cancelled уведомляют каждого слушателя из payload.waitlisted (тип event_moved или event_cancelled). Ключ дедупликации <kind>:waitlist:<event_id>:<listener_id> не зависит от конкретного переноса. Если слушатель снова встанет в лист ожидания и мероприятие перенесут ещё раз, второе уведомление о переносе не создастся.

- Реализация: [`services/lectures/consumers.py::on_event_moved:96-103`](../../services/lectures/consumers.py#L96), [`services/lectures/consumers.py::on_event_cancelled:107-109`](../../services/lectures/consumers.py#L107), [`services/lectures/consumers.py::_notify_waitlisted:83-92`](../../services/lectures/consumers.py#L83)
- БД: `notifications_dedup_key_key`
- Тесты: `tests/test_lectures_registrations.py::test_move_to_other_venue_cancels_registrations_and_notifies`, `tests/test_lectures_registrations.py::test_cancel_event_notifies_registered_and_waitlisted`
- Роли: Система (события и фоновые задачи)
- Связанные: R-LECTURES-MOVE-02, R-LECTURES-CANCEL-01

## R-LECTURES-NOTIFY-04 — Продвижение из листа ожидания сопровождается уведомлением

`draft` · effect

on_waitlist_promoted ставит слушателю уведомление waitlist_promoted («Освободилось место: вы зарегистрированы…») с ключом promoted:<registration_id>. Отдельного уведомления registered при продвижении нет: lectures.registration_created публикует только register.

- Реализация: [`services/lectures/consumers.py::on_waitlist_promoted:71-80`](../../services/lectures/consumers.py#L71)
- БД: `notifications_dedup_key_key`
- Тесты: `tests/test_lectures_registrations.py::test_cancellation_gives_seat_to_first_in_waitlist`
- Роли: Система (события и фоновые задачи)
- Связанные: R-LECTURES-WAITLIST-06

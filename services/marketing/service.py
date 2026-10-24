"""Аудитории, шаблоны писем, кампании рассылок и отписки."""

from datetime import datetime, timedelta
from string import Template as Text

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from libs import clock, events
from libs.errors import AccessDenied, DomainError, NotFound
from services.marketing import settings
from services.marketing.models import (
    Audience,
    AudienceMember,
    Campaign,
    CampaignTemplate,
    Manager,
    SentMessage,
    Unsubscription,
)

NOT_STARTED = ("draft", "scheduled")
RUNNING = ("preparing", "sending")
UNSUBSCRIBE_REASONS = ("reader", "bounce", "complaint", "operator")


def normalize_email(email: str) -> str:
    email = email.strip().lower()
    if "@" not in email[1:]:
        raise DomainError(f"некорректный адрес: {email!r}")
    return email


def render(body: str, context: dict[str, str]) -> str:
    return Text(body).safe_substitute(context)


# Менеджеры ------------------------------------------------------------------


async def add_manager(
    session: AsyncSession, *, manager_id: int, venue_id: int | None, full_name: str
) -> Manager:
    manager = Manager(manager_id=manager_id, venue_id=venue_id, full_name=full_name)
    session.add(manager)
    await session.flush()
    return manager


async def _require_manager(session: AsyncSession, manager_id: int, venue_id: int | None) -> None:
    scope = Manager.venue_id.is_(None)
    if venue_id is not None:
        scope = or_(scope, Manager.venue_id == venue_id)
    found = await session.scalar(select(Manager.id).where(Manager.manager_id == manager_id, scope).limit(1))
    if found is None:
        if venue_id is None:
            raise AccessDenied("шаблоны сети задаёт только менеджер сети")
        raise AccessDenied("менеджер не ведёт рассылки этой площадки")


# Аудитории ------------------------------------------------------------------


async def create_audience(session: AsyncSession, *, manager_id: int, venue_id: int, name: str) -> Audience:
    await _require_manager(session, manager_id, venue_id)
    name = name.strip()
    if not name:
        raise DomainError("у аудитории должно быть название")
    taken = await session.scalar(
        select(Audience.id).where(Audience.venue_id == venue_id, Audience.name == name)
    )
    if taken is not None:
        raise DomainError(f"на площадке уже есть аудитория «{name}»")
    audience = Audience(venue_id=venue_id, name=name, created_by=manager_id, created_at=clock.now())
    session.add(audience)
    await session.flush()
    return audience


async def _audience(session: AsyncSession, audience_id: int) -> Audience:
    audience = await session.get(Audience, audience_id)
    if audience is None:
        raise NotFound(f"аудитория {audience_id}")
    return audience


async def archive_audience(session: AsyncSession, audience_id: int, manager_id: int) -> Audience:
    audience = await _audience(session, audience_id)
    await _require_manager(session, manager_id, audience.venue_id)
    pending = await session.scalar(
        select(func.count()).where(
            Campaign.audience_id == audience_id, Campaign.status.in_(("scheduled", *RUNNING))
        )
    )
    if pending:
        raise DomainError("по аудитории есть незавершённые кампании")
    audience.archived = True
    return audience


async def is_unsubscribed(session: AsyncSession, email: str, venue_id: int) -> bool:
    found = await session.scalar(
        select(Unsubscription.id)
        .where(
            Unsubscription.email == email,
            or_(Unsubscription.venue_id.is_(None), Unsubscription.venue_id == venue_id),
        )
        .limit(1)
    )
    return found is not None


async def add_member(
    session: AsyncSession,
    audience_id: int,
    manager_id: int,
    *,
    email: str,
    full_name: str,
    segment: str,
) -> AudienceMember:
    audience = await _audience(session, audience_id)
    await _require_manager(session, manager_id, audience.venue_id)
    if audience.archived:
        raise DomainError("аудитория в архиве")
    if segment not in settings.AUDIENCE_GROUP:
        raise DomainError(f"неизвестный сегмент читателя: {segment}")
    email = normalize_email(email)
    size = await session.scalar(select(func.count()).where(AudienceMember.audience_id == audience_id))
    if size >= settings.MAX_AUDIENCE_SIZE:
        raise DomainError(f"в аудитории не может быть больше {settings.MAX_AUDIENCE_SIZE} адресов")
    duplicate = await session.scalar(
        select(AudienceMember.id).where(
            AudienceMember.audience_id == audience_id, AudienceMember.email == email
        )
    )
    if duplicate is not None:
        raise DomainError("адрес уже есть в аудитории")
    if await is_unsubscribed(session, email, audience.venue_id):
        raise DomainError("адрес отписан от рассылок площадки")
    member = AudienceMember(
        audience_id=audience_id,
        email=email,
        full_name=full_name.strip(),
        segment=segment,
        added_at=clock.now(),
    )
    session.add(member)
    await session.flush()
    return member


# Шаблоны --------------------------------------------------------------------


async def set_template(
    session: AsyncSession,
    *,
    manager_id: int,
    venue_id: int | None,
    audience_group: str,
    type_: str,
    body: str,
) -> CampaignTemplate:
    await _require_manager(session, manager_id, venue_id)
    if audience_group not in set(settings.AUDIENCE_GROUP.values()):
        raise DomainError(f"неизвестная группа аудитории: {audience_group}")
    if type_ not in settings.CAMPAIGN_TYPES:
        raise DomainError(f"неизвестный тип кампании: {type_}")
    if not body.strip():
        raise DomainError("текст шаблона пуст")
    if len(body) > settings.MAX_TEMPLATE_LENGTH:
        raise DomainError(f"текст шаблона длиннее {settings.MAX_TEMPLATE_LENGTH} символов")

    venue = CampaignTemplate.venue_id.is_(None) if venue_id is None else CampaignTemplate.venue_id == venue_id
    tpl = await session.scalar(
        select(CampaignTemplate).where(
            venue, CampaignTemplate.audience_group == audience_group, CampaignTemplate.type == type_
        )
    )
    if tpl is None:
        tpl = CampaignTemplate(venue_id=venue_id, audience_group=audience_group, type=type_, body=body)
        session.add(tpl)
    tpl.body = body
    tpl.updated_at = clock.now()
    await session.flush()
    return tpl


async def find_template(
    session: AsyncSession, venue_id: int, segment: str, type_: str
) -> CampaignTemplate | None:
    """Шаблон площадки для группы читателя, иначе шаблон сети; затем то же для запасной группы."""
    group = settings.AUDIENCE_GROUP.get(segment, settings.FALLBACK_GROUP)
    groups = [group] if group == settings.FALLBACK_GROUP else [group, settings.FALLBACK_GROUP]
    candidates = (
        await session.scalars(
            select(CampaignTemplate).where(
                CampaignTemplate.type == type_,
                CampaignTemplate.audience_group.in_(groups),
                or_(CampaignTemplate.venue_id == venue_id, CampaignTemplate.venue_id.is_(None)),
            )
        )
    ).all()
    by_key = {(t.audience_group, t.venue_id): t for t in candidates}
    for g in groups:
        for v in (venue_id, None):
            if (g, v) in by_key:
                return by_key[g, v]
    return None


# Кампании -------------------------------------------------------------------


def _check_schedule(scheduled_at: datetime) -> None:
    now = clock.now()
    if scheduled_at <= now:
        raise DomainError("нельзя запланировать кампанию на прошедшее время")
    if scheduled_at - now > timedelta(days=settings.MAX_SCHEDULE_AHEAD_DAYS):
        raise DomainError(
            f"кампанию можно запланировать не дальше чем на {settings.MAX_SCHEDULE_AHEAD_DAYS} дней"
        )


async def create_campaign(
    session: AsyncSession,
    *,
    manager_id: int,
    audience_id: int,
    type_: str,
    subject: str,
    scheduled_at: datetime | None = None,
) -> Campaign:
    audience = await _audience(session, audience_id)
    await _require_manager(session, manager_id, audience.venue_id)
    if audience.archived:
        raise DomainError("аудитория в архиве")
    if type_ not in settings.CAMPAIGN_TYPES:
        raise DomainError(f"неизвестный тип кампании: {type_}")
    subject = subject.strip()
    if not subject:
        raise DomainError("у кампании должна быть тема письма")
    if scheduled_at is not None:
        _check_schedule(scheduled_at)
    campaign = Campaign(
        venue_id=audience.venue_id,
        audience_id=audience_id,
        type=type_,
        subject=subject,
        status="scheduled" if scheduled_at else "draft",
        created_by=manager_id,
        created_at=clock.now(),
        scheduled_at=scheduled_at,
    )
    session.add(campaign)
    await session.flush()
    return campaign


async def _campaign_for(session: AsyncSession, campaign_id: int, manager_id: int) -> Campaign:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        raise NotFound(f"кампания {campaign_id}")
    await _require_manager(session, manager_id, campaign.venue_id)
    return campaign


async def schedule_campaign(
    session: AsyncSession, campaign_id: int, manager_id: int, scheduled_at: datetime
) -> Campaign:
    campaign = await _campaign_for(session, campaign_id, manager_id)
    if campaign.status not in NOT_STARTED:
        raise DomainError("перенести можно только кампанию, которая ещё не запущена")
    _check_schedule(scheduled_at)
    campaign.status = "scheduled"
    campaign.scheduled_at = scheduled_at
    return campaign


async def cancel_campaign(session: AsyncSession, campaign_id: int, manager_id: int) -> Campaign:
    campaign = await _campaign_for(session, campaign_id, manager_id)
    if campaign.status not in NOT_STARTED:
        raise DomainError("отменить можно только кампанию, которая ещё не запущена")
    campaign.status = "cancelled"
    return campaign


async def launch_campaign(session: AsyncSession, campaign_id: int, manager_id: int) -> Campaign:
    campaign = await _campaign_for(session, campaign_id, manager_id)
    await start(session, campaign, clock.now())
    return campaign


async def start(session: AsyncSession, campaign: Campaign, now: datetime) -> None:
    if campaign.status not in NOT_STARTED:
        raise DomainError("кампания уже запущена или закрыта")
    audience = await _audience(session, campaign.audience_id)
    if audience.archived:
        raise DomainError("аудитория в архиве")
    running = await session.scalar(
        select(Campaign.id).where(
            Campaign.audience_id == audience.id, Campaign.status.in_(RUNNING), Campaign.id != campaign.id
        )
    )
    if running is not None:
        raise DomainError("по аудитории уже идёт другая кампания")
    pause = timedelta(days=settings.MIN_DAYS_BETWEEN_CAMPAIGNS)
    if audience.last_campaign_at is not None and now - audience.last_campaign_at < pause:
        raise DomainError(
            f"аудитории уже писали меньше {settings.MIN_DAYS_BETWEEN_CAMPAIGNS} дней назад"
        )
    reachable = await session.scalar(
        select(func.count()).where(
            AudienceMember.audience_id == audience.id, AudienceMember.opted_out.is_(False)
        )
    )
    if not reachable:
        raise DomainError("в аудитории нет адресов для рассылки")

    campaign.status = "preparing"
    campaign.launched_at = now
    events.publish(
        session,
        "marketing.campaign_launched",
        {"campaign_id": campaign.id, "venue_id": campaign.venue_id, "audience_id": audience.id},
    )


async def prepare_messages(session: AsyncSession, campaign_id: int) -> None:
    """Раскладывает кампанию на письма адресатам: текст по шаблону или пропуск с причиной."""
    campaign = await session.get(Campaign, campaign_id, with_for_update=True)
    if campaign is None or campaign.status != "preparing":
        return
    members = (
        await session.scalars(
            select(AudienceMember)
            .where(AudienceMember.audience_id == campaign.audience_id, AudienceMember.opted_out.is_(False))
            .order_by(AudienceMember.id)
        )
    ).all()
    unsubscribed = set(
        (
            await session.scalars(
                select(Unsubscription.email).where(
                    Unsubscription.email.in_([m.email for m in members]),
                    or_(Unsubscription.venue_id.is_(None), Unsubscription.venue_id == campaign.venue_id),
                )
            )
        ).all()
    )

    now = clock.now()
    templates: dict[str, CampaignTemplate | None] = {}
    queued = 0
    for m in members:
        msg = SentMessage(campaign_id=campaign.id, email=m.email, segment=m.segment, body="", created_at=now)
        if m.email in unsubscribed:
            msg.status, msg.skip_reason = "skipped", "unsubscribed"
        else:
            if m.segment not in templates:
                templates[m.segment] = await find_template(
                    session, campaign.venue_id, m.segment, campaign.type
                )
            tpl = templates[m.segment]
            if tpl is None:
                msg.status, msg.skip_reason = "skipped", "no_template"
            else:
                msg.status, msg.template_id = "queued", tpl.id
                msg.body = render(
                    tpl.body, {"full_name": m.full_name, "email": m.email, "subject": campaign.subject}
                )
                queued += 1
        session.add(msg)

    campaign.status = "sending"
    campaign.recipients_count = len(members)
    await session.flush()
    events.publish(session, "marketing.campaign_prepared", {"campaign_id": campaign.id, "queued": queued})


async def deliver_messages(session: AsyncSession, campaign_id: int) -> None:
    campaign = await session.get(Campaign, campaign_id, with_for_update=True)
    if campaign is None or campaign.status != "sending":
        return
    now = clock.now()
    await session.execute(
        update(SentMessage)
        .where(SentMessage.campaign_id == campaign_id, SentMessage.status == "queued")
        .values(status="sent", sent_at=now)
    )
    campaign.status = "sent"
    campaign.finished_at = now
    events.publish(
        session,
        "marketing.campaign_finished",
        {"campaign_id": campaign.id, "audience_id": campaign.audience_id, "finished_at": now.isoformat()},
    )


async def summarize_campaign(session: AsyncSession, campaign_id: int) -> Campaign:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        raise NotFound(f"кампания {campaign_id}")
    counts = dict(
        (
            await session.execute(
                select(SentMessage.status, func.count())
                .where(SentMessage.campaign_id == campaign_id, SentMessage.is_test.is_(False))
                .group_by(SentMessage.status)
            )
        ).all()
    )
    campaign.sent_count = counts.get("sent", 0) + counts.get("bounced", 0)
    campaign.skipped_count = counts.get("skipped", 0)
    audience = await _audience(session, campaign.audience_id)
    if audience.last_campaign_at is None or audience.last_campaign_at < campaign.finished_at:
        audience.last_campaign_at = campaign.finished_at
    return campaign


async def campaign_report(
    session: AsyncSession, campaign_id: int, manager_id: int
) -> tuple[Campaign, dict[str, int]]:
    """Кампания и число пропущенных писем по причинам."""
    campaign = await _campaign_for(session, campaign_id, manager_id)
    reasons = (
        await session.execute(
            select(SentMessage.skip_reason, func.count())
            .where(
                SentMessage.campaign_id == campaign_id,
                SentMessage.status == "skipped",
                SentMessage.is_test.is_(False),
            )
            .group_by(SentMessage.skip_reason)
        )
    ).all()
    return campaign, dict(reasons)


# Письма ---------------------------------------------------------------------


async def campaign_messages(session: AsyncSession, campaign_id: int, manager_id: int) -> list[SentMessage]:
    await _campaign_for(session, campaign_id, manager_id)
    rows = await session.scalars(
        select(SentMessage).where(SentMessage.campaign_id == campaign_id).order_by(SentMessage.id)
    )
    return list(rows.all())


async def send_test_message(
    session: AsyncSession,
    campaign_id: int,
    manager_id: int,
    *,
    email: str,
    full_name: str = "Тестовый читатель",
    segment: str = "paid",
) -> SentMessage:
    campaign = await _campaign_for(session, campaign_id, manager_id)
    if campaign.status not in NOT_STARTED:
        raise DomainError("тестовое письмо отправляют только до запуска кампании")
    if segment not in settings.AUDIENCE_GROUP:
        raise DomainError(f"неизвестный сегмент читателя: {segment}")
    email = normalize_email(email)
    sent = await session.scalar(
        select(func.count()).where(SentMessage.campaign_id == campaign_id, SentMessage.is_test.is_(True))
    )
    if sent >= settings.MAX_TEST_MESSAGES:
        raise DomainError(f"по кампании уже отправлено {settings.MAX_TEST_MESSAGES} тестовых писем")
    tpl = await find_template(session, campaign.venue_id, segment, campaign.type)
    if tpl is None:
        raise DomainError("для этого сегмента нет шаблона письма")
    now = clock.now()
    msg = SentMessage(
        campaign_id=campaign_id,
        template_id=tpl.id,
        email=email,
        segment=segment,
        body=render(tpl.body, {"full_name": full_name, "email": email, "subject": campaign.subject}),
        status="sent",
        is_test=True,
        created_at=now,
        sent_at=now,
    )
    session.add(msg)
    await session.flush()
    return msg


async def register_bounce(session: AsyncSession, message_id: int) -> SentMessage:
    msg = await session.get(SentMessage, message_id)
    if msg is None:
        raise NotFound(f"письмо {message_id}")
    if msg.is_test or msg.status != "sent":
        raise DomainError("возврат возможен только по отправленному письму кампании")
    msg.status = "bounced"
    events.publish(
        session,
        "marketing.message_bounced",
        {"message_id": msg.id, "campaign_id": msg.campaign_id, "email": msg.email},
    )
    return msg


async def handle_bounce(session: AsyncSession, email: str) -> None:
    bounced = await session.scalar(
        select(func.count()).where(
            SentMessage.email == email, SentMessage.status == "bounced", SentMessage.is_test.is_(False)
        )
    )
    if bounced >= settings.BOUNCE_LIMIT:
        await unsubscribe(session, email=email, reason="bounce")


async def purge_test_messages(session: AsyncSession, before: datetime) -> int:
    result = await session.execute(
        delete(SentMessage).where(SentMessage.is_test.is_(True), SentMessage.sent_at < before)
    )
    return result.rowcount


# Отписки --------------------------------------------------------------------


async def unsubscribe(
    session: AsyncSession, *, email: str, venue_id: int | None = None, reason: str = "reader"
) -> Unsubscription:
    if reason not in UNSUBSCRIBE_REASONS:
        raise DomainError(f"неизвестная причина отписки: {reason}")
    email = normalize_email(email)
    # Уже отписан от всей сети или от этой площадки — повторно ничего не делаем
    scope = Unsubscription.venue_id.is_(None)
    if venue_id is not None:
        scope = or_(scope, Unsubscription.venue_id == venue_id)
    existing = await session.scalar(
        select(Unsubscription).where(Unsubscription.email == email, scope).limit(1)
    )
    if existing is not None:
        return existing

    row = Unsubscription(email=email, venue_id=venue_id, reason=reason, created_at=clock.now())
    session.add(row)
    await session.flush()
    events.publish(
        session, "marketing.unsubscribed", {"email": email, "venue_id": venue_id, "reason": reason}
    )
    return row


async def exclude_address(session: AsyncSession, email: str, venue_id: int | None) -> None:
    """Исключает адрес из аудиторий и из писем, которые ещё не ушли."""
    audiences = select(Audience.id)
    campaigns = select(Campaign.id).where(Campaign.status.in_(RUNNING))
    if venue_id is not None:
        audiences = audiences.where(Audience.venue_id == venue_id)
        campaigns = campaigns.where(Campaign.venue_id == venue_id)
    await session.execute(
        update(AudienceMember)
        .where(AudienceMember.email == email, AudienceMember.audience_id.in_(audiences))
        .values(opted_out=True)
    )
    await session.execute(
        update(SentMessage)
        .where(
            SentMessage.email == email,
            SentMessage.status == "queued",
            SentMessage.campaign_id.in_(campaigns),
        )
        .values(status="skipped", skip_reason="unsubscribed")
    )

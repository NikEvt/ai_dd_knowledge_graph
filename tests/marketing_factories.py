"""Данные сервиса рассылок для тестов."""

from datetime import datetime

from sqlalchemy import select

from libs import db
from services.marketing import service
from services.marketing.models import Audience, AudienceMember, Campaign, SentMessage, Unsubscription
from tests.factories import act, read

VENUE, VENUE_2 = 1, 2
MANAGER, MANAGER_2, NETWORK_MANAGER, STRANGER = 701, 702, 703, 799

READERS = (
    ("anna@example.org", "Анна Петрова", "paid"),
    ("boris@example.org", "Борис Сидоров", "social"),
    ("vika@example.org", "Виктория Ли", "vip"),
)


async def run(fn, *args, **kwargs):
    """Шаг в отдельной транзакции без доставки событий."""
    async with db.sessionmaker().begin() as s:
        return await fn(s, *args, **kwargs)


async def staff() -> None:
    await act(service.add_manager, manager_id=MANAGER, venue_id=VENUE, full_name="Ольга Лаптева")
    await act(service.add_manager, manager_id=MANAGER_2, venue_id=VENUE_2, full_name="Игорь Зуев")
    await act(service.add_manager, manager_id=NETWORK_MANAGER, venue_id=None, full_name="Марина Блохина")


def manager_of(venue: int | None) -> int:
    return {VENUE: MANAGER, VENUE_2: MANAGER_2}.get(venue, NETWORK_MANAGER)


async def template(
    group: str, *, venue: int | None = VENUE, type_: str = "newsletter", body: str | None = None
) -> int:
    tpl = await act(
        service.set_template,
        manager_id=manager_of(venue),
        venue_id=venue,
        audience_group=group,
        type_=type_,
        body=body or f"[{venue or 'сеть'}/{group}] $subject. Здравствуйте, $full_name!",
    )
    return tpl.id


async def templates(venue: int | None = VENUE, type_: str = "newsletter") -> None:
    for group in ("paid", "social", "vip"):
        await template(group, venue=venue, type_=type_)


async def audience(
    name: str = "Читатели", *, venue: int = VENUE, readers: tuple[tuple[str, str, str], ...] = READERS
) -> int:
    created = await act(service.create_audience, manager_id=manager_of(venue), venue_id=venue, name=name)
    for email, full_name, segment in readers:
        await member(created.id, email, full_name, segment, venue=venue)
    return created.id


async def member(
    audience_id: int, email: str, full_name: str = "Читатель", segment: str = "paid", *, venue: int = VENUE
) -> int:
    m = await act(
        service.add_member,
        audience_id,
        manager_of(venue),
        email=email,
        full_name=full_name,
        segment=segment,
    )
    return m.id


async def campaign(
    audience_id: int,
    *,
    venue: int = VENUE,
    type_: str = "newsletter",
    subject: str = "Новинки марта",
    scheduled_at: datetime | None = None,
) -> int:
    c = await act(
        service.create_campaign,
        manager_id=manager_of(venue),
        audience_id=audience_id,
        type_=type_,
        subject=subject,
        scheduled_at=scheduled_at,
    )
    return c.id


async def launched(audience_id: int, *, venue: int = VENUE, **kwargs) -> int:
    campaign_id = await campaign(audience_id, venue=venue, **kwargs)
    await act(service.launch_campaign, campaign_id, manager_of(venue))
    return campaign_id


async def _get(s, model, id_):
    return await s.get(model, id_)


async def campaign_row(campaign_id: int) -> Campaign:
    return await read(_get, Campaign, campaign_id)


async def audience_row(audience_id: int) -> Audience:
    return await read(_get, Audience, audience_id)


async def _messages(s, campaign_id: int) -> list[SentMessage]:
    rows = await s.scalars(
        select(SentMessage).where(SentMessage.campaign_id == campaign_id).order_by(SentMessage.id)
    )
    return list(rows.all())


async def messages(campaign_id: int) -> dict[str, SentMessage]:
    return {m.email: m for m in await read(_messages, campaign_id) if not m.is_test}


async def _members(s, email: str) -> list[AudienceMember]:
    return list((await s.scalars(select(AudienceMember).where(AudienceMember.email == email))).all())


async def members(email: str) -> list[AudienceMember]:
    return await read(_members, email)


async def _unsubscriptions(s, email: str) -> list[Unsubscription]:
    return list((await s.scalars(select(Unsubscription).where(Unsubscription.email == email))).all())


async def unsubscriptions(email: str) -> list[Unsubscription]:
    return await read(_unsubscriptions, email)

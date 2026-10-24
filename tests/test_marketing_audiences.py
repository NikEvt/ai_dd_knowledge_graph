import pytest
from sqlalchemy.exc import IntegrityError

from libs import db
from libs.errors import AccessDenied, DomainError
from services.marketing import service
from tests import marketing_factories as mf
from tests.factories import T0, act


@pytest.fixture(autouse=True)
async def staff() -> None:
    await mf.staff()


async def test_audience_is_created_by_venue_manager() -> None:
    audience_id = await mf.audience("Постоянные читатели")
    audience = await mf.audience_row(audience_id)
    assert audience.venue_id == mf.VENUE
    assert audience.created_by == mf.MANAGER
    assert audience.created_at == T0
    assert [m.audience_id for m in await mf.members("anna@example.org")] == [audience_id]


async def test_manager_of_other_venue_is_denied() -> None:
    with pytest.raises(AccessDenied, match="не ведёт рассылки этой площадки"):
        await act(service.create_audience, manager_id=mf.MANAGER_2, venue_id=mf.VENUE, name="Чужая")
    audience_id = await mf.audience(readers=())
    with pytest.raises(AccessDenied):
        await act(
            service.add_member,
            audience_id,
            mf.STRANGER,
            email="x@example.org",
            full_name="Икс",
            segment="paid",
        )
    # менеджер сети работает с любой площадкой
    created = await act(
        service.create_audience, manager_id=mf.NETWORK_MANAGER, venue_id=mf.VENUE_2, name="Партнёры"
    )
    assert created.venue_id == mf.VENUE_2


async def test_audience_name_is_unique_within_venue() -> None:
    await mf.audience("Партнёры", readers=())
    with pytest.raises(DomainError, match="уже есть аудитория «Партнёры»"):
        await mf.audience("  Партнёры ", readers=())
    # на другой площадке то же название допустимо
    await mf.audience("Партнёры", venue=mf.VENUE_2, readers=())


async def test_member_email_is_normalized_and_unique() -> None:
    audience_id = await mf.audience(readers=())
    await mf.member(audience_id, "  Anna@Example.ORG ")
    assert [m.email for m in await mf.members("anna@example.org")] == ["anna@example.org"]
    with pytest.raises(DomainError, match="уже есть в аудитории"):
        await mf.member(audience_id, "ANNA@example.org")


async def test_member_email_normalized_by_database_too() -> None:
    audience_id = await mf.audience(readers=())
    async with db.engine().begin() as conn:
        await conn.exec_driver_sql(
            "INSERT INTO marketing.audience_members (audience_id, email, full_name, segment, added_at) "
            f"VALUES ({audience_id}, ' Gleb@Example.org', 'Глеб', 'paid', now())"
        )
    assert len(await mf.members("gleb@example.org")) == 1
    with pytest.raises(IntegrityError):
        async with db.engine().begin() as conn:
            await conn.exec_driver_sql(
                "INSERT INTO marketing.audience_members (audience_id, email, full_name, segment, added_at) "
                f"VALUES ({audience_id}, 'GLEB@example.org', 'Глеб', 'paid', now())"
            )


async def test_unknown_segment_and_bad_email_rejected() -> None:
    audience_id = await mf.audience(readers=())
    with pytest.raises(DomainError, match="неизвестный сегмент читателя: student"):
        await mf.member(audience_id, "s@example.org", segment="student")
    with pytest.raises(DomainError, match="некорректный адрес"):
        await mf.member(audience_id, "@example.org")


async def test_unsubscribed_address_cannot_be_added() -> None:
    await act(service.unsubscribe, email="anna@example.org", venue_id=mf.VENUE)
    audience_id = await mf.audience(readers=())
    with pytest.raises(DomainError, match="отписан"):
        await mf.member(audience_id, "anna@example.org")
    # отписка от одной площадки не мешает другой
    other = await mf.audience(venue=mf.VENUE_2, readers=())
    await mf.member(other, "anna@example.org", venue=mf.VENUE_2)


async def test_archived_audience_cannot_have_pending_campaigns() -> None:
    audience_id = await mf.audience()
    await mf.campaign(audience_id, scheduled_at=T0.replace(hour=18))
    with pytest.raises(DomainError, match="незавершённые кампании"):
        await act(service.archive_audience, audience_id, mf.MANAGER)

    empty = await mf.audience("Пустая", readers=())
    await act(service.archive_audience, empty, mf.MANAGER)
    with pytest.raises(DomainError, match="аудитория в архиве"):
        await mf.campaign(empty)

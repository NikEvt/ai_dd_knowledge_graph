import pytest
from sqlalchemy.exc import IntegrityError

from libs import db
from libs.errors import AccessDenied, DomainError
from services.marketing import service
from services.marketing.settings import AUDIENCE_GROUP
from tests import marketing_factories as mf
from tests.factories import act, read


@pytest.fixture(autouse=True)
async def staff() -> None:
    await mf.staff()


async def _insert_template(venue: str, group: str, type_: str = "newsletter") -> None:
    async with db.engine().begin() as conn:
        await conn.exec_driver_sql(
            "INSERT INTO marketing.campaign_templates (venue_id, audience_group, type, body, updated_at) "
            f"VALUES ({venue}, '{group}', '{type_}', 'текст', now())"
        )


async def test_audience_group_is_checked_by_database() -> None:
    with pytest.raises(IntegrityError, match="campaign_templates_audience_group_check"):
        await _insert_template("1", "corporate")


async def test_one_template_per_venue_group_and_type() -> None:
    await _insert_template("1", "vip")
    with pytest.raises(IntegrityError, match="campaign_templates_venue_group_type_uq"):
        await _insert_template("1", "vip")
    await _insert_template("NULL", "vip")
    with pytest.raises(IntegrityError, match="campaign_templates_default_uq"):
        await _insert_template("NULL", "vip")


async def test_set_template_updates_existing() -> None:
    first = await mf.template("paid", body="Старый текст")
    second = await mf.template("paid", body="Новый текст для $full_name")
    assert first == second
    tpl = await read(service.find_template, mf.VENUE, "paid", "newsletter")
    assert tpl.body == "Новый текст для $full_name"


async def test_template_validation() -> None:
    with pytest.raises(DomainError, match="неизвестная группа аудитории: debt"):
        await mf.template("debt")
    with pytest.raises(DomainError, match="неизвестный тип кампании"):
        await mf.template("paid", type_="sms")
    with pytest.raises(DomainError, match="текст шаблона пуст"):
        await mf.template("paid", body="   ")


async def test_network_templates_only_by_network_manager() -> None:
    with pytest.raises(AccessDenied, match="менеджер сети"):
        await act(
            service.set_template,
            manager_id=mf.MANAGER,
            venue_id=None,
            audience_group="paid",
            type_="newsletter",
            body="текст",
        )
    await mf.template("paid", venue=None)


async def test_paying_segments_share_template() -> None:
    await mf.templates()
    for segment in ("paid", "debt", "corporate"):
        tpl = await read(service.find_template, mf.VENUE, segment, "newsletter")
        assert AUDIENCE_GROUP[segment] == "paid"
        assert (tpl.audience_group, tpl.venue_id) == ("paid", mf.VENUE)
    vip = await read(service.find_template, mf.VENUE, "vip", "newsletter")
    assert vip.audience_group == "vip"


async def test_find_template_falls_back_to_network_then_paid_group() -> None:
    venue_paid = await mf.template("paid")
    network_social = await mf.template("social", venue=None)

    social = await read(service.find_template, mf.VENUE, "social", "newsletter")
    assert social.id == network_social
    # для VIP нет ни шаблона площадки, ни шаблона сети — берётся платная группа
    vip = await read(service.find_template, mf.VENUE, "vip", "newsletter")
    assert vip.id == venue_paid
    # на другой площадке своего шаблона нет совсем
    assert await read(service.find_template, mf.VENUE_2, "vip", "newsletter") is None
    assert await read(service.find_template, mf.VENUE, "paid", "event") is None

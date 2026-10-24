from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from libs.web import session
from services.marketing import service
from services.marketing.models import Campaign

router = APIRouter(prefix="/marketing", tags=["marketing"])
Session = Annotated[AsyncSession, Depends(session)]


class AudienceIn(BaseModel):
    manager_id: int
    venue_id: int
    name: str


class MemberIn(BaseModel):
    manager_id: int
    email: str
    full_name: str
    segment: str


class TemplateIn(BaseModel):
    manager_id: int
    venue_id: int | None = None
    audience_group: str
    type: str
    body: str


class CampaignIn(BaseModel):
    manager_id: int
    audience_id: int
    type: str
    subject: str
    scheduled_at: datetime | None = None


class ScheduleIn(BaseModel):
    manager_id: int
    scheduled_at: datetime


class CampaignOut(BaseModel):
    id: int
    status: str
    scheduled_at: datetime | None
    recipients_count: int
    sent_count: int
    skipped_count: int
    skipped_by_reason: dict[str, int] = {}

    @classmethod
    def of(cls, c: Campaign, skipped_by_reason: dict[str, int] | None = None) -> CampaignOut:
        return cls(
            id=c.id,
            status=c.status,
            scheduled_at=c.scheduled_at,
            recipients_count=c.recipients_count,
            sent_count=c.sent_count,
            skipped_count=c.skipped_count,
            skipped_by_reason=skipped_by_reason or {},
        )


class TestMessageIn(BaseModel):
    manager_id: int
    email: str
    full_name: str = "Тестовый читатель"
    segment: str = "paid"


class MessageOut(BaseModel):
    id: int
    body: str
    sent_at: datetime | None


class UnsubscribeIn(BaseModel):
    email: str
    venue_id: int | None = None


@router.post("/audiences", status_code=201)
async def create_audience(body: AudienceIn, s: Session) -> dict[str, int]:
    audience = await service.create_audience(
        s, manager_id=body.manager_id, venue_id=body.venue_id, name=body.name
    )
    return {"audience_id": audience.id}


@router.post("/audiences/{audience_id}/members", status_code=201)
async def add_member(audience_id: int, body: MemberIn, s: Session) -> dict[str, int]:
    member = await service.add_member(
        s,
        audience_id,
        body.manager_id,
        email=body.email,
        full_name=body.full_name,
        segment=body.segment,
    )
    return {"member_id": member.id}


@router.post("/audiences/{audience_id}/archive", status_code=204)
async def archive_audience(audience_id: int, manager_id: int, s: Session) -> None:
    await service.archive_audience(s, audience_id, manager_id)


@router.put("/templates")
async def set_template(body: TemplateIn, s: Session) -> dict[str, int]:
    tpl = await service.set_template(
        s,
        manager_id=body.manager_id,
        venue_id=body.venue_id,
        audience_group=body.audience_group,
        type_=body.type,
        body=body.body,
    )
    return {"template_id": tpl.id}


@router.post("/campaigns", status_code=201)
async def create_campaign(body: CampaignIn, s: Session) -> dict[str, int]:
    campaign = await service.create_campaign(
        s,
        manager_id=body.manager_id,
        audience_id=body.audience_id,
        type_=body.type,
        subject=body.subject,
        scheduled_at=body.scheduled_at,
    )
    return {"campaign_id": campaign.id}


@router.get("/campaigns/{campaign_id}")
async def campaign(campaign_id: int, manager_id: int, s: Session) -> CampaignOut:
    c, skipped = await service.campaign_report(s, campaign_id, manager_id)
    return CampaignOut.of(c, skipped)


@router.post("/campaigns/{campaign_id}/schedule")
async def schedule(campaign_id: int, body: ScheduleIn, s: Session) -> CampaignOut:
    return CampaignOut.of(await service.schedule_campaign(s, campaign_id, body.manager_id, body.scheduled_at))


@router.post("/campaigns/{campaign_id}/cancel")
async def cancel(campaign_id: int, manager_id: int, s: Session) -> CampaignOut:
    return CampaignOut.of(await service.cancel_campaign(s, campaign_id, manager_id))


@router.post("/campaigns/{campaign_id}/launch")
async def launch(campaign_id: int, manager_id: int, s: Session) -> CampaignOut:
    return CampaignOut.of(await service.launch_campaign(s, campaign_id, manager_id))


@router.get("/campaigns/{campaign_id}/messages")
async def messages(campaign_id: int, manager_id: int, s: Session) -> list[MessageOut]:
    return [
        MessageOut(id=m.id, body=m.body, sent_at=m.sent_at)
        for m in await service.campaign_messages(s, campaign_id, manager_id)
    ]


@router.post("/campaigns/{campaign_id}/messages/test", status_code=201)
async def send_test(campaign_id: int, body: TestMessageIn, s: Session) -> MessageOut:
    m = await service.send_test_message(
        s,
        campaign_id,
        body.manager_id,
        email=body.email,
        full_name=body.full_name,
        segment=body.segment,
    )
    return MessageOut(id=m.id, body=m.body, sent_at=m.sent_at)


@router.post("/messages/{message_id}/bounce", status_code=204)
async def bounce(message_id: int, s: Session) -> None:
    await service.register_bounce(s, message_id)


@router.post("/unsubscribe", status_code=204)
async def unsubscribe(body: UnsubscribeIn, s: Session) -> None:
    await service.unsubscribe(s, email=body.email, venue_id=body.venue_id)

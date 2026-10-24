from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from libs.web import session
from services.applications import service

router = APIRouter(prefix="/applications", tags=["applications"])
Session = Annotated[AsyncSession, Depends(session)]


class ApplicationIn(BaseModel):
    operator_id: int
    client_id: int
    representative_id: int
    sphere_id: int
    venue_id: int
    book_ids: list[int]
    social: bool = False


class ApplicationOut(BaseModel):
    id: int
    kind: str
    stage: str
    venue_id: int
    sphere_id: int
    book_ids: list[int]


class VenueChangeIn(BaseModel):
    operator_id: int
    venue_id: int


def _out(app) -> ApplicationOut:
    return ApplicationOut(
        id=app.id,
        kind=app.kind,
        stage=app.stage,
        venue_id=app.venue_id,
        sphere_id=app.sphere_id,
        book_ids=app.book_ids,
    )


@router.post("", status_code=201)
async def create(body: ApplicationIn, s: Session) -> ApplicationOut:
    return _out(await service.create_application(s, **body.model_dump()))


@router.get("/{application_id}")
async def get(application_id: int, s: Session) -> ApplicationOut:
    return _out(await service.load(s, application_id))


@router.post("/{application_id}/submit")
async def submit(application_id: int, operator_id: int, s: Session) -> ApplicationOut:
    return _out(await service.submit_for_review(s, application_id, operator_id))


@router.post("/{application_id}/approve")
async def approve(application_id: int, reviewer_id: int, s: Session) -> ApplicationOut:
    return _out(await service.approve(s, application_id, reviewer_id))


@router.post("/{application_id}/venue")
async def change_venue(application_id: int, body: VenueChangeIn, s: Session) -> ApplicationOut:
    return _out(await service.change_venue(s, application_id, body.operator_id, body.venue_id))

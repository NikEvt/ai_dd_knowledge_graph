from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from libs.web import session
from services.inventory import service

router = APIRouter(tags=["inventory"])
Session = Annotated[AsyncSession, Depends(session)]


class CopyIn(BaseModel):
    custodian_id: int
    venue_id: int
    book_ref: int
    inventory_no: str


class CopyOut(BaseModel):
    id: int
    inventory_no: str
    book_ref: int
    venue_id: int
    state: str


class ByCustodian(BaseModel):
    custodian_id: int
    note: str | None = None


class TransferIn(BaseModel):
    custodian_id: int
    to_venue_id: int


class TransferOut(BaseModel):
    id: int
    copy_id: int
    from_venue_id: int
    to_venue_id: int
    status: str


class IllIn(BaseModel):
    custodian_id: int
    copy_id: int
    partner_id: int


class IllOut(BaseModel):
    id: int
    copy_id: int
    partner_id: int
    due_at: datetime
    status: str


class ReturnIn(BaseModel):
    custodian_id: int
    damaged: bool = False


class StockOut(BaseModel):
    total: int
    available: int


class PenaltyOut(BaseModel):
    id: int
    ill_loan_id: int
    kind: str
    days: int
    amount: Decimal
    status: str


def _copy(c) -> CopyOut:
    return CopyOut(
        id=c.id, inventory_no=c.inventory_no, book_ref=c.book_ref, venue_id=c.venue_id, state=c.state
    )


def _transfer(t) -> TransferOut:
    return TransferOut(
        id=t.id, copy_id=t.copy_id, from_venue_id=t.from_venue_id, to_venue_id=t.to_venue_id, status=t.status
    )


def _loan(x) -> IllOut:
    return IllOut(id=x.id, copy_id=x.copy_id, partner_id=x.partner_id, due_at=x.due_at, status=x.status)


@router.post("/copies", status_code=201)
async def register_copy(body: CopyIn, s: Session) -> CopyOut:
    return _copy(await service.register_copy(s, **body.model_dump()))


@router.get("/copies/{copy_id}")
async def get_copy(copy_id: int, s: Session) -> CopyOut:
    return _copy(await service.get_copy(s, copy_id))


@router.get("/venues/{venue_id}/stock/{book_ref}")
async def get_stock(venue_id: int, book_ref: int, s: Session) -> StockOut:
    total, available = await service.stock(s, book_ref, venue_id)
    return StockOut(total=total, available=available)


@router.post("/copies/{copy_id}/lost")
async def mark_lost(copy_id: int, body: ByCustodian, s: Session) -> CopyOut:
    return _copy(await service.mark_lost(s, copy_id, body.custodian_id, body.note))


@router.post("/copies/{copy_id}/damaged")
async def mark_damaged(copy_id: int, body: ByCustodian, s: Session) -> CopyOut:
    return _copy(await service.mark_damaged(s, copy_id, body.custodian_id, body.note))


@router.post("/copies/{copy_id}/write-off", status_code=201)
async def write_off_worn(copy_id: int, body: ByCustodian, s: Session) -> dict[str, str]:
    act = await service.write_off_worn(s, copy_id, body.custodian_id, body.note)
    return {"act_no": act.act_no}


@router.post("/copies/{copy_id}/transfers", status_code=201)
async def request_transfer(copy_id: int, body: TransferIn, s: Session) -> TransferOut:
    return _transfer(await service.request_transfer(s, copy_id, body.to_venue_id, body.custodian_id))


@router.post("/transfers/{transfer_id}/ship")
async def ship_transfer(transfer_id: int, body: ByCustodian, s: Session) -> TransferOut:
    return _transfer(await service.ship_transfer(s, transfer_id, body.custodian_id))


@router.post("/transfers/{transfer_id}/receive")
async def receive_transfer(transfer_id: int, body: ByCustodian, s: Session) -> TransferOut:
    return _transfer(await service.receive_transfer(s, transfer_id, body.custodian_id))


@router.post("/transfers/{transfer_id}/cancel")
async def cancel_transfer(transfer_id: int, body: ByCustodian, s: Session) -> TransferOut:
    reason = body.note or "cancelled"
    return _transfer(await service.cancel_transfer(s, transfer_id, body.custodian_id, reason=reason))


@router.post("/ill-loans", status_code=201)
async def issue_ill(body: IllIn, s: Session) -> IllOut:
    return _loan(await service.issue_ill(s, body.copy_id, body.partner_id, body.custodian_id))


@router.post("/ill-loans/{loan_id}/renew")
async def renew_ill(loan_id: int, body: ByCustodian, s: Session) -> IllOut:
    return _loan(await service.renew_ill(s, loan_id, body.custodian_id))


@router.post("/ill-loans/{loan_id}/return")
async def return_ill(loan_id: int, body: ReturnIn, s: Session) -> IllOut:
    return _loan(await service.return_ill(s, loan_id, body.custodian_id, damaged=body.damaged))


@router.post("/ill-loans/{loan_id}/lost")
async def report_ill_lost(loan_id: int, body: ByCustodian, s: Session) -> IllOut:
    return _loan(await service.report_ill_lost(s, loan_id, body.custodian_id))


@router.get("/partners/{partner_id}/penalties")
async def penalties(partner_id: int, s: Session) -> list[PenaltyOut]:
    return [
        PenaltyOut(
            id=p.id, ill_loan_id=p.ill_loan_id, kind=p.kind, days=p.days, amount=p.amount, status=p.status
        )
        for p in await service.penalties(s, partner_id)
    ]

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from libs.errors import NotFound
from libs.web import session
from services.partners import service
from services.partners.models import Contract

router = APIRouter(tags=["partners"])
Session = Annotated[AsyncSession, Depends(session)]


class RequestIn(BaseModel):
    inn: str
    contact_name: str
    contact_email: str
    kpp: str | None = None
    legal_name: str | None = None
    contact_phone: str | None = None


class DecisionIn(BaseModel):
    manager_id: int
    approve: bool = True
    reason: str | None = None


class RequisitesIn(BaseModel):
    manager_id: int
    kpp: str | None = None
    legal_name: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None


class DealIn(BaseModel):
    manager_id: int
    external_ref: str
    amount: Decimal = Field(gt=0)


class RateIn(BaseModel):
    manager_id: int
    commission_pct: Decimal


class CreditIn(BaseModel):
    manager_id: int
    allowed: bool
    limit: Decimal = Decimal(0)


class TerminationIn(BaseModel):
    manager_id: int
    reason: str


class HistoryOut(BaseModel):
    field: str
    old_value: str | None
    new_value: str | None
    changed_at: datetime


class PayoutOut(BaseModel):
    id: int
    period: date
    total: Decimal
    commissions: int
    status: str


class ContractOut(BaseModel):
    id: int
    number: str
    status: str
    commission_pct: Decimal
    credit_allowed: bool
    credit_limit: Decimal
    credit_used: Decimal


class CommissionOut(BaseModel):
    id: int
    deal_id: int
    base_amount: Decimal
    rate_pct: Decimal
    amount: Decimal
    accrued_at: datetime


@router.post("/partners/requests", status_code=201)
async def submit_request(body: RequestIn, s: Session) -> dict[str, int]:
    req = await service.submit_request(s, **body.model_dump())
    return {"request_id": req.id}


@router.post("/partners/requests/{request_id}/decision")
async def decide(request_id: int, body: DecisionIn, s: Session) -> dict[str, str]:
    if body.approve:
        req = await service.approve_request(s, request_id, body.manager_id)
    else:
        req = await service.reject_request(s, request_id, body.manager_id, body.reason or "")
    return {"status": req.status}


@router.patch("/partners/{partner_id}/requisites")
async def update_requisites(partner_id: int, body: RequisitesIn, s: Session) -> dict[str, list[str]]:
    fields = body.model_dump(exclude_unset=True, exclude={"manager_id"})
    partner = await service.update_requisites(s, partner_id, body.manager_id, **fields)
    return {"missing": service.missing_requisites(partner)}


@router.get("/contracts/{contract_id}")
async def contract(contract_id: int, s: Session) -> ContractOut:
    c = await s.get(Contract, contract_id)
    if c is None:
        raise NotFound(f"договор {contract_id}")
    return ContractOut(
        id=c.id,
        number=c.number,
        status=c.status,
        commission_pct=c.commission_pct,
        credit_allowed=c.credit_allowed,
        credit_limit=c.credit_limit,
        credit_used=await service.credit_exposure(s, c.id),
    )


@router.post("/contracts/{contract_id}/activate")
async def activate(contract_id: int, manager_id: int, s: Session) -> dict[str, str]:
    c = await service.activate_contract(s, contract_id, manager_id)
    return {"status": c.status}


@router.post("/contracts/{contract_id}/deals", status_code=201)
async def open_deal(contract_id: int, body: DealIn, s: Session) -> dict[str, int | str]:
    deal = await service.open_deal(
        s, contract_id, body.manager_id, external_ref=body.external_ref, amount=body.amount
    )
    return {"deal_id": deal.id, "status": deal.status}


@router.post("/deals/{deal_id}/close")
async def close_deal(deal_id: int, manager_id: int, s: Session) -> None:
    await service.close_deal(s, deal_id, manager_id)


@router.post("/deals/{deal_id}/prepayment")
async def prepayment(deal_id: int, manager_id: int, s: Session) -> None:
    await service.register_prepayment(s, deal_id, manager_id)


@router.post("/deals/{deal_id}/payment")
async def payment(deal_id: int, s: Session) -> None:
    await service.register_payment(s, deal_id)


@router.delete("/deals/{deal_id}")
async def cancel_deal(deal_id: int, manager_id: int, s: Session) -> None:
    await service.cancel_deal(s, deal_id, manager_id)


@router.put("/contracts/{contract_id}/rate")
async def change_rate(contract_id: int, body: RateIn, s: Session) -> None:
    await service.change_commission_rate(s, contract_id, body.manager_id, body.commission_pct)


@router.put("/contracts/{contract_id}/credit")
async def credit_terms(contract_id: int, body: CreditIn, s: Session) -> None:
    await service.set_credit_terms(s, contract_id, body.manager_id, allowed=body.allowed, limit=body.limit)


@router.post("/contracts/{contract_id}/termination")
async def terminate(contract_id: int, body: TerminationIn, s: Session) -> dict[str, str]:
    c = await service.terminate_contract(s, contract_id, body.manager_id, body.reason)
    return {"status": c.status}


@router.post("/partners/{partner_id}/contracts", status_code=201)
async def renew(partner_id: int, manager_id: int, s: Session) -> dict[str, int | str]:
    c = await service.renew_contract(s, partner_id, manager_id)
    return {"contract_id": c.id, "number": c.number}


@router.get("/contracts/{contract_id}/history")
async def history(contract_id: int, s: Session) -> list[HistoryOut]:
    return [
        HistoryOut(field=h.field, old_value=h.old_value, new_value=h.new_value, changed_at=h.changed_at)
        for h in await service.contract_history(s, contract_id)
    ]


@router.get("/partners/{partner_id}/payouts")
async def payouts(partner_id: int, s: Session) -> list[PayoutOut]:
    return [
        PayoutOut(id=p.id, period=p.period, total=p.total, commissions=p.commissions_count, status=p.status)
        for p in await service.payouts(s, partner_id)
    ]


@router.get("/partners/{partner_id}/commissions")
async def commissions(partner_id: int, s: Session) -> list[CommissionOut]:
    return [
        CommissionOut(
            id=c.id,
            deal_id=c.deal_id,
            base_amount=c.base_amount,
            rate_pct=c.rate_pct,
            amount=c.amount,
            accrued_at=c.accrued_at,
        )
        for c in await service.commissions(s, partner_id)
    ]

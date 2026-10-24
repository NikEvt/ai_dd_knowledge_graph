from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from libs.web import session
from services.subscriptions import service
from services.subscriptions.models import Subscription

router = APIRouter(tags=["subscriptions"])
Session = Annotated[AsyncSession, Depends(session)]


class PlanOut(BaseModel):
    id: int
    code: str
    name: str
    kind: str
    monthly_fee: Decimal
    max_books: int


class SubscriptionIn(BaseModel):
    client_ref: str
    plan_id: int
    holder_name: str
    passport: str | None = None
    birth_date: date | None = None
    employer_ref: str | None = None


class SubscriptionOut(BaseModel):
    id: int
    client_ref: str
    plan_id: int
    status: str
    holder_name: str
    holder_check: str
    paid_until: date | None

    @classmethod
    def of(cls, sub: Subscription) -> SubscriptionOut:
        return cls(
            id=sub.id,
            client_ref=sub.client_ref,
            plan_id=sub.plan_id,
            status=sub.status,
            holder_name=sub.holder_name,
            holder_check=sub.holder_check,
            paid_until=sub.paid_until,
        )


class HolderIn(BaseModel):
    client_ref: str
    holder_name: str | None = None
    passport: str | None = None
    birth_date: date | None = None


class PaymentIn(BaseModel):
    amount: Decimal
    external_ref: str | None = None


@router.get("/plans")
async def plans(s: Session) -> list[PlanOut]:
    return [
        PlanOut(
            id=p.id, code=p.code, name=p.name, kind=p.kind, monthly_fee=p.monthly_fee, max_books=p.max_books
        )
        for p in await service.list_plans(s)
    ]


@router.post("/subscriptions", status_code=201)
async def create(body: SubscriptionIn, s: Session) -> dict[str, int]:
    sub = await service.create_subscription(s, **body.model_dump())
    invoice = await service.open_invoice(s, sub.id)
    return {"subscription_id": sub.id, "invoice_id": invoice.id}


@router.get("/subscriptions/{subscription_id}")
async def get(subscription_id: int, s: Session) -> SubscriptionOut:
    return SubscriptionOut.of(await service.get_subscription(s, subscription_id))


@router.get("/clients/{client_ref}/subscriptions")
async def by_client(client_ref: str, s: Session) -> list[SubscriptionOut]:
    return [SubscriptionOut.of(x) for x in await service.client_subscriptions(s, client_ref)]


@router.put("/subscriptions/{subscription_id}/holder")
async def update_holder(subscription_id: int, body: HolderIn, s: Session) -> SubscriptionOut:
    sub = await service.update_holder(s, subscription_id, **body.model_dump())
    return SubscriptionOut.of(sub)


@router.post("/invoices/{invoice_id}/payments", status_code=201)
async def pay(invoice_id: int, body: PaymentIn, s: Session) -> dict[str, int]:
    payment = await service.record_payment(s, invoice_id, body.amount, external_ref=body.external_ref)
    return {"payment_id": payment.id}

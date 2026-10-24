from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from libs.web import session
from services.billing import service

router = APIRouter(tags=["billing"])
Session = Annotated[AsyncSession, Depends(session)]


class InvoiceOut(BaseModel):
    id: int
    application_id: int
    kind: str
    amount: Decimal
    status: str


class PaymentIn(BaseModel):
    amount: Decimal
    chief_id: int


def _out(inv) -> InvoiceOut:
    return InvoiceOut(
        id=inv.id, application_id=inv.application_id, kind=inv.kind, amount=inv.amount, status=inv.status
    )


@router.post("/applications/{application_id}/take")
async def take(application_id: int, accountant_id: int, s: Session) -> None:
    await service.take_application(s, application_id, accountant_id)


@router.post("/applications/{application_id}/invoices", status_code=201)
async def issue(application_id: int, accountant_id: int, s: Session) -> InvoiceOut:
    return _out(await service.issue_books_invoice(s, application_id, accountant_id))


@router.post("/invoices/{invoice_id}/payments", status_code=201)
async def link(invoice_id: int, body: PaymentIn, s: Session) -> None:
    await service.link_payment(s, invoice_id, body.amount, body.chief_id)
